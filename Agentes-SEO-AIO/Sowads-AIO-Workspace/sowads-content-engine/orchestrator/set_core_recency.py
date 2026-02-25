#!/usr/bin/env python3
import argparse
import csv
import json
import shlex
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from publish_wp_cli import shell_with_password, write_json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_ids_from_themes(csv_path: Path) -> List[str]:
    ids: List[str] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = (row.get("id") or "").strip()
            if item_id:
                ids.append(item_id)
    return ids


def run_remote(host: str, port: int, user: str, password: str, command: str, timeout: int = 600) -> str:
    cmd = f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} " + shlex.quote(command)
    return shell_with_password(cmd, password, timeout=timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set post_date recency for a list of content ids in WP.")
    parser.add_argument("--themes-csv", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--ssh-port", type=int, required=True)
    parser.add_argument("--ssh-user", required=True)
    parser.add_argument("--ssh-password", required=True)
    parser.add_argument("--wp-path", required=True)
    parser.add_argument("--step-minutes", type=int, default=3)
    parser.add_argument("--report-json", required=True)
    args = parser.parse_args()

    ids = load_ids_from_themes(Path(args.themes_csv))
    if not ids:
        raise SystemExit("No ids found in themes csv.")

    # Most recent first.
    start_dt = datetime.now(timezone.utc)
    results = []
    for idx, item_id in enumerate(ids):
        dt = start_dt - timedelta(minutes=(idx * max(1, args.step_minutes)))
        dt_local = dt.strftime("%Y-%m-%d %H:%M:%S")
        dt_gmt = dt.strftime("%Y-%m-%d %H:%M:%S")
        script = "\n".join(
            [
                "set -e",
                f"cd {shlex.quote(args.wp_path)}",
                "PID=$(wp post list --post_type=post --post_status=any --meta_key=sowads_content_id --meta_value="
                + shlex.quote(item_id)
                + " --field=ID --format=ids | awk '{print $1}')",
                "if [ -z \"$PID\" ]; then echo \"MISS|0\"; exit 0; fi",
                "wp post update \"$PID\" --post_date="
                + shlex.quote(dt_local)
                + " --post_date_gmt="
                + shlex.quote(dt_gmt)
                + " --edit_date=1 >/dev/null",
                "echo \"OK|$PID\"",
            ]
        )
        out = run_remote(
            host=args.ssh_host,
            port=args.ssh_port,
            user=args.ssh_user,
            password=args.ssh_password,
            command=script,
            timeout=1200,
        )
        status = "missing"
        wp_post_id = 0
        if "OK|" in out:
            status = "updated"
            try:
                wp_post_id = int(out.split("OK|", 1)[1].strip().splitlines()[0])
            except Exception:
                wp_post_id = 0
        results.append(
            {
                "id": item_id,
                "status": status,
                "wp_post_id": wp_post_id,
                "post_date": dt_local,
            }
        )

    report = {
        "timestamp": now_iso(),
        "themes_csv": args.themes_csv,
        "ids_total": len(ids),
        "updated": sum(1 for r in results if r["status"] == "updated"),
        "missing": sum(1 for r in results if r["status"] == "missing"),
        "results": results,
    }
    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(report_path, report)
    print(json.dumps({"updated": report["updated"], "missing": report["missing"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
