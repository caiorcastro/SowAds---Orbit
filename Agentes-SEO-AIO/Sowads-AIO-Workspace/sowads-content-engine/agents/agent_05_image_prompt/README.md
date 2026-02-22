# Agent 05 — Image Prompt Generator

## Missão
Gerar prompts de imagem de destaque para artigos aprovados, mantendo consistência visual com a marca.

## Escopo
- Produz prompt textual, não gera arquivo de imagem final.
- Mantém vínculo explícito com artigo via `id`.

## Entrada
Mapa de artigos aprovados (`id -> article`).

## Saída
`image_prompts.csv` com colunas:
`id,article_title,slug,dimensions,style,prompt,negative_prompt`

## Regras visuais
- Dimensão padrão: `1200x630`.
- Linguagem visual premium, sem texto embutido.
- `negative_prompt` fixo para evitar watermark/logotipo/texto.

## Critérios de qualidade
- Prompt precisa refletir o tema do artigo, não ser genérico.
- Estilo consistente com universo Sowads (dados, estratégia, performance).

## Execução isolada
```bash
python orchestrator/run_pipeline.py \
  --agent agent05 \
  --articles-file data/batches/BATCH-.../articles_v1.csv \
  --async-output
```
