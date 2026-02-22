# Gates de Qualidade

## Política geral
- Gate determinístico é obrigatório.
- Gate heurístico decide score e prioridade.
- Judge LLM só em zona cinzenta, para reduzir custo.

## Agente 03 — SEO/GEO/E-E-A-T
### Gate A (determinístico, bloqueante)
Checklist mínimo:
- 2 blocos obrigatórios (`META INFORMATION` e `HTML PACKAGE`).
- `meta_title <= 60`.
- `meta_description <= 155`.
- slug válido (`[a-z0-9-]`, kebab-case).
- sem link externo (`http`, `https`, `www`).
- exatamente 1 `h1`.
- FAQ presente (HTML + `FAQPage` JSON-LD).
- `Article` JSON-LD presente.
- `HowTo` só se houver passos reais.
- sem abertura genérica proibida.
- sem ano incoerente (2024/2025).
- estrutura visual mínima (listas + tabela).
- posição natural dos blocos visuais (tabela/listas no início do desenvolvimento, não apenas no final).
- sem artefatos de cauda (` ``` ` / `====`).
- sem repetição excessiva no final do texto.
- H1 e Meta Title não podem ser praticamente idênticos.
- percentual com fonte próxima (heurística).

### Gate B (heurístico)
Base de score (0–100):
- keyword no H1, 1º parágrafo, 2+ H2 e conclusão.
- presença de termos de negócio (CTR, CAC, ROAS, SEO etc.).
- sinais de contexto prático e densidade estrutural.

Regras:
- `score < 80` => rewrite.
- `score >= 80` => apto para próxima fase (se sem bloqueios críticos).

### Gate C (judge opcional)
Só para casos ambíguos (ex.: score 75–85 com sinais contraditórios).

## Agente 04 — Similaridade/Canibalização
### Gate A (determinístico)
- Jaccard 3-gram.
- Cosine bag-of-words.
- bonus/penalidade semântica por keyword primária igual.

### Gate B (risco semântico)
Sinaliza conflito quando:
- intenção equivalente (ângulo/funil muito próximos)
- headings muito parecidos
- sobreposição alta no histórico

### Gate C (judge opcional)
Apenas para zona cinzenta (55–65) quando necessário desempate.

## Decisão de similaridade
- `> 60`: `rewrite` obrigatório.
- `40–60`: `risk` (monitorar e ajustar, sem reprovação automática por si só).
- `< 40`: `ok`.

## Reason codes críticos (bloqueiam publicação)
- `missing_blocks`
- `meta_title_too_long`
- `meta_description_too_long`
- `external_link`
- `invalid_slug`
- `missing_h1`
- `faq_missing`
- `article_schema_missing`
- `temporal_incoherence`
- `malformed_tail`
- `repetitive_tail`
- `low_visual_structure`
- `late_visual_structure`

## Política de bloqueio final
Não publicar quando:
- score SEO abaixo de 80;
- similaridade acima de 60;
- qualquer reason code crítico ativo.
