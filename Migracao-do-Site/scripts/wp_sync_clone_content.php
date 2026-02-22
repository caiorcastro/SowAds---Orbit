<?php
if (!defined('ABSPATH')) {
    require_once __DIR__ . '/../../legado/WP_LOCAL/wp-load.php';
}

$theme_dir = get_template_directory();
$site_url = home_url('/');

$pages = array(
    'home-squarespace' => 'index.html',
    'redesefranquias' => 'redesefranquias.html',
    'sowads-orbit-ai' => 'sowads-orbit-ai.html',
    'termos-de-servico' => 'termos-de-servico.html',
    'politica-de-privacidade' => 'politica-de-privacidade.html',
    'data-request-policy' => 'data-request-policy.html',
    'cart' => 'cart.html',
);

$route_replacements = array(
    '/index.html' => '/',
    '/redesefranquias.html' => '/redesefranquias/',
    '/sowads-orbit-ai.html' => '/sowads-orbit-ai/',
    '/termos-de-servico.html' => '/termos-de-servico/',
    '/politica-de-privacidade.html' => '/politica-de-privacidade/',
    '/data-request-policy.html' => '/data-request-policy/',
    '/cart.html' => '/cart/',
);

foreach ($pages as $slug => $source_file) {
    $source_path = $theme_dir . '/sowads.com/' . $source_file;
    if (!file_exists($source_path)) {
        echo "[ERRO] Arquivo nao encontrado: {$source_path}\n";
        continue;
    }

    $html = file_get_contents($source_path);
    if ($html === false) {
        echo "[ERRO] Falha ao ler: {$source_path}\n";
        continue;
    }

    if (!preg_match('/<main id="page" class="container" role="main">(.*)<\/main>/is', $html, $matches)) {
        echo "[ERRO] Nao encontrou <main> em {$source_file}\n";
        continue;
    }

    $content = trim($matches[1]);

    // Troca dominios legados para o dominio atual.
    $content = str_replace(
        array(
            'https://www.sowads.com.br',
            'http://www.sowads.com.br',
            'https://www.sowads.com',
            'http://www.sowads.com',
            '//www.sowads.com',
            '//www.sowads.com.br',
        ),
        untrailingslashit($site_url),
        $content
    );

    // Normaliza rotas internas legadas (*.html).
    foreach ($route_replacements as $from => $to) {
        $content = str_replace(
            array(
                'href="' . $from . '"',
                'href="./' . ltrim($from, '/') . '"',
                'href="' . untrailingslashit($site_url) . $from . '"',
                'action="' . $from . '"',
                'action="' . untrailingslashit($site_url) . $from . '"',
            ),
            array(
                'href="' . $to . '"',
                'href="' . $to . '"',
                'href="' . untrailingslashit($site_url) . $to . '"',
                'action="' . $to . '"',
                'action="' . untrailingslashit($site_url) . $to . '"',
            ),
            $content
        );
    }

    $page = get_page_by_path($slug, OBJECT, 'page');
    if (!$page) {
        echo "[AVISO] Pagina nao encontrada para slug: {$slug}\n";
        continue;
    }

    $result = wp_update_post(
        array(
            'ID' => $page->ID,
            'post_content' => $content,
        ),
        true
    );

    if (is_wp_error($result)) {
        echo "[ERRO] Falha ao atualizar {$slug}: " . $result->get_error_message() . "\n";
        continue;
    }

    echo "[OK] {$slug} atualizado (ID {$page->ID})\n";
}
