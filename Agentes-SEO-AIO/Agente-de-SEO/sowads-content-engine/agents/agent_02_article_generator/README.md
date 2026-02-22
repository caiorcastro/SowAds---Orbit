# Agent 02 — Article Generator (Core)

## Missão
Gerar artigo final WordPress-ready com qualidade editorial e conformidade técnica, usando integralmente:
- `system/system.md` como System Prompt efetivo.
- `system/user.md` como User Prompt template.

## Escopo
- Geração inicial de artigo.
- Reescrita seletiva (`REWRITE_ONLY`) por `id+version`.

## Entradas
- Linha de `themes.csv`.
- `id`, `batch_id`, `version`.
- `rewrite_guidance` opcional (vindo dos Agentes 03/04).

## Saída
`articles_vN.csv` com `content_package` em 2 blocos obrigatórios:
1. `=== META INFORMATION ===`
2. `=== HTML PACKAGE — WORDPRESS READY ===`

## Regras obrigatórias
- Sem texto fora dos 2 blocos.
- Sem link externo.
- Ano de referência: 2026.
- Slug em kebab-case.
- FAQ + Article schema conforme v8.0.
- Linguagem consistente com posicionamento Sowads.
- Estrutura visual obrigatória: mínimo 1 tabela + 1 lista real.
- Inserção natural dos blocos visuais: primeira metade do artigo (evitar “apêndice” no final).
- Evitar duplicação de headline: H1 e Meta Title devem ser próximos em intenção, mas diferentes em construção.
- Higiene de encerramento: sem artefatos (` ``` ` / `====`) e sem repetição de cauda.

## Reescrita seletiva
- Mantém mesmo `id`.
- Incrementa `version`.
- Reescreve apenas pontos do guidance, sem colar estrutura anterior.
- Deve reduzir similaridade sem perder foco semântico.

## Falhas e fallback
- Resposta fora de contrato: logar e cair em fallback local no modo permitido.
- Falha de API: registrar em `gemini_calls.jsonl` e manter rastreabilidade.

## Execução isolada
```bash
python orchestrator/run_pipeline.py \
  --agent agent02 \
  --themes-file data/batches/BATCH-.../themes.csv \
  --async-output
```
