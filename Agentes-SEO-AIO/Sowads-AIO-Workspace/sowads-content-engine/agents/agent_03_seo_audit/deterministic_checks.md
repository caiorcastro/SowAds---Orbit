# Deterministic Checks — Agent 03

## Objetivo
Aplicar validações objetivas e reproduzíveis antes de qualquer interpretação subjetiva.

## Checklist obrigatório
1. Blocos mandatórios:
- `=== META INFORMATION ===`
- `=== HTML PACKAGE — WORDPRESS READY ===`

2. Limites técnicos:
- Meta Title <= 60 caracteres
- Meta Description <= 155 caracteres

3. URL/slug:
- kebab-case
- apenas `[a-z0-9-]`

4. Estrutura semântica:
- exatamente 0 `h1` no corpo do HTML package (H1 fica no título nativo do WordPress)
- presença de FAQ em HTML
- presença de FAQ JSON-LD
- presença de Article JSON-LD
- FAQ HTML semântico com `FAQPage` + `Question` + `acceptedAnswer`
- FAQ com pelo menos 5 pares pergunta/resposta completos
- presença obrigatória de `<section class="sowads-cta">`

5. Link policy:
- sem `<a href="http...">`, `<a href="https...">`, `<a href="www...">`

6. Coerência temporal:
- rejeitar referências incorretas para 2024/2025 em contexto atual

7. Consistência de schema:
- `HowTo` só permitido se houver passos reais (lista ordenada ou seção de passos)

8. Qualidade factual mínima:
- detectar percentuais sem evidência contextual próxima (heurística local)

9. Antigeneric opening:
- reprovar abertura com padrões proibidos (`no cenário atual`, `você sabia que`, etc.)

10. Estrutura visual mínima:
- exigir 2 a 3 recursos visuais por artigo, escolhidos conforme o tema (`<ol>`, `<ul>`, mini-checklist, `<table>`, `<blockquote>`, frases-âncora em `<strong>`)
- reprovar excesso visual (4+ recursos no mesmo artigo)
- exigir que o primeiro elemento visual estrutural apareça de forma natural após o 2º, 3º ou 4º parágrafo (e antes da metade do artigo)
- tabela (quando houver) deve estar legível com bordas/linhas visíveis e header distinto
- células da tabela (quando houver) devem ser objetivas (sem reticências, truncamentos artificiais ou placeholders)

11. Anti-template e variação estrutural:
- detectar blocos fixos padronizados proibidos (ex.: "Painel tático", "Resumo executivo em bullet points")
- detectar repetição de arquitetura de headings entre artigos do mesmo lote (assinatura estrutural repetida)

12. Ênfase inteligente:
- reprovar excesso de negrito no corpo (densidade de `<strong>` acima do limite operacional)
- negrito deve focar termos técnicos, regras operacionais e frases de decisão estratégica

13. Faixa de tamanho:
- reprovar abaixo de 900 palavras
- reprovar acima de 1500 palavras (evitar fadiga de leitura e prolixidade)
- reprovar presença de parágrafos excessivamente longos (muro de texto)

14. Higiene de saída e encerramento:
- reprovar artefatos (` ``` `, separadores `====`) no HTML final
- reprovar cauda com repetição excessiva de frases

15. Variação de títulos:
- título do post (H1 WP) e Meta Title não podem ser praticamente idênticos (evitar duplicação semântica de headline)

16. GEO e evidência:
- cada bloco H2 deve abrir com parágrafo-resumo autossuficiente (35-80 palavras)
- exigir ao menos 1 referência verificável (fonte + ano) em texto simples

## Saída esperada
Para cada item:
- lista de `reason_codes`
- lista de `issues`
- impacto no score
- guidance objetivo de correção
