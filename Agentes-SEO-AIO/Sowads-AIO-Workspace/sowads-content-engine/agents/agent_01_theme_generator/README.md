# Agent 01 — Theme Generator

## Missão
Gerar pautas acionáveis e completas para alimentar o Agente 02, já com parâmetros compatíveis com `system/user.md`.

## Escopo
- Cria temas e metadados editoriais.
- Não escreve artigo.
- Não inventa volume absoluto de busca.

## Entradas
- `nicho`
- `vertical_alvo`
- `porte_empresa_alvo`
- `modelo_negocio_alvo`
- `produto_sowads_foco`
- `quantidade_temas`
- `restricoes`
- `url_interna` (opcional)

## Saída
CSV `themes.csv` (contrato fixo) com colunas:
`id,timestamp,tema_principal,keyword_primaria,keywords_secundarias,porte_empresa_alvo,modelo_negocio_alvo,vertical_alvo,produto_sowads_foco,angulo_conteudo,url_interna,funil,busca,titulo_anuncio,notes`

## Regras obrigatórias
- `funil`: apenas `TOFU|MOFU|BOFU`.
- `busca`: apenas `Alta|Média|Baixa`.
- `keywords_secundarias`: separadas por `|`.
- Garantir diversidade temática no lote.
- Não repetir `keyword_primaria` em temas distintos do mesmo batch.

## Critérios de qualidade
- Tema deve ter utilidade editorial real (evitar genericão).
- Alinhamento explícito ao porte e vertical.
- Ângulo de conteúdo coerente com objetivo.

## Falhas e fallback
- Falha de LLM: registra log e usa fallback local para continuidade.
- CSV inválido: bloquear fase seguinte até ajuste.

## Execução isolada (assíncrona)
```bash
python orchestrator/run_pipeline.py --agent agent01 --async-output
```
