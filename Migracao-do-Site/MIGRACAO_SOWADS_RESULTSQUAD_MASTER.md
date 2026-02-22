# Master Playbook: SOWADS -> ResultSquad (Caso Especifico)

## 1) Objetivo
- Migrar clone visual do site SOWADS (origem Squarespace) para `resultsquad.com.br` em WordPress (Hostinger), mantendo visual e comportamento.
- Garantir links internos funcionais sem depender do domínio antigo.

## 2) Contexto Técnico do Caso
- Origem: Squarespace (HTML exportado/espelhado).
- Destino: WordPress na Hostinger.
- Banco: SQLite via plugin `sqlite-database-integration` (sem MySQL).
- Tema ativo: `sowads`.

## 3) Acessos
- WP Admin: `https://resultsquad.com.br/wp-admin`
- Usuário/Senha: `admin` / `admin` (trocar imediatamente).

## 4) Fluxo de Portabilidade Usado
1. Upload do pacote WordPress para `public_html`.
2. Extração e sincronização para raiz (`index.php`, `wp-content`, etc).
3. Remoção de `index.html` legado que bloqueava WordPress.
4. Ajustes de compatibilidade:
   - Redirect de links legados `.html`.
   - Reescrita de links antigos (`sowads.com`) para domínio atual.
   - Correção de carregamento Typekit.

## 5) Problemas Encontrados e Correções
- Problema: `resultsquad.com.br/redesefranquias/redesefranquias.html` abrindo página placeholder.
  - Causa: links `.html` relativos herdados do export.
  - Correção: rewrite runtime no tema + redirects no `.htaccess`.

- Problema: links apontando para `sowads.com`.
  - Causa: HTML legado com URLs absolutas antigas.
  - Correção: reescrita de domínio na saída HTML.

- Problema: fonte/estilo quebrando em alguns pontos.
  - Causa: URL Typekit reescrita inválida.
  - Correção: regra de redirect para `use.typekit.net`.

## 6) Operação Diária (Edição)
- Páginas: `Páginas` no wp-admin.
- Artigos: `Posts` no wp-admin.
- SEO básico: título, slug, imagem destacada e metadados.
- Mudanças pixel-perfect maiores: arquivos do tema `wp-content/themes/sowads`.

## 7) Checklist Pós-Deploy
- Home abre com layout SOWADS.
- Menus e CTAs não levam para `sowads.com`.
- Rotas legadas `.html` redirecionam para slugs WordPress.
- Console sem erros críticos de JS/CSS.
- Páginas institucionais carregam conteúdo completo.

## 8) Segurança e Governança
- Trocar senha do `admin`.
- Criar usuário editor para operação diária.
- Ativar backup automático de arquivos + banco SQLite.
- Manter versão do tema em Git.

## 9) SQLite no Dia a Dia
- Igual ao MySQL para edição comum de páginas/posts.
- Vantagem: migração/backup simples (arquivo único do banco).
- Atenção:
  - Compatibilidade de alguns plugins.
  - Escala de escrita concorrente alta pode exigir MySQL.

## 10) Plano de Evolução
1. Implementar sistema de artigos (categoria, template, URL `/artigos`).
2. Revisar SEO técnico e canonicals.
3. Medir performance e ajustar cache/CDN.
