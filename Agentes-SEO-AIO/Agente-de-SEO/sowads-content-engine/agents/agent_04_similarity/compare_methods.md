# Compare Methods — Agent 04

## Método A — Jaccard (shingles 3-gram)
- Remove HTML.
- Normaliza caixa e pontuação.
- Compara conjuntos de trigrams para captar sobreposição de sequência.

## Método B — Cosine (bag-of-words)
- Vetoriza tokens relevantes.
- Mede proximidade global do vocabulário.

## Método C — Heurística semântica local
- bônus de semelhança quando keyword primária coincide;
- reforço de risco por similaridade de headings/funil/ângulo.

## Score consolidado
Exemplo de ponderação operacional:
- Jaccard: 45%
- Cosine: 45%
- Semântico local: 10%

## Boas práticas
- Conflito de score alto sem evidência textual deve ser revisado.
- Não classificar risco com base em apenas um sinal fraco.
