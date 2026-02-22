#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
from pathlib import Path

from content_sanitizer import build_content_package, sanitize_article_html, split_content_package


def normalize_text(text: str) -> str:
    mapping = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñ",
        "aaaaaeeeeiiiiooooouuuucn",
    )
    text = (text or "").lower().translate(mapping)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def count_words(text: str) -> int:
    norm = normalize_text(text)
    if not norm:
        return 0
    return len(norm.split())


def phrase_occurrences(text: str, phrase: str) -> int:
    t = normalize_text(text).split()
    p = normalize_text(phrase).split()
    if not p or len(p) > len(t):
        return 0
    size = len(p)
    total = 0
    for i in range(0, len(t) - size + 1):
        if t[i : i + size] == p:
            total += 1
    return total


def keyword_density_pct(text: str, keyword: str) -> float:
    words = count_words(text)
    if words <= 0:
        return 0.0
    kw_tokens = normalize_text(keyword).split()
    if not kw_tokens:
        return 0.0
    occ = phrase_occurrences(text, keyword)
    covered = occ * len(kw_tokens)
    return (covered / words) * 100.0


def strip_html(html: str) -> str:
    html = html or ""
    html = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html


def extract_html_from_package(content_package: str) -> str:
    _, html, _ = split_content_package(content_package or "")
    return html


def inject_before_article_end(html: str, block: str) -> str:
    if not html:
        return block
    idx = html.lower().rfind("</article>")
    if idx == -1:
        return html.rstrip() + "\n" + block.strip() + "\n"
    return html[:idx].rstrip() + "\n" + block.strip() + "\n" + html[idx:]


def trim_to_max_words(html: str, max_words: int) -> str:
    if max_words <= 0:
        return html
    text = strip_html(html)
    if count_words(text) <= max_words:
        return html

    # Prefer removing trailing plain paragraphs (outside FAQ/scripts) to reduce fatigue.
    while count_words(strip_html(html)) > max_words:
        candidates = list(
            re.finditer(r"<p[^>]*>[\s\S]*?</p>", html, flags=re.I)
        )
        if not candidates:
            break

        removed = False
        for m in reversed(candidates):
            before = html[: m.start()]
            near = before[max(0, len(before) - 350) :].lower()
            if "<section" in near and "faq-section" in near:
                continue
            chunk = m.group(0).lower()
            if "<strong>faq" in chunk or "perguntas frequentes" in chunk:
                continue
            html = html[: m.start()] + html[m.end() :]
            removed = True
            break

        if not removed:
            break

    return html


def make_keyword_sentence(keyword: str, idx: int = 0) -> str:
    templates = [
        "Na operação diária, <strong>{kw}</strong> precisa ser monitorada com ticket médio, margem e taxa de retorno para orientar decisões com previsibilidade.",
        "Com rotina semanal, <strong>{kw}</strong> deve ser avaliada junto de CAC, conversão e receita incremental para calibrar investimento com segurança.",
        "Em cenários competitivos, <strong>{kw}</strong> ganha eficiência quando conectada a metas de margem, velocidade comercial e qualidade de lead.",
        "Para reduzir desperdício, <strong>{kw}</strong> precisa entrar no painel executivo com leitura por canal, região e estágio da jornada.",
        "Quando a equipe acompanha <strong>{kw}</strong> com critérios financeiros e operacionais, o planejamento fica mais assertivo e sustentável.",
        "Resultados consistentes exigem que <strong>{kw}</strong> seja tratada como métrica de negócio, não apenas como número isolado de mídia.",
    ]
    return f"<p>{templates[idx % len(templates)].format(kw=keyword)}</p>"


def make_neutral_paragraph(idx: int = 0) -> str:
    templates = [
        "Para sustentar crescimento previsível, o time precisa manter governança de dados, rotina de testes controlados, padronização de naming e análise semanal por canal, região, produto e estágio da jornada.",
        "Com processos claros e documentação contínua, a operação ganha consistência, reduz ruído e acelera decisões táticas sem comprometer o planejamento estratégico.",
        "A integração entre conteúdo, mídia e BI melhora a leitura de causalidade, facilita priorização de hipóteses e reduz desperdícios recorrentes ao longo do trimestre.",
        "Equipes que operam com checklist técnico e ritos de revisão conseguem evoluir criativos, ofertas e segmentações de forma contínua e mensurável.",
        "Sem disciplina operacional, o volume cresce mais rápido que a qualidade; por isso, governança editorial e análise de performance devem caminhar juntas.",
        "Uma cadência de melhoria contínua, com indicadores compartilhados entre marketing e vendas, aumenta previsibilidade e protege margem mesmo em cenários voláteis.",
    ]
    return f"<p>{templates[idx % len(templates)]}</p>"


def replace_html_in_package(content_package: str, new_html: str) -> str:
    meta, _, has_markers = split_content_package(content_package or "")
    return build_content_package(meta, new_html, with_markers=has_markers or bool(meta))


def enforce_row(
    row: dict,
    min_words: int,
    max_words: int,
    density_min: float,
    density_max: float,
    density_target_low: float,
    density_target_high: float,
) -> tuple[dict, dict]:
    keyword = (row.get("keyword_primaria") or "").strip()
    package = row.get("content_package", "")
    html = extract_html_from_package(package)

    text = strip_html(html)
    wc = count_words(text)
    dens = keyword_density_pct(text, keyword)
    kw_tokens = len(normalize_text(keyword).split()) or 1
    neutral_idx = 0
    keyword_idx = 0

    if wc < min_words:
        missing = min_words - wc
        para = make_neutral_paragraph(neutral_idx)
        per_para_words = count_words(strip_html(para))
        n = max(1, math.ceil(missing / max(1, per_para_words)))
        paragraphs = []
        for _ in range(n):
            paragraphs.append(make_neutral_paragraph(neutral_idx))
            neutral_idx += 1
        html = inject_before_article_end(html, "\n".join(paragraphs))
        text = strip_html(html)
        wc = count_words(text)
        dens = keyword_density_pct(text, keyword)

    if dens < density_min:
        sent = make_keyword_sentence(keyword, keyword_idx)
        sent_words = count_words(strip_html(sent))
        current_covered = phrase_occurrences(text, keyword) * kw_tokens
        target = density_target_low / 100.0
        # (covered + m*kw_tokens) / (wc + m*sent_words) >= target
        num = (target * wc) - current_covered
        den = kw_tokens - (target * sent_words)
        m = 1 if den <= 0 else max(1, math.ceil(num / den))
        inserts = []
        for _ in range(m):
            inserts.append(make_keyword_sentence(keyword, keyword_idx))
            keyword_idx += 1
        html = inject_before_article_end(html, "\n".join(inserts))
        text = strip_html(html)
        wc = count_words(text)
        dens = keyword_density_pct(text, keyword)
        while dens < density_min:
            html = inject_before_article_end(html, make_keyword_sentence(keyword, keyword_idx))
            keyword_idx += 1
            text = strip_html(html)
            wc = count_words(text)
            dens = keyword_density_pct(text, keyword)

    if dens > density_max:
        para = make_neutral_paragraph(neutral_idx)
        para_words = count_words(strip_html(para))
        covered = phrase_occurrences(text, keyword) * kw_tokens
        target = density_target_high / 100.0
        need_words = max(0, math.ceil((covered / target) - wc))
        n = max(1, math.ceil(need_words / max(1, para_words)))
        inserts = []
        for _ in range(n):
            inserts.append(make_neutral_paragraph(neutral_idx))
            neutral_idx += 1
        html = inject_before_article_end(html, "\n".join(inserts))
        text = strip_html(html)
        wc = count_words(text)
        dens = keyword_density_pct(text, keyword)
        while dens > density_max:
            html = inject_before_article_end(html, make_neutral_paragraph(neutral_idx))
            neutral_idx += 1
            text = strip_html(html)
            wc = count_words(text)
            dens = keyword_density_pct(text, keyword)

    if wc > max_words:
        html = trim_to_max_words(html, max_words)
        text = strip_html(html)
        wc = count_words(text)
        dens = keyword_density_pct(text, keyword)

    html = sanitize_article_html(html)
    text = strip_html(html)
    wc = count_words(text)
    dens = keyword_density_pct(text, keyword)

    new_row = dict(row)
    new_row["content_package"] = replace_html_in_package(package, html)

    metrics = {
        "id": row.get("id", ""),
        "keyword_primaria": keyword,
        "word_count": wc,
        "keyword_density_pct": round(dens, 4),
        "ok": bool(min_words <= wc <= max_words and density_min <= dens <= density_max),
    }
    return new_row, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce word count and keyword density constraints on article CSV")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--report-json", required=True)
    parser.add_argument("--min-words", type=int, default=900)
    parser.add_argument("--max-words", type=int, default=1500)
    parser.add_argument("--density-min", type=float, default=1.5)
    parser.add_argument("--density-max", type=float, default=2.0)
    parser.add_argument("--target-low", type=float, default=1.7)
    parser.add_argument("--target-high", type=float, default=1.85)
    args = parser.parse_args()

    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    report_path = Path(args.report_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with in_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    adjusted = []
    metrics = []
    for row in rows:
        nr, m = enforce_row(
            row=row,
            min_words=args.min_words,
            max_words=args.max_words,
            density_min=args.density_min,
            density_max=args.density_max,
            density_target_low=args.target_low,
            density_target_high=args.target_high,
        )
        adjusted.append(nr)
        metrics.append(m)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(adjusted)

    summary = {
        "input_csv": str(in_path),
        "output_csv": str(out_path),
        "report_generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "constraints": {
            "min_words": args.min_words,
            "max_words": args.max_words,
            "density_min": args.density_min,
            "density_max": args.density_max,
        },
        "summary": {
            "total": len(metrics),
            "ok": sum(1 for x in metrics if x["ok"]),
            "failed": sum(1 for x in metrics if not x["ok"]),
            "min_word_count": min((x["word_count"] for x in metrics), default=0),
            "max_word_count": max((x["word_count"] for x in metrics), default=0),
            "min_density_pct": min((x["keyword_density_pct"] for x in metrics), default=0.0),
            "max_density_pct": max((x["keyword_density_pct"] for x in metrics), default=0.0),
            "avg_density_pct": round(
                (sum(x["keyword_density_pct"] for x in metrics) / len(metrics)) if metrics else 0.0,
                4,
            ),
        },
        "items": metrics,
    }
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
