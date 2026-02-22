# Agent 04 — Similarity & Cannibalization

## Missão
Evitar duplicidade e canibalização entre artigos do lote e contra histórico.

## Escopo
- Similaridade textual local (jaccard + cosine).
- Sinal semântico por keyword/intenção.
- Classificação: `ok`, `risk`, `rewrite`.

## Entrada
- `articles_vN.csv`
- `data/history/history.jsonl`

## Saída
`similarity_report.json` com:
- `similarity_score`
- `status`
- `conflicts`
- `flag_similarity`
- `rewrite_guidance`

## Regras de decisão
- `> 60`: rewrite obrigatório.
- `40–60`: risco.
- `< 40`: ok.

## Boas práticas
- Conflitos precisam trazer `other_id` + score + motivo.
- Guidance de rewrite deve apontar exatamente como diferenciar ângulo e estrutura.

## Execução isolada
```bash
python orchestrator/run_pipeline.py \
  --agent agent04 \
  --articles-file data/batches/BATCH-.../articles_v1.csv \
  --async-output
```
