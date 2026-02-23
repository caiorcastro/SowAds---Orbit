# Sowads Content Engine

Pipeline multiagente para produção, auditoria, imagem e publicação de conteúdo da Sowads em escala, com rastreabilidade completa por lote.

## 1) Objetivo

Este projeto existe para operar uma linha de produção editorial com padrão técnico e visual consistente, reduzindo retrabalho manual.

Resultados esperados por lote:
- temas gerados com briefing estruturado
- artigos WordPress-ready em pacote padronizado
- auditoria SEO/GEO/E-E-A-T com gates
- validação de similaridade/canibalização
- prompts de imagem e imagens geradas
- publicação no WordPress com logs e evidências

## 2) Arquitetura

Fluxo principal (`agent all`):
1. `agent01` temas
2. `agent02` artigos
3. `agent03` auditoria SEO/GEO
4. `agent04` similaridade
5. loop de rewrite seletivo (itens reprovados)
6. `agent05` prompts de imagem
7. render de imagens (`render_images.py`)
8. `agent06` publicação (`publish_wp_cli.py`)

Princípios:
- `system/system.md` e `system/user.md` são fonte de verdade
- determinístico antes de LLM-judge
- bloqueio por falha crítica
- logs reais por chamada e por publicação
- execução síncrona e assíncrona por agente

## 3) Estrutura de pastas

```text
sowads-content-engine/
├── agents/
│   ├── agent_01_theme_generator/
│   ├── agent_02_article_generator/
│   ├── agent_03_seo_audit/
│   ├── agent_04_similarity/
│   ├── agent_05_image_prompt/
│   └── agent_06_publisher/
├── data/
│   ├── batches/
│   ├── history/
│   ├── logs/
│   └── cache/
├── orchestrator/
│   ├── run_pipeline.py
│   ├── render_images.py
│   ├── publish_wp_cli.py
│   ├── enrich_readability_blocks.py
│   ├── enforce_batch_constraints.py
│   ├── repair_article_packages.py
│   └── repair_h1_similarity.py
├── outputs/
│   ├── themes/
│   ├── articles/
│   ├── audits/
│   ├── similarity/
│   ├── image-prompts/
│   ├── generated-images/
│   ├── publish-jobs/
│   ├── reports/
│   └── assincronos/
└── system/
    ├── system.md
    └── user.md
```

## 4) Requisitos

- Python 3.10+
- acesso às APIs (Gemini e/ou Replicate)
- acesso WordPress via SSH/WP-CLI para publicação

## 5) Configuração

Crie `.env.local` no diretório do engine.

Exemplo mínimo:

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash

# preços (opcional, para estimativa em log)
GEMINI_INPUT_COST_PER_1M=0
GEMINI_OUTPUT_COST_PER_1M=0

# replicate (imagem)
REPLICATE_API_TOKEN=...
REPLICATE_MODEL=black-forest-labs/flux-1.1-pro

# wordpress publication
WP_SSH_HOST=147.93.37.148
WP_SSH_PORT=65002
WP_SSH_USER=...
WP_SSH_PASSWORD=...
WP_PATH=/home/.../public_html
```

## 6) Contratos de dados

### 6.1 Themes CSV
Arquivo: `outputs/themes/{batch_id}_themes.csv`

Colunas:
- `id`
- `timestamp`
- `tema_principal`
- `keyword_primaria`
- `keywords_secundarias` (separadas por `|`)
- `porte_empresa_alvo`
- `modelo_negocio_alvo`
- `vertical_alvo`
- `produto_sowads_foco`
- `angulo_conteudo`
- `url_interna`
- `funil`
- `busca`
- `titulo_anuncio`
- `notes`

### 6.2 Articles CSV
Arquivo: `outputs/articles/{batch_id}_articles*.csv`

Campos-chave:
- `id`, `batch_id`, `version`
- `slug`, `meta_title`, `meta_description`
- `content_package`
- `status`

`content_package` é obrigatório com 2 blocos:
- `=== META INFORMATION ===`
- `=== HTML PACKAGE — WORDPRESS READY ===`

### 6.3 Status de artigo
- `APPROVED`: aprovado para publicação
- `PENDING_QA`: pendente de revisão/ajuste
- `REJECTED`: bloqueado por gates críticos

## 7) Gates de qualidade

Implementados no `agent03`/orquestrador:

Críticos (bloqueiam publicação):
- `missing_blocks`
- `meta_title_too_long`
- `meta_description_too_long`
- `meta_description_missing`
- `external_link`
- `invalid_slug`
- `body_h1_present`
- `faq_missing`
- `faq_answers_missing`
- `faq_html_semantic_missing`
- `article_schema_missing`
- `article_schema_incomplete`
- `temporal_incoherence`
- `malformed_tail`
- `repetitive_tail`
- `low_visual_structure`
- `visual_overload`
- `late_visual_structure`
- `long_paragraphs`
- `geo_block_weak`
- `cta_missing`
- `sources_missing`
- `bold_overuse`
- `fixed_blocks_detected`
- `repeated_structure_pattern`

Regras atuais relevantes de conteúdo:
- faixa de palavras configurável (operação atual: 900–1500)
- densidade de keyword por faixa de controle
- título do post (H1 WP) e Meta Title não podem ser praticamente idênticos
- estrutura visual obrigatória
  - usar 2 a 3 recursos entre: lista numerada, bullets, mini-checklist, tabela, blockquote e frases-âncora em negrito
  - primeiro elemento visual estrutural após o 2º, 3º ou 4º parágrafo
  - sem blocos fixos reaproveitados entre temas
  - tabela (quando houver) com bordas cinza e células objetivas

Regras anti-template IA:
- alternância de perfil estrutural por artigo (guia, diagnóstico, framework, playbook)
- banimento de moldes fixos repetidos em sequência
- penalidade de repetição em headings/padrões de seção
- parágrafos longos em série reduzem score e geram rewrite
- negrito limitado a termos críticos e decisão operacional

## 8) Logs e rastreabilidade

`data/logs/logs.jsonl`
- eventos de execução por fase (start/success/fail)

`data/logs/gemini_calls.jsonl`
- log real de chamadas Gemini
- inclui request hash/text, response raw/text, status HTTP, latência, usage, custo estimado

`data/logs/publication_log.jsonl`
- status por item publicado (created/updated/fail)

`outputs/publish-jobs/{PUB-ID}/`
- `items.json`
- `published_posts.csv`
- `publish_results_remote.json`

`outputs/reports/*gemini_review*.json`
- auditoria pós-publicação feita por Gemini (camada externa)
- resumo de score, risco de padrão IA e ações de melhoria

## 9) Execução

### 9.1 Pipeline completo

```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json
```

### 9.2 Pipeline completo em teste

```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json \
  --test-mode \
  --quantity 5
```

### 9.3 Agente isolado (assíncrono)

```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json \
  --agent agent03 \
  --articles-file data/batches/BATCH-.../articles_v1.csv \
  --async-output
```

Saída assíncrona:
- `outputs/assincronos/{agent}/{ASYNC-ID}/`

### 9.4 Gerar imagens

Último batch:

```bash
python orchestrator/render_images.py --base . --latest
```

Todos os batches:

```bash
python orchestrator/render_images.py --base . --all
```

### 9.5 Publicar no WordPress (SSH/WP-CLI)

```bash
python orchestrator/publish_wp_cli.py \
  --base . \
  --articles-csv outputs/articles/BATCH-..._articles_final.csv \
  --include-statuses APPROVED,PENDING_QA,REJECTED \
  --status publish \
  --ssh-host $WP_SSH_HOST \
  --ssh-port $WP_SSH_PORT \
  --ssh-user $WP_SSH_USER \
  --ssh-password "$WP_SSH_PASSWORD" \
  --wp-path $WP_PATH
```

## 10) Utilitários de manutenção

### 10.1 Enriquecer legibilidade (modo seguro)

```bash
python orchestrator/enrich_readability_blocks.py \
  --input-csv outputs/articles/PUBLISH-recent30-before-enrichment.csv \
  --output-csv outputs/articles/PUBLISH-recent30-enriched-v2.csv \
  --report-json outputs/reports/recent30_readability_enrichment_report_v2.json
```

Comportamento:
- padrão atual (sem `--inject`): remove o pack legado `sowads-readability-pack` se existir
- para inserir/reposicionar pack legado explicitamente (não recomendado):
  `python orchestrator/enrich_readability_blocks.py ... --inject`

### 10.2 Reforçar constraints de lote

```bash
python orchestrator/enforce_batch_constraints.py \
  --input-csv outputs/articles/BATCH-..._articles.csv \
  --output-csv outputs/articles/BATCH-..._articles_final.csv \
  --report-json outputs/reports/BATCH-..._constraints.json \
  --min-words 900 \
  --max-words 1500 \
  --density-min 1.5 \
  --density-max 2.0
```

### 10.3 Reparar pacote/artigo

```bash
python orchestrator/repair_article_packages.py ...
python orchestrator/repair_h1_similarity.py ...
```

## 11) Convenções de batch

Formato recomendado:
- `BATCH-{assunto}-{YYYYMMDD-HHMMSS}`

Exemplos:
- `BATCH-varejo-20260221-155713`
- `BATCH-automotivo-financeiro-20260221-172457`

## 12) Boas práticas operacionais

- não publicar lote sem auditar `outputs/audits` e `outputs/similarity`
- manter histórico atualizado para reduzir canibalização futura
- rodar em lotes menores quando o custo de imagem estiver alto
- sempre validar visual dos primeiros posts de cada lote antes de publicar em massa

## 13) Troubleshooting

### Falha de publicação por SSH
- valide host/porta/usuário/senha
- teste `wp --info` direto no servidor
- confira permissões em `wp-content/uploads`

### Artigo com estrutura quebrada
- rode `repair_article_packages.py`
- rode `enrich_readability_blocks.py` para reforçar estrutura visual

### Densidade fora do alvo
- rode `enforce_batch_constraints.py`
- verifique `keyword_primaria` e duplicidade de termo no H1/H2

### Similaridade alta
- execute rewrite seletivo só para IDs com `similarity_score > 60`

## 14) Segurança

- nunca versionar `.env.local`
- não hardcode de chave/API/senha
- logs de IA podem conter prompt/resposta completos: tratar como dados sensíveis

---

Se este README divergir de contrato técnico específico de um agente, prevalecem os arquivos em `agents/*` e `orchestrator/gates.md`.
