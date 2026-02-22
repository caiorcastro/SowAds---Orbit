# Acessos e Operacao

## Login WordPress
- URL: `https://resultsquad.com.br/wp-admin`
- Login atual: `admin`
- Senha atual: `admin`

## Teste de login tecnico
O servidor aceita `admin/admin` e redireciona para `/wp-admin/`.
Se nao entrar no navegador:
1. abrir em janela anonima
2. limpar cookies de `resultsquad.com.br`
3. desativar extensoes de bloqueio para teste
4. tentar `https://resultsquad.com.br/wp-login.php`

## SSH
- Host: `147.93.37.148`
- Porta: `65002`
- Usuario: `u957947211`
- Senha: usar variavel em `.env.local` (nao comitar)

## Estrutura no servidor
- Docroot: `/home/u957947211/domains/resultsquad.com.br/public_html`
- Tema: `wp-content/themes/sowads`
- SQLite: `wp-content/database/.ht.sqlite`
