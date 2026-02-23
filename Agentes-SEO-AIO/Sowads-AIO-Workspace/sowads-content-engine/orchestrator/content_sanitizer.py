#!/usr/bin/env python3
import re
from typing import Tuple


META_MARKER = "=== META INFORMATION ==="
HTML_MARKER = "=== HTML PACKAGE — WORDPRESS READY ==="


def _normalize_newlines(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return text.lstrip("\ufeff")


def _strip_tags(text: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _strip_tags_keep_case(text: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sanitize_meta_block(meta: str) -> str:
    meta = _normalize_newlines(meta)
    cleaned = []
    for raw in meta.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("```"):
            continue
        if re.fullmatch(r"[=\-`\"'“”]{8,}", line):
            continue
        cleaned.append(raw.rstrip())
    return "\n".join(cleaned).strip()


def _remove_trailing_noise(text: str) -> str:
    text = _normalize_newlines(text)
    text = re.sub(r"^\s*```(?:html)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.I)
    text = re.sub(r"\n\s*={8,}[\s\S]*$", "", text)
    text = re.sub(r"\n\s*[\"'`“”]+\s*$", "", text)
    return text.strip()


def _clip_to_article(html: str) -> str:
    if not html:
        return ""
    html = _normalize_newlines(html)
    start_match = re.search(r"<article\b[^>]*>", html, flags=re.I)
    if start_match:
        html = html[start_match.start():]
        end_match = re.search(r"</article>", html, flags=re.I)
        if end_match:
            html = html[: end_match.end()]
    return html


def _unwrap_article_root(html: str) -> str:
    """Avoid nested <article> in WP single template by normalizing the body root to a div."""
    if not html:
        return ""
    html = html.strip()
    open_match = re.match(r"<article\b[^>]*>", html, flags=re.I)
    close_match = re.search(r"</article>\s*$", html, flags=re.I)
    if not open_match or not close_match:
        return html
    if open_match.end() >= close_match.start():
        return html
    inner = html[open_match.end(): close_match.start()].strip()
    if not inner:
        return '<div class="sowads-article-body"></div>'
    return f'<div class="sowads-article-body">\n{inner}\n</div>'


def _dedupe_repeated_trailing_paragraphs(html: str, min_chars: int = 40) -> str:
    pattern = re.compile(r"<p\b[^>]*>[\s\S]*?</p>", flags=re.I)
    for _ in range(12):
        blocks = list(pattern.finditer(html))
        if len(blocks) < 2:
            break
        last = blocks[-1]
        prev = blocks[-2]
        t_last = _strip_tags(last.group(0))
        t_prev = _strip_tags(prev.group(0))
        if not t_last or t_last != t_prev:
            break
        if len(t_last) < min_chars:
            break
        html = html[: last.start()] + html[last.end():]
    return html.strip()


def _unwrap_script_paragraphs(html: str) -> str:
    # Avoid invalid HTML like <p><script ...></script></p>
    return re.sub(
        r"<p[^>]*>\s*(<script[^>]*>[\s\S]*?</script>)\s*</p>",
        r"\1",
        html,
        flags=re.I,
    )


def _demote_body_h1_to_h2(html: str) -> str:
    def _open_tag_repl(match: re.Match) -> str:
        attrs = match.group(1) or ""
        # headline should be represented in structured data, not in duplicated body H1.
        attrs = re.sub(r"\s*itemprop\s*=\s*['\"]headline['\"]", "", attrs, flags=re.I)
        return f"<h2{attrs}>"

    html = re.sub(r"<h1([^>]*)>", _open_tag_repl, html, flags=re.I)
    html = re.sub(r"</h1>", "</h2>", html, flags=re.I)
    return html


def _ensure_faq_semantic_markup(html: str) -> str:
    def _extract_pairs(raw: str):
        pairs = []
        sem_re = re.compile(
            r'itemprop=[\'"]name[\'"][^>]*>([\s\S]*?)</h3>[\s\S]*?itemprop=[\'"]text[\'"][^>]*>([\s\S]*?)</p>',
            flags=re.I,
        )
        for m in sem_re.finditer(raw):
            q = _strip_tags_keep_case(m.group(1))
            a = _strip_tags_keep_case(m.group(2))
            if q and a:
                pairs.append((q, a))
        if pairs:
            return pairs[:8]
        raw_re = re.compile(r"<h3[^>]*>([\s\S]*?)</h3>[\s\S]*?<p[^>]*>([\s\S]*?)</p>", flags=re.I)
        for m in raw_re.finditer(raw):
            q = _strip_tags_keep_case(m.group(1))
            a = _strip_tags_keep_case(m.group(2))
            if q and a:
                pairs.append((q, a))
        return pairs[:8]

    section_re = re.compile(
        r"(<section[^>]*class=[\"'][^\"']*faq-section[^\"']*[\"'][^>]*>)([\s\S]*?)(</section>)",
        flags=re.I,
    )

    def _section_repl(match: re.Match) -> str:
        body = match.group(2)
        title_match = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", body, flags=re.I)
        title_text = _strip_tags_keep_case(title_match.group(1)) if title_match else "Perguntas Frequentes"
        if not title_text:
            title_text = "Perguntas Frequentes"
        pairs = _extract_pairs(body)
        if not pairs:
            return match.group(0)
        qa_html = []
        for q, a in pairs:
            qa_html.append(
                '<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">'
                f'<h3 itemprop="name">{q}</h3>'
                '<div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">'
                f'<p itemprop="text">{a}</p>'
                "</div>"
                "</div>"
            )
        return (
            '<section class="faq-section" itemscope itemtype="https://schema.org/FAQPage">'
            f"<h2>{title_text}</h2>"
            + "".join(qa_html)
            + "</section>"
        )

    return section_re.sub(_section_repl, html)


def _split_long_paragraphs(html: str, max_words: int = 70, target_words: int = 46) -> str:
    paragraph_re = re.compile(r"<p([^>]*)>([\s\S]*?)</p>", flags=re.I)

    def _repl(match: re.Match) -> str:
        attrs = match.group(1) or ""
        inner = (match.group(2) or "").strip()
        if not inner:
            return match.group(0)
        # Keep semantic/structured nodes intact.
        if re.search(r"<(script|style|img|iframe|table|ul|ol|blockquote)\b", inner, flags=re.I):
            return match.group(0)
        plain = _strip_tags_keep_case(inner)
        wc = len(re.findall(r"[\wÀ-ÿ-]+", plain))
        if wc <= max_words:
            return match.group(0)

        parts = re.split(r"(?<=[\.\!\?])\s+", plain)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            return match.group(0)

        chunks = []
        buf = []
        buf_words = 0
        for sent in parts:
            sw = len(re.findall(r"[\wÀ-ÿ-]+", sent))
            if buf and buf_words + sw > target_words:
                chunks.append(" ".join(buf).strip())
                buf = [sent]
                buf_words = sw
            else:
                buf.append(sent)
                buf_words += sw
        if buf:
            chunks.append(" ".join(buf).strip())

        if len(chunks) < 2:
            return match.group(0)

        built = []
        for ch in chunks:
            built.append(f"<p{attrs}>{ch}</p>")
        return "".join(built)

    return paragraph_re.sub(_repl, html)


def sanitize_article_html(html: str) -> str:
    html = _normalize_newlines(html)
    html = _remove_trailing_noise(html)
    # Legacy cleanup: remove deprecated generic readability pack block if present.
    html = re.sub(
        r"<section[^>]*id=[\"']sowads-readability-pack[\"'][^>]*>[\s\S]*?</section>",
        "",
        html,
        flags=re.I,
    )
    html = html.replace("**", "")
    html = _unwrap_script_paragraphs(html)
    html = _clip_to_article(html)
    html = _unwrap_article_root(html)
    html = _demote_body_h1_to_h2(html)
    html = _split_long_paragraphs(html)
    html = _ensure_faq_semantic_markup(html)
    html = _remove_trailing_noise(html)
    html = _unwrap_script_paragraphs(html)
    html = _dedupe_repeated_trailing_paragraphs(html)
    return html.strip()


def split_content_package(content_package: str) -> Tuple[str, str, bool]:
    content_package = _normalize_newlines(content_package)
    if META_MARKER in content_package and HTML_MARKER in content_package:
        after_meta = content_package.split(META_MARKER, 1)[1]
        meta_raw = after_meta.split(HTML_MARKER, 1)[0]
        html_raw = after_meta.split(HTML_MARKER, 1)[1]
        meta = sanitize_meta_block(meta_raw)
        html = sanitize_article_html(html_raw)
        return meta, html, True
    html = sanitize_article_html(content_package)
    return "", html, False


def build_content_package(meta: str, html: str, with_markers: bool = True) -> str:
    meta = sanitize_meta_block(meta)
    html = sanitize_article_html(html)
    if with_markers:
        return f"{META_MARKER}\n{meta}\n\n{HTML_MARKER}\n{html}".strip()
    return html.strip()
