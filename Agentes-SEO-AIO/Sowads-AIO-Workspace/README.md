# Sowads AIO Workspace

Workspace oficial da fábrica de conteúdo SEO/AIO da Sowads.

Este documento é a referência operacional completa para entender:
- o que cada arquivo faz
- como a linha de produção se comporta
- quais melhorias já foram incorporadas
- como operar, auditar, corrigir e publicar com previsibilidade

---

## 1) Visão Geral

A estrutura foi desenhada em duas camadas:

1. `claude/system/` (governança e referência histórica de instruções)
2. `sowads-content-engine/` (execução real da linha de produção)

Objetivo principal:
- transformar temas em artigos publicados com qualidade técnica, SEO/GEO, consistência visual e rastreabilidade ponta a ponta.

---

## 2) Mapa da Estrutura

```text
Sowads-AIO-Workspace/
├── .env.example
├── README.md
├── common.py
├── claude/
│   └── system/
│       ├── manual-de-orquestração.md
│       ├── system.md
│       └── user.md
└── sowads-content-engine/
    ├── .env.example
    ├── README.md
    ├── system/
    │   ├── system.md
    │   └── user.md
    ├── agents/
    ├── orchestrator/
    ├── data/
    └── outputs/
```

---

## 3) Responsabilidade por Bloco

| Bloco | Papel | Resultado esperado |
|---|---|---|
| `claude/system/*` | Governança e histórico de direção | Referência estratégica do comportamento desejado |
| `sowads-content-engine/system/*` | Prompt efetivo da produção | Regras editoriais vigentes |
| `sowads-content-engine/agents/*` | Contratos por agente | Critérios claros de entrada e saída |
| `sowads-content-engine/orchestrator/*` | Execução da esteira + reparo + publicação | Operação reproduzível |
| `sowads-content-engine/data/*` | Estado runtime (logs/cache/histórico) | Observabilidade e memória operacional |
| `sowads-content-engine/outputs/*` | Artefatos produzidos por lote | Evidências de execução |

---

## 4) Inventário Arquivo a Arquivo (Workspace)

## 4.1 Raiz do workspace

| Arquivo | Função | Quando alterar |
|---|---|---|
| `.env.example` | Exemplo de variáveis comuns de ambiente | Sempre que nova integração exigir variável |
| `README.md` | Este manual principal | Sempre que fluxo, contratos ou naming mudarem |
| `common.py` | Utilitários legados compartilhados | Apenas se houver reaproveitamento real |

## 4.2 `claude/system/`

| Arquivo | Função | Observação |
|---|---|---|
| `manual-de-orquestração.md` | Especificação macro do desenho de fábrica | Fonte histórica da arquitetura |
| `system.md` | Prompt base legado | Referência, não é necessariamente o prompt em produção |
| `user.md` | Template legado de requisição | Apoio para parametrização |

---

## 5) Inventário Arquivo a Arquivo (Engine)

## 5.1 `sowads-content-engine/` raiz

| Arquivo | Função |
|---|---|
| `.env.example` | Exemplo de variáveis da engine (Gemini, Replicate, WP, custos) |
| `README.md` | Manual técnico da engine |

## 5.2 `sowads-content-engine/system/`

| Arquivo | Função |
|---|---|
| `system.md` | Prompt sistêmico oficial da produção |
| `user.md` | Template de entrada por artigo/tema |

## 5.3 `sowads-content-engine/agents/`

### Agent 01 - Theme Generator

| Arquivo | Função |
|---|---|
| `agent_01_theme_generator/README.md` | Escopo e limites do agente |
| `agent_01_theme_generator/system_prompt.md` | Contrato de geração de pautas/temas |

### Agent 02 - Article Generator

| Arquivo | Função |
|---|---|
| `agent_02_article_generator/README.md` | Regras de geração do pacote de artigo |
| `agent_02_article_generator/system_prompt.md` | Prompt principal de redação |
| `agent_02_article_generator/user_wrapper_template.md` | Molde de entrada de parâmetros para cada tema |

### Agent 03 - SEO Audit

| Arquivo | Função |
|---|---|
| `agent_03_seo_audit/README.md` | Política geral de auditoria |
| `agent_03_seo_audit/system_prompt.md` | Prompt de auditoria |
| `agent_03_seo_audit/deterministic_checks.md` | Checks objetivos e reason codes |
| `agent_03_seo_audit/scoring_policy.md` | Critérios de score e aprovação |

### Agent 04 - Similarity

| Arquivo | Função |
|---|---|
| `agent_04_similarity/README.md` | Política de similaridade/canibalização |
| `agent_04_similarity/system_prompt.md` | Prompt de análise semântica |
| `agent_04_similarity/compare_methods.md` | Estratégias de comparação |
| `agent_04_similarity/similarity_policy.md` | Thresholds e decisões |

### Agent 05 - Image Prompt

| Arquivo | Função |
|---|---|
| `agent_05_image_prompt/README.md` | Regras de construção de prompt visual |
| `agent_05_image_prompt/system_prompt.md` | Prompt para descrição de imagem por artigo |

### Agent 06 - Publisher

| Arquivo | Função |
|---|---|
| `agent_06_publisher/README.md` | Política de publicação |
| `agent_06_publisher/system_prompt.md` | Prompt de preparação para publicação |
| `agent_06_publisher/publication_policy.md` | Critérios de push no WP |
| `agent_06_publisher/wp_fields.md` | Mapeamento de campos WordPress |

## 5.4 `sowads-content-engine/orchestrator/` - scripts e contratos

### Núcleo de execução

| Arquivo | Função operacional |
|---|---|
| `run_pipeline.py` | Orquestrador principal (`all` e agente isolado) |
| `run_pipeline_from_themes.py` | Pipeline iniciando de CSV de temas pronto |
| `render_images.py` | Render de imagem e geração de manifests |
| `publish_wp_cli.py` | Publicação via SSH + WP-CLI |

### Hardening / reparos / qualidade

| Arquivo | Função operacional |
|---|---|
| `content_sanitizer.py` | Higienização de pacotes e HTML |
| `enforce_batch_constraints.py` | Enforça constraints de lote (palavras, densidade etc.) |
| `enrich_readability_blocks.py` | Enriquecimento visual (tabela/listas) em posição natural |
| `repair_article_packages.py` | Reparo de pacote malformado |
| `repair_h1_similarity.py` | Ajuste quando H1 e meta title ficam parecidos demais |

### Governança do orquestrador

| Arquivo | Função |
|---|---|
| `contracts.md` | Contratos de I/O de cada fase |
| `gates.md` | Gates formais e reason codes |
| `cost_policy.md` | Diretriz de custo e controle de consumo |
| `orchestrator_system_prompt.md` | Prompt interno de coordenação |
| `README.md` | Guia técnico do orquestrador |

### Presets de configuração de lote

| Arquivo | Cenário |
|---|---|
| `config.example.json` | Exemplo base |
| `config.consultoria.json` | Lote de consultoria |
| `config.varejo.15.json` | Lote varejo (15) |
| `config.auto_fin.30.json` | Lote automotivo + financeiro |
| `config.auto_fin.30.batch172457.json` | Variante operacional desse lote |
| `config.bet-igaming-core.30.json` | Lote bet/igaming + core |
| `config.bet-igaming-core.30.override.json` | Override do lote bet/core |
| `config.educacao-saas-agro.45.json` | Lote educação + SaaS + agro |
| `config.educacao-saas-agro.45.override.json` | Override desse lote |
| `config.consultoria.batch10.json` | Execução consultoria (v1) |
| `config.consultoria.batch10.v2.json` | Execução consultoria (v2) |
| `config.consultoria.batch10.v3.json` | Execução consultoria (v3) |
| `config.consultoria.batch10.final.json` | Execução consultoria final |
| `config.consultoria-franquias-ecommerce-saude.60.json` | Lote multi-vertical (60) |
| `config.consultoria-franquias-ecommerce-saude.60.override.json` | Override desse lote |

## 5.5 `sowads-content-engine/data/` - estado runtime

| Pasta | Conteúdo |
|---|---|
| `batches/` | entradas/artefatos intermediários por batch |
| `history/` | memória de execução e histórico útil para dedupe |
| `logs/` | logs de execução, chamadas IA e publicação |
| `cache/` | cache técnico para reduzir recomputação |

## 5.6 `sowads-content-engine/outputs/` - artefatos

| Pasta | Artefato |
|---|---|
| `themes/` | CSV de temas por lote |
| `articles/` | CSVs de artigos em versões |
| `audits/` | resultados de auditoria SEO |
| `similarity/` | resultados de similaridade |
| `image-prompts/` | prompts de imagem por artigo |
| `generated-images/` | imagens e manifests |
| `publish-jobs/` | evidências de publicação |
| `reports/` | relatórios agregados |
| `assincronos/` | execução agente-a-agente, isolada |

---

## 6) Comportamento Esperado da Linha de Produção

Fluxo completo (`agent all`):

1. gerar temas
2. gerar artigos
3. auditar SEO
4. auditar similaridade
5. reescrever apenas reprovados
6. gerar prompt de imagem por artigo
7. renderizar imagens
8. publicar no WordPress

Comportamento obrigatório:
- qualquer reason code crítico bloqueia publicação
- logs reais de chamadas IA sempre gravados
- saída sempre versionada por `BATCH-*`
- operação pode ser síncrona (linha completa) ou assíncrona (agente isolado)

---

## 7) Melhorias já incorporadas (hardening)

Melhorias relevantes já absorvidas no processo:

- remoção de artefatos de cauda (` ``` ` e blocos de separador repetitivo)
- detecção e correção de repetição no final do texto
- controle de similaridade entre H1 e Meta Title
- enriquecimento de legibilidade com elementos visuais reais
- reposicionamento de listas/tabelas para início/meio (não no final)
- padronização de tabela com bordas cinza para leitura melhor
- separação de logs de IA (`gemini_calls.jsonl`) com horários e custo estimado
- suporte operacional para execução assíncrona por agente

---

## 8) Observabilidade e Auditoria

Arquivos de validação operacional:

| Arquivo | O que validar |
|---|---|
| `data/logs/logs.jsonl` | execução por fase (start/success/failure) |
| `data/logs/gemini_calls.jsonl` | request/response real, latência, uso e custo estimado |
| `data/logs/publication_log.jsonl` | sucesso/falha por item publicado |
| `outputs/publish-jobs/PUB-*/published_posts.csv` | IDs e slugs efetivamente publicados |

Checklist mínimo antes de publicar um lote:

1. sem reason code crítico
2. pacote de 2 blocos válido
3. mínimo de palavras respeitado
4. densidade dentro da faixa alvo
5. H1 diferente de Meta Title
6. tabela/listas em posição natural
7. logs de IA e publicação presentes

---

## 9) Execução - Comandos de Referência

Pipeline completo:

```bash
cd Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine
python orchestrator/run_pipeline.py --base . --config orchestrator/config.example.json
```

Agente isolado (assíncrono):

```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json \
  --agent agent03 \
  --articles-file data/batches/BATCH-.../articles_v1.csv \
  --async-output
```

Render de imagens:

```bash
python orchestrator/render_images.py --base . --latest
```

Publicação WordPress:

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

---

## 10) Troubleshooting Operacional

Problema: artigos com final repetido
- ação: rodar `repair_article_packages.py` + `content_sanitizer.py`
- validação: ausência de `repetitive_tail` no audit

Problema: H1 e título quase idênticos
- ação: rodar `repair_h1_similarity.py`
- validação: score de similaridade abaixo do threshold

Problema: artigos pesados sem escaneabilidade
- ação: rodar `enrich_readability_blocks.py`
- validação: presença de tabela/lista até metade do texto

Problema: imagem não aderente ao artigo
- ação: revisar prompt no `agent_05_image_prompt/system_prompt.md`
- validação: rejeitar apenas casos com texto indesejado, distorção extrema ou tema sem aderência

---

## 11) Padrões de Nome

- Workspace oficial: `Sowads-AIO-Workspace`
- Lote: `BATCH-{assunto}-{YYYYMMDD-HHMMSS}`
- Publicação: `PUB-{YYYYMMDD-HHMMSS}`
- Assíncrono: `ASYNC-{YYYYMMDD-HHMMSS}`

Exemplos:
- `BATCH-varejo-20260221-155713`
- `BATCH-automotivo-financeiro-20260221-172457`

---

## 12) Segurança e Governança

- não subir `.env.local` para git
- não hardcodar chaves em script/prompt/readme
- tratar `data/logs/gemini_calls.jsonl` como sensível (pode conter conteúdo parcial de prompts/respostas)
- versionar alterações de prompt e gates com mensagem clara de impacto

---

## 13) O que este README garante

Se este README estiver atualizado, qualquer pessoa do time consegue:

1. entender o papel de cada arquivo crítico
2. operar a linha completa com previsibilidade
3. rodar agentes de forma isolada sem quebrar contratos
4. auditar resultado por logs reais
5. corrigir falhas recorrentes com scripts de repair
6. publicar lote com rastreabilidade fim a fim

