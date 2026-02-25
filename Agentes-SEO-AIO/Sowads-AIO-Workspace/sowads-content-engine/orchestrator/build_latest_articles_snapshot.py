#!/usr/bin/env python3
import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


def parse_batch_rank(name: str) -> int:
    # Prefer semantic timestamp from file name when present.
    m = re.search(r"(20\d{6}-\d{6})", name)
    if m:
        raw = m.group(1).replace("-", "")
        try:
            return int(raw)
        except Exception:
            pass
    return 0


def parse_version(value: str) -> int:
    try:
        return int(str(value).strip() or "0")
    except Exception:
        return 0


def collect_rows(files: List[Path]) -> Dict[str, Tuple[Tuple[int, int, int], dict]]:
    by_id: Dict[str, Tuple[Tuple[int, int, int], dict]] = {}
    for idx, path in enumerate(files):
        rank = parse_batch_rank(path.name)
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = (row.get("id") or "").strip()
                if not item_id:
                    continue
                version = parse_version(row.get("version", "0"))
                key = (rank, version, idx)
                prev = by_id.get(item_id)
                if (not prev) or key >= prev[0]:
                    by_id[item_id] = (key, row)
    return by_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one deduplicated latest-article CSV by content id.")
    parser.add_argument("--articles-dir", default="outputs/articles")
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    articles_dir = Path(args.articles_dir)
    files = sorted(articles_dir.glob("BATCH-*_articles*.csv"))
    if not files:
        raise SystemExit(f"No article csv files found in {articles_dir}")

    latest = collect_rows(files)
    rows = [v[1] for v in latest.values()]
    rows.sort(key=lambda r: (r.get("batch_id", ""), r.get("id", "")))

    fieldnames = [
        "batch_id",
        "id",
        "version",
        "tema_principal",
        "keyword_primaria",
        "keywords_secundarias",
        "porte_empresa_alvo",
        "modelo_negocio_alvo",
        "vertical_alvo",
        "produto_sowads_foco",
        "angulo_conteudo",
        "url_interna",
        "slug",
        "meta_title",
        "meta_description",
        "content_package",
        "status",
    ]

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})

    stamp = datetime.now(timezone.utc).isoformat()
    print(
        f"snapshot_created_at={stamp} files_scanned={len(files)} unique_ids={len(rows)} output={output_csv}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
