# Guia Rapido - Gutenberg no Padrao SOWADS

## O que foi habilitado

- Templates novos de pagina:
  - `SOWADS Conversao`
  - `SOWADS Conteudo`
- Padroes de bloco SOWADS:
  - `SOWADS Hero Conversao`
  - `SOWADS Grid de Servicos`
  - `SOWADS CTA Band`
- Estilo visual aplicado no editor e no front para paginas novas.
- Paginas clonadas (`orbit`, `redes`, etc.) agora aceitam **secoes extras editaveis** no final, via Gutenberg.

## Como criar pagina nova linda no padrao

1. Acesse `Paginas > Adicionar nova`.
2. No painel direito, em `Template`, selecione:
   - `SOWADS Conversao` para landing pages.
   - `SOWADS Conteudo` para paginas mais editoriais.
3. Clique no inseridor de blocos, abra categoria `SOWADS` e insira os padroes.
4. Edite textos, botoes e secoes.
5. Publice.

## Como editar pagina clonada sem quebrar clone

1. Abra a pagina clonada (ex: `Sowads Orbit Ai`).
2. No Gutenberg, adicione blocos normalmente.
3. Esses blocos serao renderizados no front na area **extra** ao final da pagina, preservando o clone original.

## Importante

- O corpo principal do clone ainda vem de arquivos `page-*.php`.
- Para alterar texto estrutural do clone pixel-perfect (miolo da pagina), e necessario fazer ajuste no template correspondente.
