#!/usr/bin/env python3
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from content_sanitizer import build_content_package, split_content_package


BLOCK_ID = "sowads-readability-pack"


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _clean(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_pack(row: dict) -> str:
    tema = _clean(row.get("tema_principal", "")) or "estratégia digital"
    keyword = _clean(row.get("keyword_primaria", "")) or "performance digital"
    secondary = [s.strip() for s in _clean(row.get("keywords_secundarias", "")).split("|") if s.strip()]
    s1 = secondary[0] if len(secondary) > 0 else "intenção de busca"
    s2 = secondary[1] if len(secondary) > 1 else "eficiência de aquisição"
    s3 = secondary[2] if len(secondary) > 2 else "governança de execução"
    vertical = _clean(row.get("vertical_alvo", "")) or "negócios"
    angle = _clean(row.get("angulo_conteudo", "")) or "Educacional"
    product = _clean(row.get("produto_sowads_foco", "")) or "Ambos os pilares"

    return f"""
<section id="{BLOCK_ID}" class="sowads-readability-pack">
  <style>
    #{BLOCK_ID} {{
      margin: 28px 0 24px;
      padding: 20px 20px 12px;
      background: #f5f5f5;
      border-radius: 14px;
    }}
    #{BLOCK_ID} h2 {{
      margin: 0 0 12px;
      line-height: 1.2;
    }}
    #{BLOCK_ID} table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0 0 26px;
      table-layout: fixed;
    }}
    #{BLOCK_ID} th,
    #{BLOCK_ID} td {{
      border: 1px solid #b7b7b7;
      padding: 10px 12px;
      vertical-align: top;
      text-align: left;
      overflow-wrap: anywhere;
    }}
    #{BLOCK_ID} th {{
      background: #ececec;
      font-weight: 700;
    }}
    #{BLOCK_ID} ul,
    #{BLOCK_ID} ol {{
      margin: 0 0 22px 22px;
      padding: 0;
    }}
    #{BLOCK_ID} li {{
      margin: 0 0 8px;
    }}
  </style>
  <h2>Painel tático: {keyword}</h2>
  <table style="width:100%;border-collapse:collapse;margin:0 0 26px;table-layout:fixed;border:1px solid #b7b7b7;">
    <thead>
      <tr>
        <th style="border:1px solid #b7b7b7;padding:10px 12px;text-align:left;background:#ececec;">Frente</th>
        <th style="border:1px solid #b7b7b7;padding:10px 12px;text-align:left;background:#ececec;">Objetivo prático</th>
        <th style="border:1px solid #b7b7b7;padding:10px 12px;text-align:left;background:#ececec;">Indicador principal</th>
        <th style="border:1px solid #b7b7b7;padding:10px 12px;text-align:left;background:#ececec;">Ritmo de revisão</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Direção principal</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">{tema}</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Execução orientada por {keyword}</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Semanal</td>
      </tr>
      <tr>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Prioridade 1</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">{s1}</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Visibilidade qualificada em {vertical}</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Quinzenal</td>
      </tr>
      <tr>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Prioridade 2</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">{s2}</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Conversão, CAC e margem por canal</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Diária</td>
      </tr>
      <tr>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Prioridade 3</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">{s3}</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Qualidade editorial e previsibilidade operacional</td>
        <td style="border:1px solid #b7b7b7;padding:10px 12px;">Semanal</td>
      </tr>
    </tbody>
  </table>

  <h2>Resumo executivo em bullet points</h2>
  <ul>
    <li>Conecte <strong>{keyword}</strong> ao objetivo de negócio mais próximo de receita.</li>
    <li>Use <strong>{s1}</strong> para priorizar pauta com potencial real de conversão.</li>
    <li>Sincronize conteúdo e mídia com revisão humana para reduzir retrabalho.</li>
    <li>Monitore performance por unidade/canal em ciclos curtos de decisão.</li>
    <li>Ative <strong>{product}</strong> com governança para escalar sem perder padrão.</li>
  </ul>

  <h2>Checklist de execução (30 dias)</h2>
  <ol>
    <li>Mapear gargalos ligados a {keyword} e alinhar metas operacionais.</li>
    <li>Publicar conteúdo orientado por {s1} com escaneabilidade real.</li>
    <li>Distribuir e medir impacto em {s2} com leitura semanal.</li>
    <li>Ajustar backlog com base em dados de {s3} e custo incremental.</li>
  </ol>
</section>
""".strip()


def _insert_index_early(html: str) -> Tuple[int, str]:
    # Natural placement: after early paragraphs, avoiding intro wall of text.
    ps = list(re.finditer(r"<p[^>]*>[\s\S]*?</p>", html, flags=re.I))
    if len(ps) >= 2:
        return ps[1].end(), "inserted_after_second_paragraph"
    if len(ps) == 1:
        return ps[0].end(), "inserted_after_first_paragraph"

    # Fallback: before FAQ section.
    faq = re.search(r"<section[^>]*class=[\"'][^\"']*faq-section[^\"']*[\"'][^>]*>", html, flags=re.I)
    if faq:
        return faq.start(), "inserted_before_faq"

    end = re.search(r"</article>", html, flags=re.I)
    if end:
        return end.start(), "inserted_before_article_end"

    return len(html), "appended"


def inject_or_replace(html: str, block: str) -> Tuple[str, str]:
    html = html or ""
    marker = re.search(
        rf"<section[^>]*id=[\"']{BLOCK_ID}[\"'][^>]*>[\s\S]*?</section>",
        html,
        flags=re.I,
    )

    # Always reposition to an early/natural slot, even if block already exists.
    if marker:
        html = html[: marker.start()] + html[marker.end() :]

    insert_at, mode = _insert_index_early(html)
    if mode in {"inserted_after_second_paragraph", "inserted_after_first_paragraph"}:
        new_html = html[:insert_at].rstrip() + "\n\n" + block + "\n\n" + html[insert_at:].lstrip()
    elif mode == "appended":
        new_html = html.rstrip() + "\n\n" + block + "\n"
    else:
        new_html = html[:insert_at].rstrip() + "\n\n" + block + "\n\n" + html[insert_at:].lstrip()
    if marker:
        mode = "repositioned_" + mode
    return new_html, mode


def process_csv(input_csv: Path, output_csv: Path, inject: bool = False) -> dict:
    with input_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    changed = 0
    modes: Dict[str, int] = {}
    processed_rows: List[dict] = []

    for row in rows:
        old_package = row.get("content_package", "") or ""
        meta, html, has_markers = split_content_package(old_package)
        marker = re.search(
            rf"<section[^>]*id=[\"']{BLOCK_ID}[\"'][^>]*>[\s\S]*?</section>",
            html,
            flags=re.I,
        )
        if inject:
            block = build_pack(row)
            new_html, mode = inject_or_replace(html, block)
        else:
            if marker:
                new_html = html[: marker.start()] + html[marker.end() :]
                mode = "removed_legacy_pack"
            else:
                new_html = html
                mode = "unchanged_no_pack"
        modes[mode] = modes.get(mode, 0) + 1
        new_package = build_content_package(meta, new_html, with_markers=has_markers or bool(meta))
        if new_package != old_package:
            changed += 1
            row["content_package"] = new_package
        processed_rows.append(row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(processed_rows)

    return {
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "rows_total": len(rows),
        "rows_changed": changed,
        "modes": modes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich article HTML with readability blocks: table + bullets + checklist.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument(
        "--inject",
        action="store_true",
        help="Insere/reposiciona o pack legado de leitura. Padrão: apenas remove o pack legado, sem inserir.",
    )
    parser.add_argument(
        "--report-json",
        default="Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/outputs/reports/readability_enrichment_report.json",
    )
    args = parser.parse_args()

    report = process_csv(Path(args.input_csv), Path(args.output_csv), inject=bool(args.inject))
    report["timestamp"] = now_stamp()
    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
