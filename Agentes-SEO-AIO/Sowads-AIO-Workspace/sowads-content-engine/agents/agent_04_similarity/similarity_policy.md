# Similarity Policy — Agent 04

## Objetivo
Reduzir duplicidade e canibalização entre conteúdos do lote e histórico.

## Thresholds
- `< 40`: `ok`
- `40–60`: `risk`
- `> 60`: `rewrite` obrigatório

## Sinais considerados
- sobreposição lexical alta
- headings muito próximos
- keyword primária igual
- intenção/funil equivalentes
- conflitos com histórico recente

## Regras de ação
- Sempre listar conflitos top-N com score e justificativa.
- Para `rewrite`, guidance deve indicar como diferenciar:
  - ângulo
  - estrutura
  - exemplos
  - profundidade técnica

## Saída mínima por item
- `similarity_score`
- `status`
- `conflicts[]`
- `flag_similarity`
- `rewrite_guidance`
