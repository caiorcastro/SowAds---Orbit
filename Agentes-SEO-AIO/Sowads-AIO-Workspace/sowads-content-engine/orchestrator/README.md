# Orchestrator — SOWADS Content Engine v8.0

## Objetivo
O orquestrador coordena a fábrica inteira de conteúdo (Agentes 01→06), garante contratos de dados, aplica gates de qualidade, executa rewrite seletivo e controla publicação.

## Princípios de arquitetura
- `system/system.md` e `system/user.md` são fonte da verdade editorial.
- Fail-safe por padrão: falha crítica bloqueia publicação.
- Determinístico antes de LLM: auditoria e similaridade rodam primeiro sem judge.
- Rastreabilidade total: toda fase gera artefato versionado + log estruturado.
- Execução dual: pipeline completo síncrono OU agente isolado em modo assíncrono.
- Geração anti-template por padrão: diversidade estrutural + critic-refine.
- `max_rewrites` default `0` para evitar loops de reescrita em lote.

## Modos de execução
### 1) Pipeline completo (`--agent all`)
- Ordem fixa: 01 temas → 02 artigos → 03 auditoria → 04 similaridade → loop rewrite seletivo → 05 image prompts → 06 publicação.
- Saída principal por batch em `data/batches/{batch_id}/`.

### 2) Agente isolado (`--agent agent0X`)
- Permite rodar somente um agente para operação pontual.
- Pode ler entradas já existentes (`--themes-file`, `--articles-file`, etc.).
- Se `--async-output`, copia artefatos para `outputs/assincronos/{agent}/{job_id}/` com `manifest.json`.

## CLI
### Pipeline completo
```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json
```

### Pipeline de teste
```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json \
  --test-mode \
  --quantity 5
```

### Agente isolado (assíncrono)
```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json \
  --agent agent03 \
  --articles-file data/batches/BATCH-YYYYMMDD-HHMMSS/articles_v1.csv \
  --async-output
```

### Render de imagens (a partir de `image-prompts`)
```bash
python orchestrator/render_images.py \
  --base . \
  --latest
```

Processamento de todos os batches:
```bash
python orchestrator/render_images.py \
  --base . \
  --all
```

### Snapshot deduplicado de artigos e ordenação CORE
```bash
python orchestrator/build_latest_articles_snapshot.py \
  --articles-dir outputs/articles \
  --output-csv outputs/articles/PUBLISH-all-latest.csv

python orchestrator/set_core_recency.py \
  --base . \
  --themes-csv outputs/themes/bet-igaming-core_30_fixed.csv \
  --ssh-host $WP_SSH_HOST \
  --ssh-port $WP_SSH_PORT \
  --ssh-user $WP_SSH_USER \
  --ssh-password "$WP_SSH_PASSWORD" \
  --wp-path $WP_SSH_WP_PATH
```

## Monitoramento em tempo real
### 1) Terminal live por agente
```bash
./orchestrator/monitor_agents.sh .
```

Com intervalo customizado (em segundos) e batch fixo:
```bash
./orchestrator/monitor_agents.sh . 3 BATCH-core30-refresh-20260227-185750
```

### 2) Snapshot único (JSON)
```bash
python orchestrator/agent_status.py --base . --format json
```

### 3) Dashboard web (auto-refresh)
```bash
python orchestrator/serve_agent_status.py --base . --host 127.0.0.1 --port 8787
```

Abrir no navegador:
- `http://127.0.0.1:8787/`
- API bruta: `http://127.0.0.1:8787/api/status`
- API para batch específico: `http://127.0.0.1:8787/api/status?batch=BATCH-...`

## Matriz de entradas por agente isolado
- `agent01`: usa apenas `config`.
- `agent02`: opcional `--themes-file`.
- `agent03`: obrigatório `--articles-file`.
- `agent04`: obrigatório `--articles-file`.
- `agent05`: obrigatório `--articles-file`.
- `agent06`: obrigatórios `--articles-file --audit-file --similarity-file`.

## Artefatos por fase
- Agente 01: `outputs/themes/{batch_id}_themes.csv`
- Agente 02: `outputs/articles/{batch_id}_articles_vN.csv` e `..._articles.csv`
- Agente 03: `outputs/audits/{batch_id}_seo_audit.json`
- Agente 04: `outputs/similarity/{batch_id}_similarity.json`
- Agente 05: `outputs/image-prompts/{batch_id}_image_prompts.csv`
- Agente 06: `outputs/published/{batch_id}_publish_results.json`

## Logs operacionais
- `data/logs/logs.jsonl`: eventos de pipeline/fases.
- `data/logs/gemini_calls.jsonl`: telemetria real de chamadas Gemini (request/response/status/latência/tokens/custo estimado).
- `data/logs/publication_log.jsonl`: status de publicação por item.
- `outputs/generated-images/{batch_id}/...`: imagens geradas + `*_images_manifest.csv`.

## Regras de publicação
Publicação só acontece quando:
- `seo_geo_score >= 80`
- `similarity_score <= 60`
- sem `reason_code` crítico

Caso contrário, item vai para bloqueio de política.

## Governança de erro
- Erro em chamada LLM gera log detalhado e fallback local apenas quando permitido pelo modo.
- Erro de contrato (arquivo obrigatório ausente) encerra execução com mensagem explícita.
- Dados incompletos para publicação bloqueiam `agent06`.
- Erros transitórios da API Gemini são tratados com retry e telemetria completa de cada tentativa.

## Observações de segurança
- Nunca logar credenciais.
- Prompts e respostas podem ser extensos em `gemini_calls.jsonl`; trate este arquivo como dado sensível de operação.
