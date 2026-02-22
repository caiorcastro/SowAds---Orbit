# WordPress Fields Mapping

## Campos base
- `title`: derivado do título final do artigo
- `slug`: campo `slug` do contrato
- `content_html`: conteúdo HTML do pacote
- `status`: `draft|publish|dry_run`

## Taxonomia
- `categories`: padrão por vertical (quando configurado)
- `tags`: padrão do projeto + tags específicas do item

## Metadados técnicos
- `sowads_content_id`
- `sowads_content_version`
- `sowads_batch_id`

## SEO fields (quando plugin suportar)
- `meta_title`
- `meta_description`

## Regras de integridade
- Nunca publicar sem `id` e `version`.
- Nunca alterar `id` original em rewrite.
- Manter rastreio cruzado com `publish_results.json` e `publication_log.jsonl`.
