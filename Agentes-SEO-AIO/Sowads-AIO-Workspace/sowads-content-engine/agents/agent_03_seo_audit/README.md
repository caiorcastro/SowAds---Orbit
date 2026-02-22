# Agent 03 — SEO/GEO/E-E-A-T Auditor

## Missão
Avaliar conformidade técnica/editorial do artigo e decidir se o item segue ou volta para rewrite.

## Escopo
- Gate A determinístico (bloqueante).
- Gate B heurístico (score).
- Geração de `reason_codes`, `issues` e `rewrite_guidance`.

## Entrada
`articles_vN.csv`

## Saída
`seo_audit.json` com:
- `seo_geo_score`
- `flags.flag_rewrite`
- `flags.reason_codes`
- `issues`
- `rewrite_guidance`

## Regras de decisão
- Score alvo: `>= 80`.
- Qualquer reason code crítico => bloqueio para publicação.
- Guidance deve ser objetivo e acionável (não genérico).

## Motivos comuns de reprovação
- Falta de bloco obrigatório.
- Meta fora do limite.
- H1 inválido.
- Links externos.
- FAQ/schema ausentes.
- incoerência temporal.

## Execução isolada
```bash
python orchestrator/run_pipeline.py \
  --agent agent03 \
  --articles-file data/batches/BATCH-.../articles_v1.csv \
  --async-output
```
