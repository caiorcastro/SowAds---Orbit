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
- exatamente 0 `h1` no HTML package (H1 fica no título nativo do WP).
- FAQ presente (HTML + `FAQPage` JSON-LD).
- FAQ semântico (`FAQPage` + `Question` + `acceptedAnswer`) e com respostas completas.
- `Article` JSON-LD presente e completo.
- `HowTo` só se houver passos reais.
- sem abertura genérica proibida.
- sem ano incoerente (2024/2025).
- faixa de palavras entre 900 e 1500.
- estrutura visual mínima com 2 a 3 recursos por artigo (lista numerada, bullets, mini-checklist, tabela, blockquote, frases-âncora em negrito).
- reprovar excesso visual (4+ recursos no mesmo artigo).
- tabela (quando houver) com células curtas/objetivas e legibilidade visual (linhas/bordas visíveis).
- posição natural dos blocos visuais estruturais (primeiro elemento visual após 2º/3º/4º parágrafo, nunca como apêndice final).
- reprovar blocos fixos/template rígido e padrão estrutural repetido no mesmo lote.
- reprovar excesso de negrito no corpo.
- sem artefatos de cauda (` ``` ` / `====`).
- sem repetição excessiva no final do texto.
- título do post e Meta Title não podem ser praticamente idênticos.
- CTA obrigatório (`<section class=\"sowads-cta\">`).
- blocos H2 com resumo autossuficiente no primeiro parágrafo.
- presença de referência verificável (fonte + ano) em texto simples.
- reprovar parágrafos excessivamente longos (muro de texto).
- percentual com fonte próxima (heurística).

### Gate B (heurístico)
Base de score (0–100):
- keyword no título do post, 1º parágrafo, 2+ H2 e conclusão.
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
- `body_h1_present`
- `meta_description_missing`
- `faq_missing`
- `faq_answers_missing`
- `faq_html_semantic_missing`
- `article_schema_missing`
- `article_schema_incomplete`
- `temporal_incoherence`
- `malformed_tail`
- `repetitive_tail`
- `low_visual_structure`
- `visual_overload`
- `late_visual_structure`
- `long_paragraphs`
- `geo_block_weak`
- `cta_missing`
- `sources_missing`
- `bold_overuse`
- `fixed_blocks_detected`
- `repeated_structure_pattern`

## Política de bloqueio final
Não publicar quando:
- score SEO abaixo de 80;
- similaridade acima de 60;
- qualquer reason code crítico ativo.
