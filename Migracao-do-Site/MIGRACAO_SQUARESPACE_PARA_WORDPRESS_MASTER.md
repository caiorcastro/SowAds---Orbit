# Master Playbook Geral: Squarespace -> WordPress

## 1) Quando usar este playbook
- Site de origem está em Squarespace.
- Projeto precisa ir para WordPress com controle total.
- Pode ser clone visual, rebuild parcial ou rebuild completo.

## 2) Estratégias possíveis
- Estrategia A (recomendada): reconstruir layout em tema/page builder no WordPress.
  - Melhor manutenção e performance no longo prazo.
- Estrategia B (rápida): portar HTML exportado para tema custom.
  - Mais rápida no curto prazo.
  - Exige camada de compatibilidade para links/rotas/assets legados.

## 3) Pré-migração
- Inventário completo:
  - URLs, menus, páginas, blog, formulários, scripts de tracking.
- Exportar/espelhar conteúdo e assets.
- Definir regra de URL no WordPress (slugs finais).
- Escolher banco (MySQL padrão ou SQLite em casos específicos).

## 4) Implementação no WordPress
1. Provisionar WordPress limpo.
2. Criar tema base do projeto.
3. Migrar HTML/CSS/JS e ativos.
4. Ajustar cabeçalho/rodapé para WP.
5. Criar páginas com templates corretos.
6. Configurar permalinks.
7. Implementar redirects legados (`.html`, paths antigos).

## 5) Compatibilidade crítica
- Links internos:
  - Converter `*.html` para slugs WordPress.
  - Remover dependência de domínio antigo.
- Assets:
  - Garantir que todos os arquivos necessários estejam locais ou com fallback estável.
- Fontes/CDN:
  - Validar HTTP 200 em CSS/JS/fontes externas.

## 6) SEO e rastreabilidade
- Ajustar:
  - Canonical, Open Graph, Twitter cards, sitemap.
- Mapear 301:
  - URLs antigas -> novas.
- Conferir Search Console depois da virada.

## 7) Banco: MySQL vs SQLite
- MySQL:
  - Padrão WordPress.
  - Melhor para escala e compatibilidade ampla.
- SQLite:
  - Excelente portabilidade e setup rápido.
  - Exige validação de plugins e cenário de carga.

## 8) Go-live seguro
- Ativar manutenção curta.
- Backup completo pré-corte.
- Deploy.
- Purge de cache.
- Smoke test de navegação (desktop/mobile).
- Monitorar logs e erros por 24-48h.

## 9) Checklist pós-migração
- Home e páginas principais ok.
- Menu/rodapé com links corretos.
- Imagens e fontes carregando.
- Formulários funcionando.
- Redirecionamentos 301 válidos.
- Admin WordPress acessível e com usuários corretos.

## 10) Gestão contínua
- Registrar decisões técnicas em documentação.
- Versionar tema em Git.
- Padronizar rotina:
  - Backup
  - Atualização de plugins/tema
  - Verificação de links quebrados
  - Revisão de performance
