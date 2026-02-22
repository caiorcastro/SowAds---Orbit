#!/usr/bin/env python3
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from content_sanitizer import build_content_package, split_content_package


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def detect_issues(content_package: str) -> Dict[str, bool]:
    content_package = content_package or ""
    if "=== HTML PACKAGE — WORDPRESS READY ===" in content_package:
        html = content_package.split("=== HTML PACKAGE — WORDPRESS READY ===", 1)[1]
    else:
        i = content_package.lower().find("<article")
        html = content_package[i:] if i >= 0 else content_package
    flags = {
        "after_article_garbage": False,
        "fence_inside_html": "```" in html,
        "equals_tail_inside_html": "=======================================" in html,
        "repeated_trailing_paragraph": False,
    }

    idx = html.lower().rfind("</article>")
    if idx >= 0 and html[idx + len("</article>") :].strip():
        flags["after_article_garbage"] = True

    paras = re.findall(r"<p[^>]*>([\s\S]*?)</p>", html, flags=re.I)
    if len(paras) >= 2:
        a = re.sub(r"<[^>]+>", " ", paras[-1]).strip().lower()
        b = re.sub(r"<[^>]+>", " ", paras[-2]).strip().lower()
        a = re.sub(r"\s+", " ", a)
        b = re.sub(r"\s+", " ", b)
        if a and b and a == b and len(a) >= 40:
            flags["repeated_trailing_paragraph"] = True
    return flags


def row_to_package(row: dict) -> str:
    old = row.get("content_package", "") or ""
    meta, html, has_markers = split_content_package(old)
    meta = meta.strip()

    if not meta:
        mt = (row.get("meta_title", "") or "").strip()
        md = (row.get("meta_description", "") or "").strip()
        meta_lines: List[str] = []
        if mt:
            meta_lines.append(f"Meta Title: {mt}")
        if md:
            meta_lines.append(f"Meta Description: {md}")
        meta = "\n".join(meta_lines).strip()

    # Always persist in canonical two-block format.
    return build_content_package(meta, html, with_markers=True if (has_markers or html) else False)


def process_file(path: Path) -> Dict[str, int]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = rows[0].keys() if rows else []

    changed = 0
    before_issue_count = 0
    after_issue_count = 0

    for row in rows:
        old = row.get("content_package", "") or ""
        before_flags = detect_issues(old)
        if any(before_flags.values()):
            before_issue_count += 1

        new = row_to_package(row)
        after_flags = detect_issues(new)
        if any(after_flags.values()):
            after_issue_count += 1

        if new != old:
            row["content_package"] = new
            changed += 1

    if changed > 0:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(fieldnames))
            w.writeheader()
            w.writerows(rows)

    return {
        "rows": len(rows),
        "changed_rows": changed,
        "issue_rows_before": before_issue_count,
        "issue_rows_after": after_issue_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair malformed article content_package fields in CSV outputs.")
    parser.add_argument(
        "--articles-dir",
        default="Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/outputs/articles",
        help="Directory containing *_articles*.csv files.",
    )
    parser.add_argument(
        "--report-json",
        default="Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/outputs/reports/article_package_repair_report.json",
        help="Path to write repair report JSON.",
    )
    args = parser.parse_args()

    articles_dir = Path(args.articles_dir)
    files = sorted(articles_dir.glob("*.csv"))
    summary = {
        "timestamp": now_stamp(),
        "articles_dir": str(articles_dir),
        "files_total": len(files),
        "files_changed": 0,
        "rows_total": 0,
        "rows_changed": 0,
        "issue_rows_before": 0,
        "issue_rows_after": 0,
        "files": [],
    }

    for fp in files:
        result = process_file(fp)
        summary["rows_total"] += result["rows"]
        summary["rows_changed"] += result["changed_rows"]
        summary["issue_rows_before"] += result["issue_rows_before"]
        summary["issue_rows_after"] += result["issue_rows_after"]
        if result["changed_rows"] > 0:
            summary["files_changed"] += 1
        summary["files"].append({"file": fp.name, **result})

    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
