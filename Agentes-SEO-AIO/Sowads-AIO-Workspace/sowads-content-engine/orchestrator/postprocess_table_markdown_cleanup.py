#!/usr/bin/env python3
import argparse
import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from content_sanitizer import build_content_package, sanitize_meta_block, split_content_package


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_html(text: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_markdown_bold(text: str) -> Tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        inner = m.group(1).strip()
        if not inner:
            return ""
        return f"<strong>{inner}</strong>"

    text = re.sub(r"(?<!\*)\*\*([^*][\s\S]*?)\*\*(?!\*)", repl, text)
    orphan = text.count("**")
    if orphan:
        text = text.replace("**", "")
    return text, count + orphan


def compact_text(raw: str, max_chars: int, max_words: int) -> Tuple[str, bool]:
    txt = strip_html(raw)
    if not txt:
        return "", False
    txt = txt.replace('"', "").replace("“", "").replace("”", "").replace("'", "")
    words = txt.split()
    changed = False
    if len(words) > max_words:
        txt = " ".join(words[:max_words])
        changed = True
    if len(txt) > max_chars:
        txt = txt[:max_chars].rstrip()
        if " " in txt:
            txt = txt.rsplit(" ", 1)[0].rstrip()
        changed = True
    txt = txt.rstrip(" ,;:")
    if changed:
        txt = txt + "..."
    return html.escape(txt), changed


def compact_table_cells(html_body: str, th_max_chars: int, th_max_words: int, td_max_chars: int, td_max_words: int) -> Tuple[str, int]:
    edits = 0

    def repl(m: re.Match) -> str:
        nonlocal edits
        tag = m.group(1).lower()
        attrs = m.group(2) or ""
        inner = m.group(3) or ""
        if tag == "th":
            new_inner, changed = compact_text(inner, th_max_chars, th_max_words)
        else:
            new_inner, changed = compact_text(inner, td_max_chars, td_max_words)
        if changed:
            edits += 1
        else:
            # also normalize accidental markdown markers even without truncation
            cleaned, md_changed = normalize_markdown_bold(inner)
            if md_changed:
                edits += 1
                new_inner = cleaned
            else:
                new_inner = inner
        return f"<{tag}{attrs}>{new_inner}</{tag}>"

    pattern = re.compile(r"<(td|th)([^>]*)>([\s\S]*?)</\1>", flags=re.I)
    return pattern.sub(repl, html_body), edits


def process_csv(
    input_csv: Path,
    output_csv: Path,
    report_json: Path,
    th_max_chars: int,
    th_max_words: int,
    td_max_chars: int,
    td_max_words: int,
) -> None:
    with input_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    out_rows = []
    report_items: List[dict] = []

    for row in rows:
        item_id = (row.get("id") or "").strip()
        package = row.get("content_package", "") or ""
        meta, html_body, has_markers = split_content_package(package)

        html_body, md_changes_html = normalize_markdown_bold(html_body)
        html_body, table_edits = compact_table_cells(
            html_body,
            th_max_chars=th_max_chars,
            th_max_words=th_max_words,
            td_max_chars=td_max_chars,
            td_max_words=td_max_words,
        )
        html_body, md_changes_html_2 = normalize_markdown_bold(html_body)

        meta, md_changes_meta = normalize_markdown_bold(meta)
        meta = sanitize_meta_block(meta)

        # keep dedicated columns clean as well
        meta_title = row.get("meta_title", "") or ""
        meta_desc = row.get("meta_description", "") or ""
        meta_title, md_title = normalize_markdown_bold(meta_title)
        meta_desc, md_desc = normalize_markdown_bold(meta_desc)

        new_pkg = build_content_package(meta, html_body, with_markers=has_markers or bool(meta))
        nr = dict(row)
        nr["content_package"] = new_pkg
        nr["meta_title"] = meta_title
        nr["meta_description"] = meta_desc
        out_rows.append(nr)

        total_md = md_changes_html + md_changes_html_2 + md_changes_meta + md_title + md_desc
        report_items.append(
            {
                "id": item_id,
                "table_cells_compacted": int(table_edits),
                "markdown_markers_fixed": int(total_md),
                "changed": bool(table_edits or total_md),
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    summary = {
        "timestamp": now_iso(),
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "rows_total": len(rows),
        "rows_changed": sum(1 for x in report_items if x["changed"]),
        "items": report_items,
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows_total": summary["rows_total"], "rows_changed": summary["rows_changed"]}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup markdown ** markers and compact long table cell text in article CSV.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--report-json", required=True)
    parser.add_argument("--th-max-chars", type=int, default=42)
    parser.add_argument("--th-max-words", type=int, default=7)
    parser.add_argument("--td-max-chars", type=int, default=88)
    parser.add_argument("--td-max-words", type=int, default=14)
    args = parser.parse_args()

    process_csv(
        input_csv=Path(args.input_csv),
        output_csv=Path(args.output_csv),
        report_json=Path(args.report_json),
        th_max_chars=args.th_max_chars,
        th_max_words=args.th_max_words,
        td_max_chars=args.td_max_chars,
        td_max_words=args.td_max_words,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
