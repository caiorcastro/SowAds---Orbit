# Política de Custo

## Princípios
- Modelo padrão: `gemini-2.5-flash`.
- Evitar judge LLM quando gate determinístico resolve.
- Rewrite é seletivo por `id` flagado.
- Não gerar imagem antes de aprovação editorial/técnica.

## Ordem de eficiência
1. Determinístico (regex, parsing, score local)
2. Heurístico (sem chamada LLM)
3. LLM judge (somente incerteza real)

## Variáveis de custo estimado
Configurar no `.env`:
- `GEMINI_INPUT_COST_PER_1M_USD`
- `GEMINI_OUTPUT_COST_PER_1M_USD`

## Fórmula usada
`estimated_cost_usd = (prompt_tokens/1_000_000 * input_rate) + (output_tokens/1_000_000 * output_rate)`

## Origem de tokens
- Preferência: `usageMetadata` retornado pela API.
- Fallback (somente para estimativa): aproximação por tamanho de texto quando usage não vier.

## Onde auditar custo
- `data/logs/gemini_calls.jsonl` em `cost_estimate`.
- O custo é estimado; request/response/status/horário são reais.

## Estratégias recomendadas para reduzir custo
- lotes menores na fase de calibração;
- congelar prompts de agentes após aprovação;
- cache por `id+version` para evitar reruns idênticos;
- usar `test_mode=true` para QA de infraestrutura sem chamar LLM.
