# Contratos de Dados — SOWADS Content Engine v8.0

## Convenções de identificação
- `batch_id`: `BATCH-YYYYMMDD-HHMMSS`
- `id`: `SOWADS-YYYYMMDD-HHMMSS-RANDOM6`
- `version`: inteiro incremental por item

## Estrutura canônica por batch
Diretório: `data/batches/{batch_id}/`
- `themes.csv`
- `articles_v{N}.csv`
- `seo_audit.json`
- `similarity_report.json`
- `image_prompts.csv`
- `publish_results.json`
- `summary.json`

## CSV — themes.csv
Ordem fixa:
`id,timestamp,tema_principal,keyword_primaria,keywords_secundarias,porte_empresa_alvo,modelo_negocio_alvo,vertical_alvo,produto_sowads_foco,angulo_conteudo,url_interna,funil,busca,titulo_anuncio,notes`

Regras:
- `keywords_secundarias` separadas por `|`
- `funil`: `TOFU|MOFU|BOFU`
- `busca`: `Alta|Média|Baixa`

## CSV — articles_vN.csv
Ordem fixa:
`batch_id,id,version,tema_principal,keyword_primaria,keywords_secundarias,porte_empresa_alvo,modelo_negocio_alvo,vertical_alvo,produto_sowads_foco,angulo_conteudo,url_interna,slug,meta_title,meta_description,content_package,status`

Regras:
- `content_package` deve conter os 2 blocos mandatórios do v8.0
- `slug` em kebab-case
- `status`: `PENDING_QA|APPROVED|REJECTED`

## JSON — seo_audit.json
```json
{
  "batch_id": "...",
  "threshold": 80,
  "items": [
    {
      "id": "...",
      "version": 1,
      "seo_geo_score": 86,
      "flags": {"flag_rewrite": false, "reason_codes": []},
      "issues": [],
      "rewrite_guidance": ""
    }
  ]
}
```

## JSON — similarity_report.json
```json
{
  "batch_id": "...",
  "policy": {"risk_threshold": 40, "rewrite_threshold": 60},
  "items": [
    {
      "id": "...",
      "version": 1,
      "similarity_score": 31.2,
      "status": "ok",
      "conflicts": [],
      "flag_similarity": false,
      "rewrite_guidance": ""
    }
  ]
}
```

## CSV — image_prompts.csv
Ordem fixa:
`id,article_title,slug,dimensions,style,prompt,negative_prompt`

Regra de vínculo:
- `id` deve corresponder ao mesmo `id` do artigo em `articles_vN.csv`.

## Render de imagem (bitmap) — generated-images
Diretório:
- `outputs/generated-images/{batch_id}/`

Arquivos:
- `{id}_{NN}.png|jpg|webp` (imagens)
- `{batch_id}_images_manifest.csv` (status por prompt)

Manifest columns:
`id,article_title,slug,status,images_saved,primary_image,output_dir,error`

## JSON — publish_results.json
```json
{
  "batch_id": "...",
  "published": [
    {"id": "...", "version": 1, "wp_post_id": 0, "status": "dry_run", "timestamp": "..."}
  ],
  "failed": [
    {"id": "...", "version": 1, "error": "blocked_by_policy", "timestamp": "..."}
  ]
}
```

## Logs — data/logs/logs.jsonl
Cada linha:
- `timestamp`
- `phase`
- `batch_id`
- `id`
- `version`
- `status`
- `reason`
- `metrics`
- `model`

## Logs reais Gemini — data/logs/gemini_calls.jsonl
Cada linha representa 1 chamada real de API:
- `timestamp`, `completed_at`, `latency_ms`
- `provider`, `model`, `phase`, `agent`, `batch_id`, `id`, `version`
- `http_status_code`, `success`, `endpoint`
- `request.temperature`, `request.prompt_sha256`, `request.prompt_text`
- `response_raw`, `response_text`, `usage_metadata`
- `cost_estimate` (estimado)
- `error`

Importante:
- Apenas custo é estimado.
- Status, horário, payload e resposta são dados reais da chamada.

## Saída assíncrona por agente
Diretório: `outputs/assincronos/{agent}/{job_id}/`
- cópia dos artefatos gerados
- `manifest.json` com metadados da execução
