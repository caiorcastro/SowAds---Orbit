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
- exatamente 1 `h1`
- presença de FAQ em HTML
- presença de FAQ JSON-LD
- presença de Article JSON-LD

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
- exigir presença de listas e tabela no HTML (`<ul>/<ol>` e `<table>`)
- exigir que esses elementos apareçam na primeira metade do artigo (evitar bloco visual só no final)
- tabela deve estar legível com bordas/linhas visíveis e header distinto

11. Higiene de saída e encerramento:
- reprovar artefatos (` ``` `, separadores `====`) no HTML final
- reprovar cauda com repetição excessiva de frases

12. Variação de títulos:
- H1 e Meta Title não podem ser praticamente idênticos (evitar duplicação semântica de headline)

## Saída esperada
Para cada item:
- lista de `reason_codes`
- lista de `issues`
- impacto no score
- guidance objetivo de correção
