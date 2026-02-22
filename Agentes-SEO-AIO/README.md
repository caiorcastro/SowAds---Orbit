# Agentes SEO/AIO - Índice do Projeto

Este diretório é o ponto de entrada do projeto de produção de conteúdo em escala da Sowads.

## O que existe aqui

```text
Agentes-SEO-AIO/
└── Sowads-AIO-Workspace/
    ├── README.md
    ├── .env.example
    ├── common.py
    ├── claude/
    │   └── system/
    └── sowads-content-engine/
```

## Para começar rápido

1. Abra `Agentes-SEO-AIO/Sowads-AIO-Workspace/README.md`.
2. Configure ambiente usando `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/.env.example`.
3. Rode pipeline pelo `run_pipeline.py`.
4. Gere imagens com `render_images.py`.
5. Publique com `publish_wp_cli.py`.

## Nome da pasta

A pasta operacional foi renomeada para `Sowads-AIO-Workspace` para remover redundância do nome antigo e separar claramente:

- camada de workspace e governança
- engine operacional de produção

## Navegação recomendada

- Documentação completa do workspace:
  - `Agentes-SEO-AIO/Sowads-AIO-Workspace/README.md`
- Documentação técnica da engine:
  - `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/README.md`
- Orquestrador:
  - `Agentes-SEO-AIO/Sowads-AIO-Workspace/sowads-content-engine/orchestrator/README.md`
