# MANUAL DE ORQUESTRAÇÃO — SOWADS CONTENT ENGINE v8.0

> **Propósito deste manual**: servir como um README ultra detalhado para **criar o projeto inteiro**, com **pastas**, **agentes**, **contratos**, **logs**, **histórico**, **gates de qualidade**, **rewrite seletivo** e **publicação no WordPress**, obedecendo SEMPRE o **SOWADS CONTENT ENGINE v8.0**.

---

## Escopo e premissas

* **Este manual NÃO substitui** seus arquivos:

  * `system/system.md` (SOWADS CONTENT ENGINE v8.0)
  * `system/user.md` (USER MESSAGE — v8.0)
    Eles são **a autoridade máxima** da geração do artigo.

* **Modelo de IA padrão**: **Gemini 2.5 Flash**.

  * Regra: **todos os agentes usam Gemini 2.5 Flash**, exceto quando explicitamente definido diferente.
  * Observação importante de custo: use Flash como padrão; qualquer “Judge”/avaliação com LLM só entra quando os **gates determinísticos** não forem suficientes.

* **Objetivo final**: produzir lotes de artigos com qualidade editorial e técnica, sem canibalização, e publicar automaticamente no WordPress com rastreabilidade.

---

## Complexidade e confiabilidade

* **Complexidade**: Alta (pipeline multiagente, auditoria, similaridade com histórico, rewrite seletivo, publicação automatizada).
* **Confiabilidade deste manual**: Alta para governança/contratos e fluxo (0,86). 
---

## Visão geral do fluxo (pipeline)

1. **Agente 01 — Theme Generator**: gera temas + parâmetros completos seguindo o `user.md` e `system.md`.
2. **Agente 02 — Article Generator**: gera artigos WordPress-ready, seguindo `system.md` e `user.md`, com output em 2 blocos.
3. **Agente 03 — SEO/GEO/E-E-A-T Auditor**: pontua e decide rewrite com base em gates determinísticos + (opcional) judge.
4. **Agente 04 — Similarity & Cannibalization Validator**: valida duplicação e canibalização vs lote + histórico; refaz se >60%.
5. **Agente 05 — Image Prompt Generator**: gera prompts de imagens destacadas (SowAds look & feel).
6. **Agente 06 — Publisher**: publica no WordPress (API/SSH/WP-ALL-IMPORT) e gera logs.

**Loop de qualidade**: se algum artigo reprovar em (3) ou (4), ele volta para (2) em modo `REWRITE_ONLY` (somente os IDs flagados), até 100% aprovado.

---

## Arquivos “fonte da verdade” (obrigatórios)

### `system/system.md`

* Contém o guia editorial completo: regras absolutas, estilo e voz, SEO/GEO, E-E-A-T, schemas, 2 blocos obrigatórios, proibição de links externos, referência de ano 2026, etc.

### `system/user.md`

* Contém o template de parâmetros + instruções de execução.
* O Orquestrador deve apenas **substituir placeholders** `{{…}}`.

**Regra de ouro**: esses dois arquivos **não devem ser reescritos** por nenhum agente.

---

## Estrutura de pastas (OBRIGATÓRIA)

Crie exatamente a estrutura abaixo:

```
sowads-content-engine/
│
├── system/
│   ├── system.md
│   └── user.md
│
├── orchestrator/
│   ├── README.md
│   ├── orchestrator_system_prompt.md
│   ├── contracts.md
│   ├── cost_policy.md
│   ├── gates.md
│   └── config.example.json
│
├── agents/
│   ├── agent_01_theme_generator/
│   │   ├── README.md
│   │   └── system_prompt.md
│   │
│   ├── agent_02_article_generator/
│   │   ├── README.md
│   │   ├── system_prompt.md
│   │   └── user_wrapper_template.md
│   │
│   ├── agent_03_seo_audit/
│   │   ├── README.md
│   │   ├── system_prompt.md
│   │   ├── deterministic_checks.md
│   │   └── scoring_policy.md
│   │
│   ├── agent_04_similarity/
│   │   ├── README.md
│   │   ├── system_prompt.md
│   │   ├── similarity_policy.md
│   │   └── compare_methods.md
│   │
│   ├── agent_05_image_prompt/
│   │   ├── README.md
│   │   └── system_prompt.md
│   │
│   └── agent_06_publisher/
│       ├── README.md
│       ├── system_prompt.md
│       ├── wp_fields.md
│       └── publication_policy.md
│
├── data/
│   ├── batches/
│   │   └── (cada batch em uma pasta)
│   ├── history/
│   │   ├── history.jsonl
│   │   └── index.json
│   ├── logs/
│   │   ├── logs.jsonl
│   │   └── publication_log.jsonl
│   └── cache/
│       └── (cache de checks e scores por id+version)
│
├── outputs/
│   ├── themes/
│   ├── articles/
│   ├── audits/
│   ├── similarity/
│   ├── images/
│   └── published/
│
└── README.md  (este manual)
```

---

## Variáveis de ambiente (segurança)

Crie um `.env` (não versionar) contendo:

* `GEMINI_API_KEY=...` 
* `WP_BASE_URL=...`
* `WP_USERNAME=...` 
* `WP_APP_PASSWORD=...` 
* `WP_DEFAULT_STATUS=draft|publish`
* `WP_DEFAULT_CATEGORY=...`
* `WP_DEFAULT_TAGS=...`
* variáveis de API, SSH ou Informações WP-ALL-IMPORT necessárias 

**Proibido**: hardcode de credenciais em prompts, logs ou código.

---

## Contratos de dados (I/O) — padrão do projeto

### Identificadores

* `batch_id`: `BATCH-YYYYMMDD-HHMMSS`
* `id`: `SOWADS-YYYYMMDD-HHMMSS-RANDOM6`
* `version`: inteiro (1,2,3…)

### Convenção de arquivos por batch

Em `data/batches/{batch_id}/` criar:

* `themes.csv`
* `articles_v{version}.csv` (pode ser um arquivo por versão global, ou por item; mas padronize)
* `seo_audit.json`
* `similarity_report.json`
* `image_prompts.csv`
* `publish_results.json`

---

## Política de custo (para não gastar um barril)

### Padrão

* **Gemini 2.5 Flash** para tudo.
* Rodar checks determinísticos antes de qualquer judge.

### Regra prática

* **Geração (Agente 02)**: 1 chamada por artigo.
* **Auditoria (Agente 03)**:

  * Gate determinístico primeiro.
  * Judge com LLM apenas se o determinístico ficar inconclusivo.
* **Similaridade (Agente 04)**:

  * Gate determinístico (shingle/jaccard/tfidf) primeiro.
  * Judge com LLM apenas na “zona cinzenta”.
* **Rewrites**: somente itens flagados.
* **Imagem**: só depois de aprovado.

---

# 2. O ORQUESTRADOR (centro do sistema)

## Função

* Executar pipeline na ordem correta.
* Validar contratos de saída.
* Controlar rewrite seletivo.
* Atualizar histórico.
* Bloquear publicação se qualquer regra crítica falhar.

## Entrada do usuário (sempre)

O orquestrador deve receber:

* Nicho / assunto macro
* `{{VERTICAL_ALVO}}`
* `{{PORTE_EMPRESA_ALVO}}`
* `{{MODELO_NEGOCIO_ALVO}}`
* `{{PRODUTO_SOWADS_FOCO}}`
* Quantidade de temas (ideal múltiplo de 20)
* `publish_mode` (draft|publish)
* Restrições (ex.: foco BR; evitar preço; etc.)
* URL interna opcional (`{{URL_INTERNA}}`)

## Saída final esperada

* Um batch aprovado, com:

  * Artigos `APPROVED`
  * Relatórios de auditoria e similaridade
  * Prompts de imagem
  * Resultado de publicação
  * Logs e histórico atualizados

---

# 3. AGENTE 01 — THEME GENERATOR

## Para que serve

Gerar **temas e parâmetros completos** para alimentar o `system/user.md`, garantindo consistência com:

* Vertical
* Porte
* Modelo de negócio
* Produto Sowads em foco
* Ângulo do conteúdo

Esse agente **não escreve artigo**. Ele produz o “briefing estruturado” para o Agente 02.

## Modelo

* **Gemini 2.5 Flash**

## Entradas

* nicho
* vertical alvo (tabela do user.md)
* porte alvo (tabela do user.md)
* modelo de negócio (tabela do user.md)
* produto Sowads em foco (tabela do user.md)
* quantidade de temas
* restrições
* url interna opcional

## Regras

1. **Sem números de busca**: apenas Alta/Média/Baixa.
2. Definir funil: TOFU/MOFU/BOFU.
3. Gerar keyword primária e secundárias (secundárias separadas por `|`).
4. Garantir que o tema não force dados sem fonte. Se depender de dado interno do cliente, marcar em `notes`.
5. Gerar `angulo_conteudo` com base na lista do user.md.

## Saída (CSV obrigatório)

Salvar em `outputs/themes/{batch_id}_themes.csv` e `data/batches/{batch_id}/themes.csv`.

**Colunas (ordem fixa):**

`id,timestamp,tema_principal,keyword_primaria,keywords_secundarias,porte_empresa_alvo,modelo_negocio_alvo,vertical_alvo,produto_sowads_foco,angulo_conteudo,url_interna,funil,busca,titulo_anuncio,notes`

### Exemplo de linha (ilustrativo)

* keywords_secundarias: `pixel do meta|conversão|capi|atribuição|utm|crm`
* url_interna: vazio ou `{{URL_INTERNA}}`

---

# 4. AGENTE 02 — ARTICLE GENERATOR (CORE)

## Para que serve

Gerar o artigo final em **HTML WordPress-ready**, obedecendo 100%:

* `system/system.md` (guia v8.0)
* `system/user.md` (template de parâmetros)

Ele deve retornar o artigo com **os 2 blocos obrigatórios** e schemas conforme v8.0.

## Modelo

* **Gemini 2.5 Flash**

## Como ele deve ser chamado (extremamente importante)

### System Prompt do Agente 02

* Deve ser exatamente o conteúdo do arquivo: `system/system.md`

### User Prompt do Agente 02

* Deve ser exatamente o conteúdo do arquivo: `system/user.md`
* Com placeholders substituídos pelo Orquestrador.

### Wrapper (economia + rastreabilidade)

Antes do conteúdo do `user.md`, o Orquestrador adiciona somente:

* `ID do Artigo: {id}`
* `Batch ID: {batch_id}`
* `Version: {version}`

Sem duplicar o guia v8.0.

## Entradas

* Uma linha do `themes.csv` por geração
* `batch_id`, `id`, `version`

## Regras críticas (repetidas para evitar erro)

1. Output final do artigo deve conter **EXATAMENTE 2 blocos**, sem texto antes/depois.
2. Sem hyperlinks externos (`<a href>` externo é proibido).
3. Ano de referência: 2026.
4. Dados/estatísticas: somente com fonte nomeada e ano (sem links).
5. Variação ativa de abertura e ordem de seções (conforme user.md + system.md).

## Saída (CSV obrigatório)

Salvar em `outputs/articles/{batch_id}_articles.csv` e `data/batches/{batch_id}/articles_v{N}.csv`.

**Colunas (ordem fixa):**

`batch_id,id,version,tema_principal,keyword_primaria,keywords_secundarias,porte_empresa_alvo,modelo_negocio_alvo,vertical_alvo,produto_sowads_foco,angulo_conteudo,url_interna,slug,meta_title,meta_description,content_package,status`

* `content_package` = os **2 blocos** do v8.0.
* `status` começa como `PENDING_QA`.

## Como funciona o REWRITE_ONLY

Quando o orquestrador pedir rewrite:

* Entrada inclui `rewrite_guidance` do Agente 03 e/ou 04.
* O Agente 02 deve:

  * manter o **mesmo id**
  * incrementar `version`
  * reescrever respeitando guidance
  * não “refazer tudo igual” (mudar ângulo, estrutura, exemplos, H2s)

---

# 5. AGENTE 03 — SEO/GEO/E-E-A-T AUDITOR

## Para que serve

Garantir que o artigo:

* respeita o formato (2 blocos)
* cumpre regras SEO + GEO + E-E-A-T
* não viola v8.0 (links externos, ano errado, abertura genérica, dados sem fonte)

## Modelo

* **Gemini 2.5 Flash** (apenas se precisar)

## Estratégia: Gates (barato → caro)

### Gate A — determinístico (sem LLM)

Este gate deve rodar sempre. Se falhar, reprova.

Checklist mínimo:

1. Existem as strings:

   * `=== META INFORMATION ===`
   * `=== HTML PACKAGE — WORDPRESS READY ===`
2. Meta Title ≤ 60 caracteres
3. Meta Description ≤ 155 caracteres
4. Slug em kebab-case sem acento
5. Proibido `<a href="http` ou `<a href="https` ou `<a href="www`.
6. H1 único.
7. FAQ presente (5–8 perguntas) + FAQ JSON-LD presente.
8. Article JSON-LD presente.
9. HowTo JSON-LD só se existir seção numerada de passos.
10. Detectar aberturas genéricas proibidas (começo do artigo e começo do texto).
11. Detectar menções temporais incoerentes ("atualmente em 2025" etc.).
12. Detectar números “soltos” sem fonte (heurística: percentuais ou estatísticas sem “(Fonte, ano)” próximo).

### Gate B — scoring heurístico (sem LLM)

Se Gate A passar, aplicar um score heurístico (0–100) baseado em:

* keyword no H1 + 1º parágrafo + 2+ H2 + conclusão
* presença de explicação de jargões (heurística por padrões “(… )” e frases explicativas)
* densidade de headings e parágrafos curtos
* presença de bloco de framework (quando ângulo pede)
* presença de cenário prático (E-E-A-T)

Se score heurístico < 80 → rewrite.

### Gate C — Judge com LLM (opcional)

Só chamar Gemini 2.5 Flash como judge quando:

* score heurístico ficar na zona 75–85 e houver dúvida qualitativa
* ou quando a heurística detectar potencial “texto com cara de IA” sem conseguir provar

O judge deve devolver:

* score final
* razões objetivas
* guidance de rewrite específico

## Saída (JSON obrigatório)

Salvar em `outputs/audits/{batch_id}_seo_audit.json` e `data/batches/{batch_id}/seo_audit.json`.

Formato:

```json
{
  "batch_id": "...",
  "threshold": 80,
  "items": [
    {
      "id": "...",
      "version": 1,
      "seo_geo_score": 86,
      "flags": {
        "flag_rewrite": false,
        "reason_codes": []
      },
      "issues": [],
      "rewrite_guidance": ""
    }
  ]
}
```

---

# 6. AGENTE 04 — SIMILARITY & CANIBALIZATION VALIDATOR

## Para que serve

Evitar:

* duplicação de conteúdo
* canibalização de SEO (mesma intenção/keyword competindo)

Conforme seu v8.0:

* **>60% de similaridade → refazer automaticamente**.

## Modelo

* **Gemini 2.5 Flash** (somente se necessário para desempate)

## Entrada

* Artigos do lote (CSV)
* Histórico (history.jsonl)

## Método recomendado (barato → caro)

### Gate A — textual cheap

1. Normalizar texto (remover HTML, lowercase, remover stopwords simples)
2. Shingles 3-gram e Jaccard
3. TF-IDF cosine

Gerar um score consolidado (0–100).

### Gate B — canibalização semântica (barato)

Mesmo se texto diferente, marcar risco quando:

* mesma keyword primária
* mesma intenção (inferida por ângulo/funil + padrões)
* headings muito parecidos

### Gate C — desempate com LLM (opcional)

Usar Gemini 2.5 Flash apenas quando o score estiver **55–65** e você precisar decidir se é “mesma página” ou “páginas diferentes”.

## Regras de decisão

* `similarity_score > 60` → `flag_similarity=true` + rewrite obrigatório
* `40–60` → risco (pode sugerir ajustes, mas não reprovar automaticamente, a menos que seja canibalização clara)
* `<40` → ok

## Saída (JSON obrigatório)

Salvar em `outputs/similarity/{batch_id}_similarity.json` e `data/batches/{batch_id}/similarity_report.json`.

Formato:

```json
{
  "batch_id": "...",
  "policy": {"risk_threshold": 40, "rewrite_threshold": 60},
  "items": [
    {
      "id": "...",
      "version": 1,
      "similarity_score": 28,
      "status": "ok",
      "conflicts": [
        {"other_id": "...", "score": 22, "reason": "mesma intenção, mas estrutura diferente"}
      ],
      "flag_similarity": false,
      "rewrite_guidance": ""
    }
  ]
}
```

---

# 7. AGENTE 05 — IMAGE PROMPT GENERATOR

## Para que serve

Gerar **prompts de imagens destacadas** para cada artigo aprovado.

Ele não deve rodar antes da aprovação, para economizar custo.

## Modelo

* **Gemini 2.5 Flash** para gerar o prompt
* (Opcional) “Nano Banana” para gerar as imagens se estiver integrado ao gerador.

## Regras visuais SowAds

* 1200x630
* Profissional, moderno, premium
* Contexto: marketing ops, dados, performance, estratégia
* Paleta sugerida: #0F172A (base) + #22C55E (acento)
* Sem texto, sem logo, sem watermark
* Sem marcas registradas explícitas
* Nada “genérico banco de imagem”; sempre ancorar no tema do artigo

## Saída (CSV obrigatório)

Salvar em `outputs/images/{batch_id}_image_prompts.csv` e `data/batches/{batch_id}/image_prompts.csv`.

Colunas:

`id,dimensions,style,prompt,negative_prompt`

Negative prompt fixo:
`text, logo, watermark, brand names, readable UI text, trademarks`

---

# 8. AGENTE 06 — PUBLISHER (WORDPRESS)

## Para que serve

Publicar automaticamente os artigos aprovados no WordPress e registrar logs.

## Modelo

* **Gemini 2.5 Flash** apenas para formatação/normalização se necessário; publicação é integração técnica.

## Pré-condições para publicar

Somente publicar se:

* `seo_geo_score >= 80`
* `similarity_score <= 60`
* nenhum reason_code crítico ativo

## Métodos de publicação (escolher 1)

1. **WP REST API** (recomendado)
2. **SSH** (WP-CLI)
3. **WP-ALL-IMPORT** (via CSV pronto)

## Campos recomendados

* title
* slug
* content_html (apenas o HTML interno do pacote)
* excerpt (opcional)
* featured image (se tiver URL/asset)
* categories/tags (padrão por vertical)
* custom field/meta:

  * `sowads_content_id` = ID
  * `sowads_content_version` = version

## Saída (JSON obrigatório)

Salvar em `outputs/published/{batch_id}_publish_results.json` e `data/batches/{batch_id}/publish_results.json`.

Formato:

```json
{
  "batch_id": "...",
  "published": [
    {"id": "...", "version": 1, "wp_post_id": 123, "status": "published", "timestamp": "..."}
  ],
  "failed": [
    {"id": "...", "version": 1, "error": "...", "timestamp": "..."}
  ]
}
```

---

# 9. HISTÓRICO (HISTORY)

## Para que serve

Permitir comparação de similaridade e evitar repetição em lotes futuros.

## Onde fica

* `data/history/history.jsonl`

## O que salvar (mínimo)

Por artigo aprovado/publicado:

* id
* version
* title
* slug
* keyword_primaria
* keywords_secundarias
* funil
* angulo_conteudo
* vertical
* porte
* content_hash (hash do conteúdo normalizado)
* excerpt (primeiros 400–800 chars sem HTML)
* seo_geo_score
* similarity_score
* timestamp

---

# 10. LOGS (JSONL)

## Objetivo

Permitir auditoria, debugging e rastreabilidade.

## Onde fica

* `data/logs/logs.jsonl`
* `data/logs/publication_log.jsonl`

## Formato

Cada linha um JSON:

* timestamp
* phase (themes|articles|audit|similarity|images|publish)
* batch_id
* id
* version
* status (success|fail|requeued)
* reason
* metrics (obj)
* model

---

# 11. POLÍTICAS DE BLOQUEIO (não publicar)

Bloquear publicação automaticamente quando:

* Falta um dos 2 blocos obrigatórios
* Meta Title/Description fora do limite
* Há hyperlink externo
* Há dado numérico sem fonte
* Similaridade > 60
* Score < 80

---

# 12. CHECKLIST DE ENTREGA DO SISTEMA (para a IA que vai criar)

A IA deve:

1. Criar pastas exatamente como definido.
2. Copiar `system.md` e `user.md` para `system/`.
3. Criar README e system_prompt.md de cada agente, com:

   * objetivo
   * entradas
   * saídas
   * regras
   * exemplos
4. Criar `orchestrator/orchestrator_system_prompt.md` com as regras de pipeline e loops.
5. Criar `orchestrator/contracts.md` contendo os contratos CSV/JSON e nomes de arquivos.
6. Criar `orchestrator/gates.md` detalhando Gate A/B/C dos agentes 3 e 4.
7. Criar `orchestrator/cost_policy.md` com regras de custo.
8. Garantir que o sistema use **Gemini 2.5 Flash** por padrão.

---

# 13. Instrução final (para não errar)

* Se houver conflito entre este manual e `system.md`, **`system.md` vence**.
* Nunca “resumir” o `system.md` dentro do agente 02: ele deve usar o arquivo integral.
* Sempre preferir gates determinísticos antes de LLM judge.
* Rewrite seletivo sempre.

Fim.
