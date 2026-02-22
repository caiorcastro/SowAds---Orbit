# Agente de SEO / AIO (Sowads)

Este diretório agora é um workspace de operação do **Sowads Content Engine**.

## Projeto ativo
- Engine principal: `sowads-content-engine/`
- Documentação operacional completa: `sowads-content-engine/README.md`

## Escopo atual
- geração de temas
- geração de artigos em escala
- auditoria SEO/GEO/E-E-A-T
- validação de similaridade/canibalização
- prompts de imagem + render
- publicação WordPress com logs completos

## Entrada rápida

```bash
cd sowads-content-engine
python orchestrator/run_pipeline.py --base . --config orchestrator/config.example.json
```

## Observação

Scripts legados de geração simples foram substituídos pela arquitetura multiagente.
Para operação em produção, use somente o fluxo documentado no README do engine.
