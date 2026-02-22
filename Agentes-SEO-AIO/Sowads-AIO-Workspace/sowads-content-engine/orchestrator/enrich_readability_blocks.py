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
    keyword = _clean(row.get("keyword_primaria", "")) or "performance digital"
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
  <h2>Painel rápido de decisão</h2>
  <table>
    <thead>
      <tr>
        <th>Frente</th>
        <th>Objetivo prático</th>
        <th>Indicador principal</th>
        <th>Ritmo de revisão</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>{keyword}</td>
        <td>Transformar execução em ganho de resultado previsível</td>
        <td>CAC, CTR e conversão assistida</td>
        <td>Semanal</td>
      </tr>
      <tr>
        <td>SEO + IA Overviews</td>
        <td>Aumentar presença orgânica em {vertical}</td>
        <td>Impressões qualificadas e posição média</td>
        <td>Quinzenal</td>
      </tr>
      <tr>
        <td>Mídia paga</td>
        <td>Escalar aquisição sem perder margem</td>
        <td>CPA/ROAS por campanha</td>
        <td>Diária</td>
      </tr>
      <tr>
        <td>Operação editorial</td>
        <td>Garantir consistência de execução ({angle})</td>
        <td>Prazo, qualidade e retrabalho</td>
        <td>Semanal</td>
      </tr>
    </tbody>
  </table>

  <h2>Resumo executável em bullet points</h2>
  <ul>
    <li>Priorize temas com potencial real de negócio e não apenas volume de busca.</li>
    <li>Conecte conteúdo, mídia e dados na mesma leitura de performance.</li>
    <li>Use revisão humana para manter precisão, clareza e padrão de marca.</li>
    <li>Documente aprendizados para reduzir retrabalho e acelerar decisões.</li>
    <li>Ative {product} de forma integrada para ganhar velocidade com controle.</li>
  </ul>

  <h2>Checklist de implementação (30 dias)</h2>
  <ol>
    <li>Mapear lacunas de funil e definir metas objetivas por canal.</li>
    <li>Publicar blocos de conteúdo orientados por intenção e performance.</li>
    <li>Distribuir com mídia paga e monitorar sinais de eficiência.</li>
    <li>Ajustar backlog com base em dados de conversão e custo.</li>
  </ol>
</section>
""".strip()


def _insert_index_early(html: str) -> Tuple[int, str]:
    # Natural placement: early in article, before the second H2 if possible.
    h2s = list(re.finditer(r"<h2[^>]*>[\s\S]*?</h2>", html, flags=re.I))
    if len(h2s) >= 2:
        return h2s[1].start(), "inserted_before_second_h2"

    # Fallback: after the second paragraph in the introduction.
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


def process_csv(input_csv: Path, output_csv: Path) -> dict:
    with input_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    changed = 0
    modes: Dict[str, int] = {}
    processed_rows: List[dict] = []

    for row in rows:
        old_package = row.get("content_package", "") or ""
        meta, html, has_markers = split_content_package(old_package)
        block = build_pack(row)
        new_html, mode = inject_or_replace(html, block)
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
        "--report-json",
        default="Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/outputs/reports/readability_enrichment_report.json",
    )
    args = parser.parse_args()

    report = process_csv(Path(args.input_csv), Path(args.output_csv))
    report["timestamp"] = now_stamp()
    report_path = Path(args.report_json)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
