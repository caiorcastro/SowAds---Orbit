#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from content_sanitizer import split_content_package


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def append_jsonl(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def extract_html_from_package(content_package: str) -> str:
    if not content_package:
        return ""
    _, html, _ = split_content_package(content_package)
    return html


def read_rows(path: Path) -> List[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_batch_id_from_articles_name(name: str) -> str:
    # BATCH-YYYYMMDD-HHMMSS_articles.csv
    return name.split("_articles.csv", 1)[0]


def shell_with_password(command: str, password: str, timeout: int = 1200) -> str:
    script = f"""
import pexpect
import sys
cmd = {command!r}
pwd = {password!r}
child = pexpect.spawn(cmd, encoding='utf-8', timeout={timeout})
i = child.expect(['assword:', 'continue connecting (yes/no)?', pexpect.EOF])
if i == 1:
    child.sendline('yes')
    child.expect('assword:')
    child.sendline(pwd)
elif i == 0:
    child.sendline(pwd)
child.expect(pexpect.EOF)
print(child.before)
child.close()
code = child.exitstatus if child.exitstatus is not None else (child.status or 0)
sys.exit(code)
"""
    proc = subprocess.run(["python3", "-c", script], capture_output=True, text=True)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"SSH/SCP failed: {msg}")
    return proc.stdout


def parse_batch_id_from_row_or_file(row: dict, file_name: str) -> str:
    batch_id = (row.get("batch_id") or "").strip()
    if batch_id:
        return batch_id
    if file_name.endswith("_articles.csv"):
        return parse_batch_id_from_articles_name(file_name)
    # Fallback for custom CSV names
    return file_name.rsplit(".", 1)[0]


def collect_posts(
    base: Path,
    batch_id_filter: str = "",
    include_statuses: Optional[List[str]] = None,
    articles_csv: str = "",
) -> List[dict]:
    rows: List[dict] = []
    batch_id_filter = (batch_id_filter or "").strip()
    allowed_statuses = {(s or "").strip().upper() for s in (include_statuses or ["APPROVED"]) if (s or "").strip()}

    files: List[Path] = []
    if articles_csv:
        p = Path(articles_csv)
        if not p.is_absolute():
            p = (base / articles_csv).resolve()
        files = [p]
    else:
        articles_dir = base / "outputs/articles"
        files = sorted(articles_dir.glob("BATCH-*_articles.csv"))

    for f in files:
        for r in read_rows(f):
            status = (r.get("status") or "").strip().upper()
            if allowed_statuses and status not in allowed_statuses:
                continue
            batch_id = parse_batch_id_from_row_or_file(r, f.name)
            if batch_id_filter and batch_id != batch_id_filter:
                continue
            rows.append({**r, "_batch_id": batch_id})
    return rows


def find_image_for_item(base: Path, batch_id: str, item_id: str) -> Optional[Path]:
    direct = sorted((base / "outputs/generated-images" / batch_id).glob(f"{item_id}_01.*"))
    if direct:
        return direct[0]
    any_batch = sorted((base / "outputs/generated-images").glob(f"*/{item_id}_01.*"))
    if any_batch:
        return any_batch[-1]
    return None


def build_publish_job(
    base: Path,
    status: str,
    batch_id_filter: str = "",
    include_statuses: Optional[List[str]] = None,
    articles_csv: str = "",
) -> Dict[str, object]:
    selected_rows = collect_posts(
        base,
        batch_id_filter=batch_id_filter,
        include_statuses=include_statuses,
        articles_csv=articles_csv,
    )
    job_id = "PUB-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    job_dir = base / "outputs/publish-jobs" / job_id
    content_dir = job_dir / "content"
    image_dir = job_dir / "images"
    ensure_dir(content_dir)
    ensure_dir(image_dir)

    items: List[dict] = []
    for r in selected_rows:
        item_id = (r.get("id") or "").strip()
        slug = (r.get("slug") or "").strip()
        if not item_id or not slug:
            continue
        html = extract_html_from_package(r.get("content_package", ""))
        if not html:
            continue

        content_file = content_dir / f"{item_id}.html"
        content_file.write_text(html, encoding="utf-8")

        img_path = find_image_for_item(base, r["_batch_id"], item_id)
        copied_img = ""
        if img_path and img_path.exists():
            copied = image_dir / img_path.name
            shutil.copy2(img_path, copied)
            copied_img = f"images/{copied.name}"

        items.append(
            {
                "id": item_id,
                "batch_id": r["_batch_id"],
                "version": int((r.get("version") or "1").strip() or 1),
                "slug": slug,
                "title": (r.get("tema_principal") or "").strip() or slug,
                "meta_title": (r.get("meta_title") or "").strip(),
                "meta_description": (r.get("meta_description") or "").strip(),
                "content_rel": f"content/{content_file.name}",
                "image_rel": copied_img,
                "status": status,
            }
        )

    write_json(job_dir / "items.json", {"job_id": job_id, "items": items, "generated_at": now_iso()})
    return {"job_id": job_id, "job_dir": job_dir, "items": items}


def run_remote_publish(
    base: Path,
    job_id: str,
    job_dir: Path,
    items: List[dict],
    host: str,
    port: int,
    user: str,
    password: str,
    wp_path: str,
) -> dict:
    remote_root = f"/home/{user}/tmp_sowads_publish"
    remote_job = f"{remote_root}/{job_id}"
    local_parent = job_dir.parent

    # 1) Ensure remote root exists
    mkdir_cmd = f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} \"mkdir -p {remote_root}\""
    shell_with_password(mkdir_cmd, password, timeout=600)

    # 2) Upload whole job directory
    scp_cmd = f"scp -o StrictHostKeyChecking=no -P {port} -r {str(job_dir)} {user}@{host}:{remote_root}/"
    shell_with_password(scp_cmd, password, timeout=1800)
    results = []
    for item in items:
        slug = item["slug"]
        title = item["title"]
        post_status = item.get("status", "publish")
        content_remote = f"{remote_job}/{item['content_rel']}"
        image_remote = f"{remote_job}/{item['image_rel']}" if item.get("image_rel") else ""

        script_lines = [
            "set -e",
            f"cd {shlex.quote(wp_path)}",
            f"SLUG={shlex.quote(slug)}",
            f"TITLE={shlex.quote(title)}",
            f"STATUS={shlex.quote(post_status)}",
            f"CONTENT={shlex.quote(content_remote)}",
            "EXISTING=$(wp post list --name=\"$SLUG\" --post_type=post --post_status=any --field=ID --format=ids | awk '{print $1}')",
            "if [ -n \"$EXISTING\" ]; then",
            "  PID=\"$EXISTING\"",
            "  ACTION=updated",
            "  wp post update \"$PID\" \"$CONTENT\" --post_title=\"$TITLE\" --post_name=\"$SLUG\" --post_status=\"$STATUS\" --post_type=post >/dev/null",
            "else",
            "  ACTION=created",
            "  PID=$(wp post create \"$CONTENT\" --post_title=\"$TITLE\" --post_name=\"$SLUG\" --post_status=\"$STATUS\" --post_type=post --porcelain)",
            "fi",
            "wp post meta update \"$PID\" sowads_content_id " + shlex.quote(item["id"]) + " >/dev/null || true",
            "wp post meta update \"$PID\" sowads_content_version " + shlex.quote(str(item.get("version", 1))) + " >/dev/null || true",
            "wp post meta update \"$PID\" sowads_batch_id " + shlex.quote(item.get("batch_id", "")) + " >/dev/null || true",
        ]
        if item.get("meta_title"):
            script_lines.append("wp post meta update \"$PID\" _yoast_wpseo_title " + shlex.quote(item["meta_title"]) + " >/dev/null || true")
        if item.get("meta_description"):
            script_lines.append("wp post meta update \"$PID\" _yoast_wpseo_metadesc " + shlex.quote(item["meta_description"]) + " >/dev/null || true")

        script_lines += [
            "MID=0",
        ]
        if image_remote:
            script_lines += [
                f"IMG={shlex.quote(image_remote)}",
                "if [ -f \"$IMG\" ]; then",
                "  MID=$(wp media import \"$IMG\" --post_id=\"$PID\" --featured_image --porcelain 2>/dev/null || echo 0)",
                "fi",
            ]
        script_lines.append('echo "RESULT|$PID|$MID|$ACTION"')

        remote_cmd = (
            f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} "
            + shlex.quote("\n".join(script_lines))
        )
        try:
            output = shell_with_password(remote_cmd, password, timeout=1800)
            m = re.search(r"RESULT\|(\d+)\|(\d+)\|([a-zA-Z_]+)", output)
            if not m:
                raise RuntimeError("No RESULT marker returned by remote command")
            results.append(
                {
                    "id": item["id"],
                    "slug": slug,
                    "wp_post_id": int(m.group(1)),
                    "wp_media_id": int(m.group(2)),
                    "status": post_status,
                    "action": m.group(3),
                    "error": "",
                }
            )
        except Exception as e:
            results.append(
                {
                    "id": item["id"],
                    "slug": slug,
                    "wp_post_id": 0,
                    "wp_media_id": 0,
                    "status": post_status,
                    "action": "",
                    "error": str(e),
                }
            )

    result = {
        "job_id": job_id,
        "total": len(items),
        "ok": len([r for r in results if not r["error"]]),
        "failed": len([r for r in results if r["error"]]),
        "results": results,
    }

    local_result = job_dir / "publish_results_remote.json"
    write_json(local_result, result)

    # 3) Cleanup remote temp
    cleanup_cmd = f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} \"rm -rf {remote_job}\""
    shell_with_password(cleanup_cmd, password, timeout=600)
    return result


def write_csv(path: Path, rows: List[dict], columns: List[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def main():
    parser = argparse.ArgumentParser(description="Publish selected articles to WordPress via WP-CLI over SSH")
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--status", default="publish", choices=["draft", "publish", "private"])
    parser.add_argument("--batch-id", default="", help="Publicar somente itens deste batch_id")
    parser.add_argument(
        "--include-statuses",
        default="APPROVED",
        help="Statuses aceitos no CSV de artigos (csv list), ex: APPROVED,PENDING_QA,REJECTED",
    )
    parser.add_argument("--articles-csv", default="", help="CSV específico de artigos para publicar")
    parser.add_argument("--wp-path", default="")
    parser.add_argument("--ssh-host", default=os.getenv("WP_SSH_HOST", ""))
    parser.add_argument("--ssh-port", type=int, default=int(os.getenv("WP_SSH_PORT", "22")))
    parser.add_argument("--ssh-user", default=os.getenv("WP_SSH_USER", ""))
    parser.add_argument("--ssh-password", default=os.getenv("WP_SSH_PASSWORD", ""))
    args = parser.parse_args()

    base = Path(args.base).resolve()
    load_env_file(base / ".env")
    load_env_file(base.parent / ".env")

    ssh_host = args.ssh_host or os.getenv("WP_SSH_HOST", "")
    ssh_user = args.ssh_user or os.getenv("WP_SSH_USER", "")
    ssh_password = args.ssh_password or os.getenv("WP_SSH_PASSWORD", "")
    ssh_port = int(args.ssh_port)
    wp_path = args.wp_path or os.getenv("WP_SSH_WP_PATH", "")

    if not (ssh_host and ssh_user and ssh_password and wp_path):
        raise SystemExit("Missing SSH params. Use --ssh-* and --wp-path or envs: WP_SSH_HOST/PORT/USER/PASSWORD/WP_SSH_WP_PATH")

    include_statuses = [s.strip() for s in (args.include_statuses or "").split(",") if s.strip()]
    job = build_publish_job(
        base,
        status=args.status,
        batch_id_filter=args.batch_id,
        include_statuses=include_statuses,
        articles_csv=args.articles_csv,
    )
    job_id = str(job["job_id"])
    job_dir = Path(job["job_dir"])
    items: List[dict] = list(job["items"])
    if not items:
        raise SystemExit("No posts found to publish with selected filters.")

    remote_result = run_remote_publish(
        base=base,
        job_id=job_id,
        job_dir=job_dir,
        items=items,
        host=ssh_host,
        port=ssh_port,
        user=ssh_user,
        password=ssh_password,
        wp_path=wp_path,
    )

    published_rows = remote_result.get("results", [])
    csv_path = job_dir / "published_posts.csv"
    write_csv(csv_path, published_rows, ["id", "slug", "wp_post_id", "wp_media_id", "status", "action", "error"])

    publication_log = base / "data/logs/publication_log.jsonl"
    for row in published_rows:
        append_jsonl(
            publication_log,
            {
                "timestamp": now_iso(),
                "job_id": job_id,
                "id": row.get("id", ""),
                "slug": row.get("slug", ""),
                "wp_post_id": row.get("wp_post_id", 0),
                "wp_media_id": row.get("wp_media_id", 0),
                "status": row.get("status", ""),
                "action": row.get("action", ""),
                "error": row.get("error", ""),
            },
        )

    summary = {
        "job_id": job_id,
        "generated_items": len(items),
        "ok": remote_result.get("ok", 0),
        "failed": remote_result.get("failed", 0),
        "job_dir": str(job_dir),
        "csv": str(csv_path),
        "json": str(job_dir / "publish_results_remote.json"),
    }
    write_json(job_dir / "publish_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
