#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple

from content_sanitizer import build_content_package, split_content_package


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def normalize(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_phrase(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if text:
        return text[0].upper() + text[1:]
    return text


def build_h1(row: dict) -> str:
    keyword = clean_phrase((row.get("keyword_primaria") or "").strip())
    title = clean_phrase((row.get("tema_principal") or "").strip())
    vertical = clean_phrase((row.get("vertical_alvo") or "negócios").strip())
    angle = clean_phrase((row.get("angulo_conteudo") or "Educacional").strip())
    item_id = (row.get("id") or title or keyword or "item").strip()

    anchor = keyword or title or "Estratégia digital"

    templates = [
        "{anchor}: guia prático para decisões de {vertical} em 2026",
        "Como aplicar {anchor} com método, governança e execução em 2026",
        "{anchor} na prática: framework para escalar com previsibilidade",
        "{anchor}: estratégia executável para ganho de performance em 2026",
        "Playbook {angle}: como transformar {anchor} em resultado recorrente",
        "{anchor}: do planejamento à operação com foco em ROI e eficiência",
    ]
    idx = int(hashlib.sha1(item_id.encode("utf-8")).hexdigest(), 16) % len(templates)
    h1 = templates[idx].format(anchor=anchor, vertical=vertical, angle=angle)
    h1 = re.sub(r"\s+", " ", h1).strip(" -")
    return h1


def replace_first_h1(html: str, new_h1: str) -> Tuple[str, bool]:
    match = re.search(r"(<h1\b[^>]*>)([\s\S]*?)(</h1>)", html or "", flags=re.I)
    if not match:
        return html, False
    replaced = html[: match.start()] + match.group(1) + new_h1 + match.group(3) + html[match.end() :]
    return replaced, True


def should_replace(title: str, h1: str, threshold: float) -> bool:
    nt = normalize(title)
    nh = normalize(h1)
    if not nt or not nh:
        return False
    if nt == nh:
        return True
    if nt in nh or nh in nt:
        return True
    ratio = SequenceMatcher(None, nt, nh).ratio()
    return ratio >= threshold


def process_file(path: Path, threshold: float) -> Dict[str, int]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    changed = 0
    candidate = 0
    total = len(rows)

    for row in rows:
        old = row.get("content_package", "") or ""
        meta, html, has_markers = split_content_package(old)
        match = re.search(r"<h1\b[^>]*>([\s\S]*?)</h1>", html, flags=re.I)
        if not match:
            continue
        old_h1 = re.sub(r"<[^>]+>", " ", match.group(1))
        old_h1 = re.sub(r"\s+", " ", old_h1).strip()
        title = (row.get("tema_principal") or "").strip()
        if not should_replace(title, old_h1, threshold):
            continue
        candidate += 1
        new_h1 = build_h1(row)
        if normalize(new_h1) == normalize(old_h1):
            continue
        new_html, ok = replace_first_h1(html, new_h1)
        if not ok:
            continue
        row["content_package"] = build_content_package(meta, new_html, with_markers=has_markers or bool(meta))
        changed += 1

    if changed:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    return {"rows": total, "candidates": candidate, "changed_rows": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite first H1 when too similar to article title.")
    parser.add_argument(
        "--articles-dir",
        default="Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/outputs/articles",
    )
    parser.add_argument("--threshold", type=float, default=0.88)
    parser.add_argument(
        "--report-json",
        default="Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/outputs/reports/h1_similarity_repair_report.json",
    )
    args = parser.parse_args()

    articles_dir = Path(args.articles_dir)
    files = sorted(articles_dir.glob("*.csv"))

    summary = {
        "timestamp": now_stamp(),
        "threshold": args.threshold,
        "articles_dir": str(articles_dir),
        "files_total": len(files),
        "files_changed": 0,
        "rows_total": 0,
        "candidate_rows": 0,
        "rows_changed": 0,
        "files": [],
    }

    for fp in files:
        result = process_file(fp, args.threshold)
        summary["rows_total"] += result["rows"]
        summary["candidate_rows"] += result["candidates"]
        summary["rows_changed"] += result["changed_rows"]
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
