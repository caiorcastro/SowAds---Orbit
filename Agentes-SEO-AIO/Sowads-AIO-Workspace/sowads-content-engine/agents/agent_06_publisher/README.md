# Agent 06 — Publisher

## Missão
Publicar conteúdo aprovado no WordPress (ou dry-run) com rastreabilidade por ID/version.

## Pré-condições
- `seo_geo_score >= 80`
- `similarity_score <= 60`
- sem reason code crítico

## Entrada
- `articles_vN.csv`
- `seo_audit.json`
- `similarity_report.json`

## Saída
`publish_results.json` com arrays `published` e `failed`.

## Política operacional
- Itens fora da política entram em `failed` com motivo `blocked_by_policy`.
- Em `test_mode`, saída é `dry_run`, sem publicação real.

## Rastreamento
- `data/logs/publication_log.jsonl` deve registrar status por item.
- Todo item publicado deve preservar `id` e `version` em metadados WP quando integração real estiver ativa.

## Execução isolada
```bash
python orchestrator/run_pipeline.py \
  --agent agent06 \
  --articles-file data/batches/BATCH-.../articles_v1.csv \
  --audit-file data/batches/BATCH-.../seo_audit.json \
  --similarity-file data/batches/BATCH-.../similarity_report.json \
  --async-output
```
