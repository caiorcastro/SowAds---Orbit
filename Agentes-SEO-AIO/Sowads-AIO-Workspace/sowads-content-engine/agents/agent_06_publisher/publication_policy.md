# Publication Policy

## Modos de publicação
1. REST API (preferencial)
2. SSH/WP-CLI
3. WP-ALL-IMPORT

## Pré-condição obrigatória
Publicar somente se:
- `seo_geo_score >= 80`
- `similarity_score <= 60`
- sem reason code crítico

## Políticas de bloqueio
Bloquear item quando:
- falha de contrato
- falha de compliance
- falha de política de qualidade

## Test mode
- `test_mode=true` => status `dry_run`
- sem escrita real no WordPress
- logs e artefatos completos continuam obrigatórios

## Registro de publicação
Cada tentativa deve registrar:
- timestamp
- batch_id
- id
- version
- status final
- erro (se existir)
