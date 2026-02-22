#!/usr/bin/env python3
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from content_sanitizer import build_content_package, sanitize_article_html, split_content_package


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_html(text: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate_chars(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip()
    return clipped.rstrip(" ,;:.")


def remove_external_links(html: str) -> Tuple[str, int]:
    count = 0

    def _replace_anchor(match: re.Match) -> str:
        nonlocal count
        count += 1
        return match.group(1)

    html = re.sub(
        r"<a[^>]*href=[\"'](?:https?:)?//[^\"']+[\"'][^>]*>([\s\S]*?)</a>",
        _replace_anchor,
        html,
        flags=re.I,
    )
    return html, count


def ensure_keyword_first_paragraph(html: str, keyword: str) -> Tuple[str, bool]:
    keyword = (keyword or "").strip()
    if not keyword:
        return html, False

    # Remove previously injected boilerplate keyword paragraphs from past reprocess runs.
    html = re.sub(
        r"<p>\s*<strong>[\s\S]*?</strong>\s*exige governanca de execucao,\s*leitura de dados e iteracao continua para gerar crescimento previsivel em 2026\.\s*</p>\s*",
        "",
        html,
        flags=re.I,
    )

    p_match = re.search(r"<p[^>]*>([\s\S]*?)</p>", html, flags=re.I)
    if p_match:
        first_par_text = strip_html(p_match.group(1)).lower()
        if keyword.lower() in first_par_text:
            return html, False

    sentence = (
        f"<p><strong>{keyword}</strong> exige governanca de execucao, leitura de dados e "
        "iteracao continua para gerar crescimento previsivel em 2026.</p>"
    )
    if p_match:
        html = html[: p_match.start()] + sentence + "\n" + html[p_match.start() :]
        return html, True

    h1_match = re.search(r"</h1>", html, flags=re.I)
    if h1_match:
        html = html[: h1_match.end()] + "\n" + sentence + html[h1_match.end() :]
    else:
        html = sentence + "\n" + html
    return html, True


def ensure_keyword_in_two_h2(html: str, keyword: str) -> Tuple[str, int]:
    keyword = (keyword or "").strip()
    if not keyword:
        return html, 0

    h2_pattern = re.compile(r"<h2[^>]*>([\s\S]*?)</h2>", flags=re.I)
    matches = list(h2_pattern.finditer(html))
    if not matches:
        insert_block = f"<h2>{keyword}: diretrizes de execucao</h2>\n<h2>{keyword}: plano de implementacao</h2>\n"
        p_match = re.search(r"<p[^>]*>[\s\S]*?</p>", html, flags=re.I)
        if p_match:
            html = html[: p_match.end()] + "\n" + insert_block + html[p_match.end() :]
        else:
            html = insert_block + html
        return html, 2

    count_with_kw = 0
    target_idxs: List[int] = []
    for idx, m in enumerate(matches):
        if keyword.lower() in strip_html(m.group(1)).lower():
            count_with_kw += 1
        else:
            target_idxs.append(idx)

    needed = max(0, 2 - count_with_kw)
    if needed == 0:
        return html, 0

    chosen = set(target_idxs[:needed])
    edit_count = 0
    cursor = 0
    parts: List[str] = []
    for idx, m in enumerate(matches):
        parts.append(html[cursor : m.start()])
        inner = m.group(1)
        if idx in chosen:
            inner_text = strip_html(inner).strip()
            if inner_text:
                inner = f"{inner} - {keyword}"
            else:
                inner = keyword
            edit_count += 1
        parts.append(f"<h2>{inner}</h2>")
        cursor = m.end()
    parts.append(html[cursor:])
    html = "".join(parts)

    # Still below threshold because there were fewer than 2 H2 blocks.
    final_count = sum(
        1 for x in re.findall(r"<h2[^>]*>([\s\S]*?)</h2>", html, flags=re.I)
        if keyword.lower() in strip_html(x).lower()
    )
    if final_count < 2:
        missing = 2 - final_count
        extra = "\n".join(f"<h2>{keyword}: bloco adicional {i+1}</h2>" for i in range(missing))
        p_match = re.search(r"<p[^>]*>[\s\S]*?</p>", html, flags=re.I)
        if p_match:
            html = html[: p_match.end()] + "\n" + extra + "\n" + html[p_match.end() :]
        else:
            html = extra + "\n" + html
        edit_count += missing

    return html, edit_count


def normalize_meta_from_block(meta: str, fallback_title: str, fallback_desc: str) -> Tuple[str, str]:
    lines = [ln.strip() for ln in (meta or "").splitlines() if ln.strip()]
    meta_title = ""
    meta_description = ""
    for ln in lines:
        m1 = re.match(r"Meta Title\s*:\s*(.+)$", ln, flags=re.I)
        if m1:
            meta_title = m1.group(1).strip()
            continue
        m2 = re.match(r"Meta Description\s*:\s*(.+)$", ln, flags=re.I)
        if m2:
            meta_description = m2.group(1).strip()
            continue
    meta_title = meta_title or (fallback_title or "").strip()
    meta_description = meta_description or (fallback_desc or "").strip()
    return meta_title, meta_description


def process_rows(rows: List[dict]) -> Tuple[List[dict], Dict[str, object]]:
    out_rows: List[dict] = []
    report_items: List[dict] = []

    for row in rows:
        item_id = (row.get("id") or "").strip()
        keyword = (row.get("keyword_primaria") or "").strip()
        pkg = row.get("content_package", "") or ""

        meta_block, html, has_markers = split_content_package(pkg)
        meta_title, meta_description = normalize_meta_from_block(
            meta_block,
            row.get("meta_title", ""),
            row.get("meta_description", ""),
        )

        meta_title_before = meta_title
        meta_description_before = meta_description

        html = sanitize_article_html(html)
        html, removed_external = remove_external_links(html)
        html, first_par_added = ensure_keyword_first_paragraph(html, keyword)
        html, h2_edits = ensure_keyword_in_two_h2(html, keyword)
        html = sanitize_article_html(html)

        meta_title = truncate_chars(meta_title, 60)
        meta_description = truncate_chars(meta_description, 155)

        new_meta = (
            f"Meta Title: {meta_title}\n"
            f"Meta Description: {meta_description}"
        )
        new_pkg = build_content_package(new_meta, html, with_markers=has_markers or bool(new_meta))

        nr = dict(row)
        nr["content_package"] = new_pkg
        nr["meta_title"] = meta_title
        nr["meta_description"] = meta_description
        out_rows.append(nr)

        report_items.append(
            {
                "id": item_id,
                "removed_external_links": removed_external,
                "added_keyword_first_paragraph": bool(first_par_added),
                "h2_keyword_edits": int(h2_edits),
                "meta_title_trimmed": meta_title_before != meta_title,
                "meta_description_trimmed": meta_description_before != meta_description,
            }
        )

    summary = {
        "timestamp": now_iso(),
        "rows_total": len(rows),
        "rows_changed": sum(
            1 for x in report_items
            if x["removed_external_links"] or x["added_keyword_first_paragraph"] or x["h2_keyword_edits"]
            or x["meta_title_trimmed"] or x["meta_description_trimmed"]
        ),
        "items": report_items,
    }
    return out_rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-process article CSV for deterministic quality compliance.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--report-json", required=True)
    args = parser.parse_args()

    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    report_path = Path(args.report_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    out_rows, report = process_rows(rows)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows_total": report["rows_total"], "rows_changed": report["rows_changed"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
