# SOWADS Repository

Repositorio principal com dois projetos "primos":
- migracao e operacao de site WordPress clone
- fabrica de conteudo SEO/AIO multiagente

Este README da visao geral da raiz e aponta exatamente onde voce encontra cada parte.

## Mapa rapido da raiz

| Pasta | O que e | Quando usar |
|---|---|---|
| `Agentes-SEO-AIO/` | Projeto de agentes de conteudo, auditoria, imagem e publicacao | Quando for gerar, revisar e publicar artigos em lote |
| `Migracao-do-Site/` | Projeto de migracao do site original para WordPress + guias operacionais | Quando for mexer em clone, tema, layout, deploy e operacao do site |

## Estrutura visual

```text
SOWADS/
├── Agentes-SEO-AIO/
│   └── Sowads-AIO-Workspace/
│       ├── README.md
│       └── sowads-content-engine/
│           ├── README.md
│           ├── agents/
│           ├── orchestrator/
│           ├── system/
│           ├── data/
│           └── outputs/
└── Migracao-do-Site/
    ├── README.md
    ├── scripts/
    ├── deploy_ssh*.py
    ├── MIGRACAO_*_MASTER.md
    └── GUIA_GUTENBERG_SOWADS.md
```

## Onde comecar em cada projeto

### 1) Fabrica de conteudo (SEO/AIO)
Entrada principal:
- `Agentes-SEO-AIO/README.md`
- `Agentes-SEO-AIO/Sowads-AIO-Workspace/README.md`
- `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/README.md`

Arquivos-chave:
- `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/system/system.md`
- `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/system/user.md`
- `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/orchestrator/run_pipeline.py`

Uso tipico:
1. configurar `.env.local`
2. rodar pipeline
3. gerar imagens
4. publicar no WordPress

### 2) Migracao do site
Entrada principal:
- `Migracao-do-Site/README.md`

Documentacao-chave:
- `Migracao-do-Site/MIGRACAO_SOWADS_RESULTSQUAD_MASTER.md`
- `Migracao-do-Site/MIGRACAO_SQUARESPACE_PARA_WORDPRESS_MASTER.md`
- `Migracao-do-Site/GUIA_GUTENBERG_SOWADS.md`

Scripts uteis:
- `Migracao-do-Site/deploy_ssh.py`
- `Migracao-do-Site/deploy_ssh_mv.py`
- `Migracao-do-Site/scripts/wp_sync_clone_content.php`

## Convencoes deste repositorio

- `BATCH-{assunto}-{YYYYMMDD-HHMMSS}` para lotes de conteudo.
- Logs operacionais e resultados ficam no projeto de engine (`data/logs`, `outputs/*`).
- Credenciais nunca hardcoded: usar `.env`/`.env.local`.
- Arquivos gerados de runtime (logs, outputs, cache) estao ignorados via `.gitignore`.

## Estado atual

- Engine multiagente ativa e publicada no remoto.
- Gates de qualidade atualizados para:
  - estrutura visual adaptativa (2 a 3 recursos por artigo, conforme tema)
  - posicionamento natural dos blocos visuais
  - anti-template (bloqueio de blocos fixos repetidos)
  - controle de excesso de negrito
  - deteccao de artefatos e repeticao de cauda
  - controle de similaridade titulo do post x Meta Title
- Projeto de migracao mantido em pasta separada para operacao e manutencao.

## Checklist rapido antes de operar

1. Confirmar variaveis de ambiente.
2. Ler README do modulo alvo (`Agentes-SEO-AIO/...` ou `Migracao-do-Site/...`).
3. Executar em lote de teste pequeno antes do lote cheio.
4. Validar saida visual e logs.
5. Publicar somente apos gates aprovados.

---

Se voce abrir apenas 1 arquivo para começar, abra:
- `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/README.md` (conteudo)
- `Migracao-do-Site/README.md` (site)
