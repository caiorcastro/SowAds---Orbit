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


def sanitize_article_html(html: str) -> str:
    html = _normalize_newlines(html)
    html = _remove_trailing_noise(html)
    html = _clip_to_article(html)
    html = _remove_trailing_noise(html)
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

