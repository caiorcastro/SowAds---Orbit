# Sowads AIO Workspace

Camada de operacao da fabrica de conteudo da Sowads.
Este workspace centraliza prompts, orquestracao, contratos, validacoes, render de imagens e publicacao em WordPress.

## TL;DR

- Entrada editorial: `sowads-content-engine/system/system.md` e `sowads-content-engine/system/user.md`
- Pipeline principal: `sowads-content-engine/orchestrator/run_pipeline.py`
- Publicacao: `sowads-content-engine/orchestrator/publish_wp_cli.py`
- Logs reais de IA: `sowads-content-engine/data/logs/gemini_calls.jsonl`
- Saida operacional: `sowads-content-engine/outputs/*`

## O que voce encontra aqui

```text
Sowads-AIO-Workspace/
├── .env.example
├── common.py
├── claude/
│   └── system/
│       ├── manual-de-orquestracao.md
│       ├── system.md
│       └── user.md
└── sowads-content-engine/
    ├── README.md
    ├── system/
    ├── agents/
    ├── orchestrator/
    ├── data/
    └── outputs/
```

## Responsabilidade de cada bloco

| Bloco | Responsabilidade | Tipo |
|---|---|---|
| `claude/system/*` | Base de prompt e manual original | Governanca de instrucao |
| `sowads-content-engine/system/*` | Prompt efetivo da producao | Fonte de verdade editorial |
| `sowads-content-engine/agents/*` | Contratos e politicas por agente | Especificacao |
| `sowads-content-engine/orchestrator/*` | Execucao real da linha de montagem | Codigo |
| `sowads-content-engine/data/*` | logs, cache, historico e lotes | Estado runtime |
| `sowads-content-engine/outputs/*` | artefatos finais de cada fase | Resultado runtime |

## Inventario detalhado de arquivos (workspace)

### Raiz do workspace

| Arquivo | Serve para | Quando mexer |
|---|---|---|
| `.env.example` | Modelo de variaveis de ambiente | Ao adicionar nova integracao/API |
| `common.py` | Utilitarios compartilhados legados | Quando reutilizar funcoes fora do orchestrator |
| `README.md` | Este guia de operacao | Sempre que arquitetura mudar |

### `claude/system/`

| Arquivo | Serve para | Observacao |
|---|---|---|
| `manual-de-orquestracao.md` | Documento mestre de requisitos | Base historica do desenho da fabrica |
| `system.md` | Prompt editorial original | Nao e o prompt efetivo de execucao do pipeline |
| `user.md` | Template de pedido original | Usado como referencia de parametrizacao |

## Comportamento operacional (fim a fim)

1. **Theme generation**: cria temas com parametros validos para lote.
2. **Article generation**: produz `content_package` no formato de 2 blocos.
3. **SEO audit**: valida regras deterministicas + score.
4. **Similarity audit**: mede canibalizacao intra-lote e historico.
5. **Rewrite loop**: reprocessa apenas IDs reprovados.
6. **Image prompt**: gera prompt de imagem por artigo.
7. **Image render**: renderiza e salva manifests.
8. **Publish**: cria/atualiza post no WP e grava logs de publicacao.

## Melhorias ja incorporadas no processo

- Controle de qualidade de cauda de artigo:
  - deteccao de artefatos de geracao (` ``` ` e `====`)
  - deteccao de repeticao de frases no final
- Controle de estrutura visual:
  - exige tabela + listas
  - bloqueia estrutura visual tardia no texto
- Controle de headline:
  - valida H1 e Meta Title para nao ficarem praticamente iguais
- Enriquecimento de legibilidade:
  - script de insercao/reposicionamento de bloco visual em ponto natural
  - tabela com bordas cinza e espacos consistentes

## Regras de comportamento que a operacao espera

- Nao publicar com reason code critico.
- Nao aceitar artigo sem pacote de 2 blocos.
- Nao aceitar link externo fora da politica.
- Nao aceitar densidade fora da faixa configurada.
- Nao aceitar H1 duplicando semanticamente o Meta Title.
- Nao aceitar bloco visual como apendice no fim.

## Modo de execucao

### Pipeline completo

```bash
cd sowads-content-engine
python orchestrator/run_pipeline.py --base . --config orchestrator/config.example.json
```

### Agente isolado (modo assincrono)

```bash
python orchestrator/run_pipeline.py \
  --base . \
  --config orchestrator/config.example.json \
  --agent agent03 \
  --articles-file data/batches/BATCH-.../articles_v1.csv \
  --async-output
```

### Render de imagens

```bash
python orchestrator/render_images.py --base . --latest
```

### Publicacao WP

```bash
python orchestrator/publish_wp_cli.py \
  --base . \
  --articles-csv outputs/articles/BATCH-..._articles_final.csv \
  --include-statuses APPROVED,PENDING_QA,REJECTED \
  --status publish \
  --ssh-host <host> \
  --ssh-port <port> \
  --ssh-user <user> \
  --ssh-password '<password>' \
  --wp-path <wp_path>
```

## Mapa de arquivos relevantes do engine

### `sowads-content-engine/system/`

| Arquivo | O que define |
|---|---|
| `system.md` | voz, estrutura, SEO/GEO, schemas, formato obrigatorio |
| `user.md` | placeholders de entrada e parametros por artigo |

### `sowads-content-engine/agents/`

| Pasta | O que define |
|---|---|
| `agent_01_theme_generator/` | contrato de temas e estrategia de pauta |
| `agent_02_article_generator/` | contrato de geracao de artigo |
| `agent_03_seo_audit/` | checks deterministas e score |
| `agent_04_similarity/` | regras de canibalizacao e comparacao |
| `agent_05_image_prompt/` | politica de prompt visual |
| `agent_06_publisher/` | politica de campos e publicacao WP |

### `sowads-content-engine/orchestrator/`

| Arquivo | Funcao |
|---|---|
| `run_pipeline.py` | orquestrador principal (all + agente isolado) |
| `run_pipeline_from_themes.py` | execucao partindo de themes prontos |
| `publish_wp_cli.py` | publish remoto via SSH/WP-CLI |
| `render_images.py` | render de imagens e manifests |
| `enrich_readability_blocks.py` | injeta tabela/listas com estilo e posicao natural |
| `enforce_batch_constraints.py` | ajusta tamanho/densidade por lote |
| `repair_article_packages.py` | repara pacote malformed |
| `repair_h1_similarity.py` | corrige H1 quando parecido demais com titulo |
| `content_sanitizer.py` | normaliza e higieniza package/html |
| `gates.md` | politica formal de gates |
| `contracts.md` | contratos de I/O e colunas |
| `cost_policy.md` | diretriz de custo por fase |
| `orchestrator_system_prompt.md` | prompt de coordenacao do orquestrador |
| `config*.json` | presets de lotes por vertical e volume |

## Observabilidade (onde validar se esta tudo certo)

- `data/logs/logs.jsonl`: eventos de fase
- `data/logs/gemini_calls.jsonl`: request/response real, latencia, tokens, custo estimado
- `data/logs/publication_log.jsonl`: status por item publicado
- `outputs/publish-jobs/PUB-.../published_posts.csv`: created/updated por slug

## Fluxo de manutencao e hardening

Quando surgir novo problema em lote:
1. reproduzir no menor lote possivel
2. criar check deterministico no audit
3. atualizar prompt/contrato se necessario
4. criar script de repair se houver passivo historico
5. documentar no README e em `gates.md`
6. reprocessar e publicar com evidencias

## Sinais de qualidade minima antes de novo push de lote

- score SEO aprovado
- similaridade abaixo do limite
- sem reason code critico
- bloco visual presente e em posicao inicial
- sem artefato de output e sem repeticao de cauda
- logs de IA e publicacao gravados

## Decisoes de naming

- Nome da pasta: `Sowads-AIO-Workspace`
- Motivo: remover redundancia do nome anterior e separar claramente workspace de operacao da engine interna.

## Nota de seguranca

- `.env` nao deve ir para git.
- Nao armazenar token em README, prompt ou codigo.
- `data/logs/gemini_calls.jsonl` pode conter prompts/respostas: tratar como dado sensivel.

