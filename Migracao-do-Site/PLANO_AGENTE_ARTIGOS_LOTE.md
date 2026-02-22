# Plano: Agente de Artigos em Lote

## Objetivo
Gerar e publicar centenas/milhares de artigos com qualidade minima, controle de estrutura e importacao segura.

## Recomendacao de stack
- Geracao: pipeline local (JSON/CSV intermediario)
- Publicacao: priorizar `WP-ALL-IMPORT` para lotes grandes
- Complemento: REST API para ajustes incrementais (status, categorias, meta)
- SSH/WP-CLI: manutencao, jobs e verificacoes

## Arquitetura proposta
1. `Coletor de pauta`
   - recebe temas, palavras-chave, personas, clusters
2. `Gerador`
   - produz titulo, slug, resumo, corpo, FAQ, metadados
3. `Validador`
   - evita duplicidade
   - valida tamanho, heading structure, links internos
4. `Empacotador`
   - exporta CSV/XML no formato do WP All Import
5. `Importador`
   - cria/atualiza posts
6. `Pos-processamento`
   - vincula categorias/tags
   - seta featured image
   - atualiza status (draft/publish)

## Fluxo recomendado (MVP)
1. Gerar 50 artigos em `draft`
2. Revisar qualidade e padrao
3. Escalar para 500
4. Escalar para 1000+

## Formato minimo de campos
- `post_title`
- `post_name` (slug)
- `post_content`
- `post_excerpt`
- `post_status` (`draft`/`publish`)
- `post_date`
- `category`
- `tags`
- `featured_image_url`
- `seo_title`
- `seo_description`

## Controle de qualidade
- max 1 H1, hierarquia H2/H3 coerente
- sem canibalizacao de slug
- links internos para paginas de dinheiro
- densidade de keyword natural
- checagem de plágio e factualidade

## Operacao e performance
- importar em lotes de 100-300
- executar fora de horario pico
- monitorar timeout/memoria no import
- manter rollback por lote

## Estrategia de publicacao
- lote inicial em `draft`
- aprovacao humana por amostra
- publicar progressivo (ex: 20/dia)

## Ferramenta: quando usar cada via
- `WP All Import`: volume alto, mapeamento visual, reimport
- `REST API`: operacoes pontuais e automacao continua
- `SSH/WP-CLI`: jobs, limpeza, ajustes massivos de metadados

## Proximos passos praticos
1. Definir taxonomia final (categorias e tags)
2. Definir template de artigo
3. Criar schema CSV v1
4. Implementar gerador de lote v1
5. Rodar piloto com 50 artigos
