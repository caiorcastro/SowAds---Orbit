# Scoring Policy — Agent 03

## Escala
- Score final: 0 a 100
- Aprovação: >= 80

## Penalidades base
- Falhas críticas (estrutura, schema essencial, link externo): penalidade alta.
- Falhas de otimização (keyword coverage, densidade de sinais): penalidade moderada.
- Falhas de acabamento (conclusão fraca, ausência de termos de negócio): penalidade leve.

## Dimensões avaliadas
1) Conformidade de formato
2) Cobertura de keyword primária (H1, primeiro parágrafo, H2, conclusão)
3) Clareza estrutural (headings, parágrafos, legibilidade)
4) Sinais GEO/E-E-A-T (contexto prático, termos técnicos explicados)
5) Confiabilidade editorial (consistência temporal e factual)

## Decisão
- `score >= 80` e sem reason code crítico: aprovado na fase.
- `score < 80`: `flag_rewrite=true`.
- reason code crítico: bloqueio independentemente do score.

## Guidance obrigatório
Quando houver rewrite:
- orientar por problema objetivo;
- não usar instruções vagas;
- priorizar correções de maior impacto primeiro.
