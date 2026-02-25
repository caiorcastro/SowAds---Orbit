#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import string
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import urllib.error
import urllib.parse
import urllib.request

from content_sanitizer import build_content_package, split_content_package


THEME_COLUMNS = [
    "id",
    "timestamp",
    "tema_principal",
    "keyword_primaria",
    "keywords_secundarias",
    "porte_empresa_alvo",
    "modelo_negocio_alvo",
    "vertical_alvo",
    "produto_sowads_foco",
    "angulo_conteudo",
    "url_interna",
    "funil",
    "busca",
    "titulo_anuncio",
    "notes",
]

ARTICLE_COLUMNS = [
    "batch_id",
    "id",
    "version",
    "tema_principal",
    "keyword_primaria",
    "keywords_secundarias",
    "porte_empresa_alvo",
    "modelo_negocio_alvo",
    "vertical_alvo",
    "produto_sowads_foco",
    "angulo_conteudo",
    "url_interna",
    "slug",
    "meta_title",
    "meta_description",
    "content_package",
    "status",
]

IMAGE_PROMPT_COLUMNS = [
    "id",
    "article_title",
    "slug",
    "dimensions",
    "style",
    "prompt",
    "negative_prompt",
]

ASYNC_ROOT = "outputs/assincronos"

GENERIC_OPENINGS = [
    "no cenario atual",
    "no mundo digital de hoje",
    "voce sabia que",
    "vivemos em uma era",
    "em um mercado cada vez mais",
    "nos dias de hoje",
    "atualmente as empresas",
    "com a evolucao da tecnologia",
]

BANNED_OPENING_STARTS = [
    "em 2026",
    "atualmente",
    "nos dias de hoje",
    "no cenario atual",
    "no mundo digital de hoje",
    "em um mercado cada vez mais",
]

STRUCTURE_PROFILES = [
    ("Diagnostico-Playbook", "diagnóstico direto, causa-raiz, plano de ação e erros críticos"),
    ("Tese-Framework-Decisao", "tese executiva, framework de decisão, próximos passos"),
    ("Comparativo-Criterios", "comparação por critérios, trade-offs, recomendação por cenário"),
    ("Operacao-90-Dias", "execução por fases com checkpoints operacionais e de negócio"),
    ("Sintoma-Causa-Impacto", "sinais, causa, impacto, correção orientada por dados"),
]

NARRATIVE_FRAMES = [
    ("Hipotese-Validacao", "abrir com hipótese executiva, validar com sinais e fechar com decisão"),
    ("Diagnostico-Executivo", "abrir com sintoma operacional, destrinchar causa-raiz e fechar com plano"),
    ("Playbook-Pratico", "abrir com meta de negócio, sequenciar ações e checkpoints de execução"),
    ("Tradeoff-Decisao", "abrir com dilema real, comparar caminhos e recomendar decisão por cenário"),
    ("Caso-Aplicado", "abrir com micro-cenário realista, extrair aprendizados e operacionalizar"),
    ("Risco-Controle", "abrir com risco invisível, mapear impacto e definir controles preventivos"),
]

VISUAL_MIXES = [
    ("Lista+Tabela", ["lista numerada", "tabela simples"]),
    ("Bullets+Checklist", ["bullets objetivos", "mini-checklist"]),
    ("Tabela+Blockquote", ["tabela simples", "blockquote de síntese"]),
    ("Lista+Bullets+Anchor", ["lista numerada", "bullets", "frases-âncora em negrito"]),
    ("Checklist+Tabela", ["mini-checklist", "tabela simples"]),
    ("Bullets+Blockquote", ["bullets objetivos", "blockquote de decisão"]),
]

CRITICAL_REASON_CODES = {
    "missing_blocks",
    "meta_title_too_long",
    "meta_description_too_long",
    "meta_description_missing",
    "external_link",
    "invalid_slug",
    "body_h1_present",
    "faq_missing",
    "faq_answers_missing",
    "faq_html_semantic_missing",
    "article_schema_missing",
    "article_schema_incomplete",
    "temporal_incoherence",
    "malformed_tail",
    "repetitive_tail",
    "low_visual_structure",
    "visual_overload",
    "late_visual_structure",
    "word_count_high",
    "long_paragraphs",
    "geo_block_weak",
    "cta_missing",
    "sources_missing",
    "bold_overuse",
    "fixed_blocks_detected",
    "repeated_structure_pattern",
    "examples_missing",
    "hard_opening_banned",
    "table_verbose",
    "table_ellipsis",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def batch_id_now(topic: str = "") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    topic = (topic or "").strip().lower()
    topic = re.sub(r"[^a-z0-9]+", "-", topic).strip("-")
    if topic:
        return f"BATCH-{topic}-{stamp}"
    return "BATCH-" + stamp


def content_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rnd = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"SOWADS-{stamp}-{rnd}"


def slugify(text: str) -> str:
    text = text.lower().strip()
    # remove accents manually
    mapping = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñ",
        "aaaaaeeeeiiiiooooouuuucn",
    )
    text = text.translate(mapping)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def strip_html(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: List[dict], columns: List[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def write_json(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def extract_json_from_text(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m_obj = re.search(r"\{[\s\S]*\}", text)
    m_arr = re.search(r"\[[\s\S]*\]", text)
    candidates = []
    if m_arr:
        candidates.append(m_arr.group(0))
    if m_obj:
        candidates.append(m_obj.group(0))
    for c in candidates:
        try:
            return json.loads(c)
        except Exception:
            continue
    raise ValueError("Could not parse JSON from model output")


def read_csv(path: Path) -> List[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class GeminiClient:
    api_key: str
    api_base: str
    model: str
    delay_seconds: float = 0.6
    log_file: Optional[Path] = None
    input_cost_per_1m: float = 0.0
    output_cost_per_1m: float = 0.0

    def _estimate_tokens_from_text(self, text: str) -> int:
        # Heuristic fallback (somente para estimativa de custo quando usage não vem da API).
        return max(1, int(round(len(text) / 4)))

    def _build_cost_block(
        self,
        prompt_tokens: Optional[int],
        output_tokens: Optional[int],
        prompt_text: str,
        response_text: str,
    ) -> dict:
        estimated_by_heuristic = False
        if prompt_tokens is None:
            prompt_tokens = self._estimate_tokens_from_text(prompt_text)
            estimated_by_heuristic = True
        if output_tokens is None:
            output_tokens = self._estimate_tokens_from_text(response_text)
            estimated_by_heuristic = True

        estimated_cost_usd = (
            (prompt_tokens / 1_000_000.0) * self.input_cost_per_1m
            + (output_tokens / 1_000_000.0) * self.output_cost_per_1m
        )
        return {
            "prompt_tokens": int(prompt_tokens),
            "output_tokens": int(output_tokens),
            "input_cost_per_1m_usd": self.input_cost_per_1m,
            "output_cost_per_1m_usd": self.output_cost_per_1m,
            "estimated_cost_usd": round(float(estimated_cost_usd), 8),
            "estimated_by_heuristic": estimated_by_heuristic,
            "pricing_configured": (self.input_cost_per_1m > 0.0 or self.output_cost_per_1m > 0.0),
        }

    def _log_call(self, record: dict) -> None:
        if not self.log_file:
            return
        append_jsonl(self.log_file, record)

    def generate_text(self, prompt: str, temperature: float = 0.4, context: Optional[dict] = None) -> str:
        context = context or {}
        started_at = now_iso()
        t0 = time.time()
        endpoint = f"{self.api_base}/models/{self.model}:generateContent?key={urllib.parse.quote(self.api_key)}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response_text = ""
        raw_body = ""
        usage = {}
        status_code = None
        error_message = ""

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw_body = resp.read().decode("utf-8")
                status_code = int(getattr(resp, "status", 200))
        except urllib.error.HTTPError as e:
            status_code = int(getattr(e, "code", 0) or 0)
            raw_body = e.read().decode("utf-8", errors="replace")
            error_message = f"Gemini HTTP {status_code}"
            latency_ms = int((time.time() - t0) * 1000)
            self._log_call(
                {
                    "timestamp": started_at,
                    "completed_at": now_iso(),
                    "latency_ms": latency_ms,
                    "provider": "gemini",
                    "model": self.model,
                    "phase": context.get("phase", ""),
                    "agent": context.get("agent", ""),
                    "batch_id": context.get("batch_id", ""),
                    "id": context.get("id", ""),
                    "version": context.get("version", 0),
                    "http_status_code": status_code,
                    "success": False,
                    "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                    "request": {
                        "temperature": temperature,
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "prompt_text": prompt,
                    },
                    "response_raw": raw_body,
                    "response_text": "",
                    "usage_metadata": {},
                    "cost_estimate": self._build_cost_block(None, None, prompt, ""),
                    "error": error_message,
                }
            )
            raise RuntimeError(f"{error_message}: {raw_body}") from e
        except urllib.error.URLError as e:
            latency_ms = int((time.time() - t0) * 1000)
            error_message = f"Gemini network error: {e}"
            self._log_call(
                {
                    "timestamp": started_at,
                    "completed_at": now_iso(),
                    "latency_ms": latency_ms,
                    "provider": "gemini",
                    "model": self.model,
                    "phase": context.get("phase", ""),
                    "agent": context.get("agent", ""),
                    "batch_id": context.get("batch_id", ""),
                    "id": context.get("id", ""),
                    "version": context.get("version", 0),
                    "http_status_code": 0,
                    "success": False,
                    "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                    "request": {
                        "temperature": temperature,
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "prompt_text": prompt,
                    },
                    "response_raw": "",
                    "response_text": "",
                    "usage_metadata": {},
                    "cost_estimate": self._build_cost_block(None, None, prompt, ""),
                    "error": error_message,
                }
            )
            raise RuntimeError(f"Gemini network error: {e}") from e

        data = json.loads(raw_body)
        usage = data.get("usageMetadata", {}) if isinstance(data, dict) else {}
        cand = data.get("candidates", [])
        if not cand:
            latency_ms = int((time.time() - t0) * 1000)
            self._log_call(
                {
                    "timestamp": started_at,
                    "completed_at": now_iso(),
                    "latency_ms": latency_ms,
                    "provider": "gemini",
                    "model": self.model,
                    "phase": context.get("phase", ""),
                    "agent": context.get("agent", ""),
                    "batch_id": context.get("batch_id", ""),
                    "id": context.get("id", ""),
                    "version": context.get("version", 0),
                    "http_status_code": status_code or 200,
                    "success": False,
                    "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                    "request": {
                        "temperature": temperature,
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "prompt_text": prompt,
                    },
                    "response_raw": raw_body,
                    "response_text": "",
                    "usage_metadata": usage,
                    "cost_estimate": self._build_cost_block(
                        usage.get("promptTokenCount"),
                        usage.get("candidatesTokenCount"),
                        prompt,
                        "",
                    ),
                    "error": "Gemini no candidates",
                }
            )
            raise RuntimeError(f"Gemini no candidates: {raw_body}")
        parts = cand[0].get("content", {}).get("parts", [])
        response_text = "".join(p.get("text", "") for p in parts).strip()
        if not response_text:
            latency_ms = int((time.time() - t0) * 1000)
            self._log_call(
                {
                    "timestamp": started_at,
                    "completed_at": now_iso(),
                    "latency_ms": latency_ms,
                    "provider": "gemini",
                    "model": self.model,
                    "phase": context.get("phase", ""),
                    "agent": context.get("agent", ""),
                    "batch_id": context.get("batch_id", ""),
                    "id": context.get("id", ""),
                    "version": context.get("version", 0),
                    "http_status_code": status_code or 200,
                    "success": False,
                    "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                    "request": {
                        "temperature": temperature,
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "prompt_text": prompt,
                    },
                    "response_raw": raw_body,
                    "response_text": "",
                    "usage_metadata": usage,
                    "cost_estimate": self._build_cost_block(
                        usage.get("promptTokenCount"),
                        usage.get("candidatesTokenCount"),
                        prompt,
                        "",
                    ),
                    "error": "Gemini empty text",
                }
            )
            raise RuntimeError(f"Gemini empty text: {raw_body}")

        latency_ms = int((time.time() - t0) * 1000)
        self._log_call(
            {
                "timestamp": started_at,
                "completed_at": now_iso(),
                "latency_ms": latency_ms,
                "provider": "gemini",
                "model": self.model,
                "phase": context.get("phase", ""),
                "agent": context.get("agent", ""),
                "batch_id": context.get("batch_id", ""),
                "id": context.get("id", ""),
                "version": context.get("version", 0),
                "http_status_code": status_code or 200,
                "success": True,
                "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                "request": {
                    "temperature": temperature,
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "prompt_text": prompt,
                },
                "response_raw": raw_body,
                "response_text": response_text,
                "usage_metadata": usage,
                "cost_estimate": self._build_cost_block(
                    usage.get("promptTokenCount"),
                    usage.get("candidatesTokenCount"),
                    prompt,
                    response_text,
                ),
                "error": "",
            }
        )
        time.sleep(self.delay_seconds)
        return response_text


class Pipeline:
    def __init__(self, base: Path, cfg: dict):
        self.base = base
        self.cfg = cfg
        self.system_md = (base / "system/system.md").read_text(encoding="utf-8")
        self.user_md = (base / "system/user.md").read_text(encoding="utf-8")

        batch_topic = str(cfg.get("batch_topic", "") or "").strip()
        self.batch_id = cfg.get("batch_id") or batch_id_now(batch_topic)
        self.batch_dir = base / "data" / "batches" / self.batch_id
        ensure_dir(self.batch_dir)

        self.logs_file = base / "data/logs/logs.jsonl"
        self.gemini_logs_file = base / "data/logs/gemini_calls.jsonl"
        self.publication_logs = base / "data/logs/publication_log.jsonl"
        self.history_file = base / "data/history/history.jsonl"
        self.history_index = base / "data/history/index.json"
        self.async_root = base / ASYNC_ROOT
        ensure_dir(self.async_root)

        self.test_mode = bool(cfg.get("test_mode", False))
        # Default rewrite loop disabled: quality is enforced in generation + critic refine pass.
        self.max_rewrites = int(cfg.get("max_rewrites", 0))
        self.threshold = 80
        self.min_article_words = int(cfg.get("min_article_words", 900))
        self.max_article_words = int(cfg.get("max_article_words", 1500))
        self.keyword_density_min = float(cfg.get("keyword_density_min_pct", 1.5))
        self.keyword_density_max = float(cfg.get("keyword_density_max_pct", 2.0))

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        api_base = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").strip()
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
        delay = float(os.getenv("REQUEST_DELAY_SECONDS", "0.5"))
        input_cost = float(os.getenv("GEMINI_INPUT_COST_PER_1M_USD", "0.0"))
        output_cost = float(os.getenv("GEMINI_OUTPUT_COST_PER_1M_USD", "0.0"))
        self.gemini = GeminiClient(
            api_key=api_key,
            api_base=api_base,
            model=model,
            delay_seconds=delay,
            log_file=self.gemini_logs_file,
            input_cost_per_1m=input_cost,
            output_cost_per_1m=output_cost,
        )

    def log(self, phase: str, status: str, reason: str = "", metrics: dict = None, item_id: str = "", version: int = 0):
        append_jsonl(
            self.logs_file,
            {
                "timestamp": now_iso(),
                "phase": phase,
                "batch_id": self.batch_id,
                "id": item_id,
                "version": version,
                "status": status,
                "reason": reason,
                "metrics": metrics or {},
                "model": self.gemini.model,
            },
        )

    def _resolve_input_path(self, maybe_path: str) -> Path:
        p = Path(maybe_path)
        if p.is_absolute():
            return p
        return (self.base / maybe_path).resolve()

    def _load_themes_from_csv(self, csv_path: Path) -> List[dict]:
        rows = read_csv(csv_path)
        out = []
        for r in rows:
            out.append({k: r.get(k, "") for k in THEME_COLUMNS})
        return out

    def _load_articles_from_csv(self, csv_path: Path) -> Dict[str, dict]:
        rows = read_csv(csv_path)
        out = {}
        for r in rows:
            item_id = r.get("id", "").strip()
            if not item_id:
                continue
            rec = {k: r.get(k, "") for k in ARTICLE_COLUMNS}
            try:
                rec["version"] = int(str(rec.get("version", "1")).strip() or "1")
            except Exception:
                rec["version"] = 1
            out[item_id] = rec
        return out

    def _save_async_artifacts(self, agent_name: str, job_id: str, file_paths: List[Path], extra: Optional[dict] = None) -> Path:
        job_dir = self.async_root / agent_name / job_id
        ensure_dir(job_dir)
        copied = []
        for src in file_paths:
            src = Path(src)
            if not src.exists():
                continue
            dst = job_dir / src.name
            shutil.copy2(src, dst)
            copied.append(str(dst.relative_to(self.base)))
        manifest = {
            "timestamp": now_iso(),
            "agent": agent_name,
            "job_id": job_id,
            "batch_id": self.batch_id,
            "files": copied,
            "extra": extra or {},
        }
        write_json(job_dir / "manifest.json", manifest)
        return job_dir

    def _theme_fallback(self, n: int) -> List[dict]:
        catalog = [
            {
                "tema_principal": "Mapa de intenção para franquias multiunidade",
                "keyword_primaria": "seo local para franquias",
                "keywords_secundarias": "cluster geografico|conteudo por unidade|visibilidade local|crescimento organico",
                "funil": "TOFU",
                "busca": "Alta",
                "titulo_anuncio": "SEO local para franquias em escala",
                "angulo_conteudo": "Guia Passo-a-Passo",
            },
            {
                "tema_principal": "Operação de pauta com IA e revisão editorial",
                "keyword_primaria": "pipeline editorial com ia",
                "keywords_secundarias": "qa editorial|governanca de conteudo|cadencia semanal|padrao de marca",
                "funil": "MOFU",
                "busca": "Média",
                "titulo_anuncio": "Pipeline editorial com IA sem perda de qualidade",
                "angulo_conteudo": "Educacional",
            },
            {
                "tema_principal": "Integração entre mídia paga e conteúdo orgânico",
                "keyword_primaria": "sinergia entre seo e meta ads",
                "keywords_secundarias": "otimizacao de cac|aprendizado de campanha|criativos orientados a dados|authority loop",
                "funil": "MOFU",
                "busca": "Alta",
                "titulo_anuncio": "SEO + Meta Ads com inteligência de dados",
                "angulo_conteudo": "Comparativo",
            },
            {
                "tema_principal": "Escala de produção para times enxutos",
                "keyword_primaria": "conteudo em escala com controle de qualidade",
                "keywords_secundarias": "playbook editorial|sprint de conteudo|priorizacao por impacto|eficiencia operacional",
                "funil": "BOFU",
                "busca": "Média",
                "titulo_anuncio": "Escalar conteúdo sem perder consistência",
                "angulo_conteudo": "Erros Comuns",
            },
            {
                "tema_principal": "Métricas de conteúdo para decisões de budget",
                "keyword_primaria": "indicadores de performance de conteudo",
                "keywords_secundarias": "ctr organico|roas assistido|pipeline comercial|receita incremental",
                "funil": "BOFU",
                "busca": "Baixa",
                "titulo_anuncio": "Quais métricas realmente importam em 2026",
                "angulo_conteudo": "Dado e Insight",
            },
            {
                "tema_principal": "BI editorial para operações B2B complexas",
                "keyword_primaria": "bi para marketing de conteudo b2b",
                "keywords_secundarias": "painel executivo|mql por cluster|pipeline previsivel|analise de coorte",
                "funil": "MOFU",
                "busca": "Média",
                "titulo_anuncio": "BI editorial para times B2B",
                "angulo_conteudo": "Tendência de Mercado",
            },
        ]
        items = []
        for i in range(n):
            base = dict(catalog[i % len(catalog)])
            base["notes"] = "fallback local"
            items.append(base)
        return items

    def _gemini_generate_with_retry(
        self,
        prompt: str,
        temperature: float,
        context: dict,
        attempts: int = 3,
        backoff_seconds: float = 1.5,
    ) -> str:
        last_err = None
        for i in range(1, attempts + 1):
            try:
                return self.gemini.generate_text(prompt, temperature=temperature, context=context)
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                retryable = ("http 503" in msg) or ("http 429" in msg) or ("network error" in msg) or ("timed out" in msg)
                if (not retryable) or i == attempts:
                    raise
                wait = backoff_seconds * i
                self.log(
                    "gemini",
                    "retry",
                    reason=f"retryable_error_attempt_{i}: {e}",
                    item_id=context.get("id", ""),
                    version=int(context.get("version", 0) or 0),
                )
                time.sleep(wait)
        raise RuntimeError(f"Gemini retry exhausted: {last_err}")

    def agent01_generate_themes(self) -> List[dict]:
        n = int(self.cfg.get("quantidade_temas", 5))
        if self.test_mode:
            data = self._theme_fallback(n)
            rows = []
            ts = now_iso()
            for d in data:
                rows.append(
                    {
                        "id": content_id(),
                        "timestamp": ts,
                        "tema_principal": d.get("tema_principal", "Tema sem nome"),
                        "keyword_primaria": d.get("keyword_primaria", "keyword principal"),
                        "keywords_secundarias": d.get("keywords_secundarias", ""),
                        "porte_empresa_alvo": self.cfg.get("porte_empresa_alvo", "Média Empresa"),
                        "modelo_negocio_alvo": self.cfg.get("modelo_negocio_alvo", "B2B"),
                        "vertical_alvo": self.cfg.get("vertical_alvo", "Geral"),
                        "produto_sowads_foco": self.cfg.get("produto_sowads_foco", "Ambos os pilares"),
                        "angulo_conteudo": d.get("angulo_conteudo", "Educacional"),
                        "url_interna": self.cfg.get("url_interna", ""),
                        "funil": d.get("funil", "TOFU"),
                        "busca": d.get("busca", "Média"),
                        "titulo_anuncio": d.get("titulo_anuncio", d.get("tema_principal", "")),
                        "notes": d.get("notes", ""),
                    }
                )
            p1 = self.base / "outputs/themes" / f"{self.batch_id}_themes.csv"
            p2 = self.batch_dir / "themes.csv"
            write_csv(p1, rows, THEME_COLUMNS)
            write_csv(p2, rows, THEME_COLUMNS)
            self.log("themes", "success", metrics={"count": len(rows), "mode": "test_fallback"})
            return rows

        prompt = f"""
Você é o Agent 01 (Theme Generator).
Responda SOMENTE um JSON array de {n} objetos.
Cada objeto deve conter:
- tema_principal
- keyword_primaria
- keywords_secundarias (separadas por |)
- funil (TOFU|MOFU|BOFU)
- busca (Alta|Média|Baixa)
- titulo_anuncio
- notes
- angulo_conteudo (Educacional|Comparativo|Guia Passo-a-Passo|Erros Comuns|Tendência de Mercado|Dado e Insight)

Contexto:
- nicho: {self.cfg.get('nicho','')}
- vertical: {self.cfg.get('vertical_alvo','Geral')}
- porte: {self.cfg.get('porte_empresa_alvo','Média Empresa')}
- modelo: {self.cfg.get('modelo_negocio_alvo','B2B')}
- produto foco: {self.cfg.get('produto_sowads_foco','Ambos os pilares')}
- restricoes: {self.cfg.get('restricoes','')}

Regras:
- não escreva artigo
- sem números de busca
- evite temas repetidos
""".strip()
        rows = []
        try:
            text = self._gemini_generate_with_retry(
                prompt=prompt,
                temperature=0.5,
                context={
                    "phase": "themes",
                    "agent": "agent_01_theme_generator",
                    "batch_id": self.batch_id,
                },
            )
            data = extract_json_from_text(text)
            if not isinstance(data, list):
                raise ValueError("Theme output is not list")
        except Exception as e:
            self.log("themes", "fail", reason=str(e))
            data = self._theme_fallback(n)

        ts = now_iso()
        for i in range(n):
            d = data[i] if i < len(data) and isinstance(data[i], dict) else self._theme_fallback(1)[0]
            row = {
                "id": content_id(),
                "timestamp": ts,
                "tema_principal": d.get("tema_principal", "Tema sem nome"),
                "keyword_primaria": d.get("keyword_primaria", "keyword principal"),
                "keywords_secundarias": d.get("keywords_secundarias", ""),
                "porte_empresa_alvo": self.cfg.get("porte_empresa_alvo", "Média Empresa"),
                "modelo_negocio_alvo": self.cfg.get("modelo_negocio_alvo", "B2B"),
                "vertical_alvo": self.cfg.get("vertical_alvo", "Geral"),
                "produto_sowads_foco": self.cfg.get("produto_sowads_foco", "Ambos os pilares"),
                "angulo_conteudo": d.get("angulo_conteudo", "Educacional"),
                "url_interna": self.cfg.get("url_interna", ""),
                "funil": d.get("funil", "TOFU"),
                "busca": d.get("busca", "Média"),
                "titulo_anuncio": d.get("titulo_anuncio", d.get("tema_principal", "")),
                "notes": d.get("notes", ""),
            }
            rows.append(row)

        p1 = self.base / "outputs/themes" / f"{self.batch_id}_themes.csv"
        p2 = self.batch_dir / "themes.csv"
        write_csv(p1, rows, THEME_COLUMNS)
        write_csv(p2, rows, THEME_COLUMNS)
        self.log("themes", "success", metrics={"count": len(rows)})
        return rows

    def _apply_user_template(self, theme: dict) -> str:
        repl = {
            "{{TEMA_PRINCIPAL}}": theme["tema_principal"],
            "{{KEYWORD_PRIMARIA}}": theme["keyword_primaria"],
            "{{KEYWORDS_SECUNDARIAS}}": theme["keywords_secundarias"],
            "{{PORTE_EMPRESA_ALVO}}": theme["porte_empresa_alvo"],
            "{{MODELO_NEGOCIO_ALVO}}": theme["modelo_negocio_alvo"],
            "{{VERTICAL_ALVO}}": theme["vertical_alvo"],
            "{{PRODUTO_SOWADS_FOCO}}": theme["produto_sowads_foco"],
            "{{ANGULO_CONTEUDO}}": theme["angulo_conteudo"],
            "{{URL_INTERNA}}": theme.get("url_interna", ""),
        }
        text = self.user_md
        for k, v in repl.items():
            text = text.replace(k, str(v))
        return text

    def _extract_blocks(self, out: str) -> Tuple[str, str, str]:
        meta, html, _ = split_content_package(out or "")
        mt = ""
        md = ""
        for line in meta.splitlines():
            if line.lower().startswith("meta title"):
                mt = line.split(":", 1)[-1].strip()
            elif line.lower().startswith("meta description"):
                md = line.split(":", 1)[-1].strip()
        if not mt:
            h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.I | re.S)
            if h1s:
                mt = strip_html(h1s[0])[:60].strip()
            if not mt:
                mt = (meta.splitlines() + [""])[0].strip()[:60]
        if not md:
            first_par = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.I | re.S)
            if first_par:
                md = strip_html(first_par[0])[:155].strip()
            if not md:
                md = " ".join(meta.splitlines()[1:]).strip()[:155]
        clean_meta = f"Meta Title: {mt}\nMeta Description: {md}"
        package = build_content_package(clean_meta, html, with_markers=True)
        return mt, md, package

    def _article_fallback(self, theme: dict, item_id: str, version: int, rewrite_guidance: str = "") -> dict:
        title = theme["tema_principal"].strip()
        keyword = theme["keyword_primaria"].strip()
        secondary = [k.strip() for k in theme.get("keywords_secundarias", "").split("|") if k.strip()]
        sec_a = secondary[0] if len(secondary) > 0 else "conteudo em escala"
        sec_b = secondary[1] if len(secondary) > 1 else "orquestracao editorial"
        sec_c = secondary[2] if len(secondary) > 2 else "performance organica"

        variant = int(hashlib.sha1(f"{item_id}-{version}-{keyword}".encode("utf-8")).hexdigest(), 16) % 3
        signal = item_id[-6:].lower()
        context_line = (
            f"Contexto de teste {signal}: operação {theme.get('vertical_alvo','Geral')} em "
            f"{theme.get('modelo_negocio_alvo','B2B')} para {theme.get('porte_empresa_alvo','Média Empresa')}."
        )

        headline = f"{title}: {keyword}"
        meta_title = slugify(f"{title} {keyword}").replace("-", " ")[:60].strip()
        if not meta_title:
            meta_title = (headline[:60]).strip()
        meta_desc = (
            f"{keyword} com foco em {sec_a}, {sec_b} e revisão humana. Guia prático para 2026."
        )[:155]

        if variant == 0:
            body = f"""
  <p>{keyword} se torna crítico quando a operação precisa escalar sem perder padrão editorial. {context_line}</p>
  <h2>Como {keyword} acelera decisões de mídia e SEO</h2>
  <p>A combinação de dados, IA e revisão humana reduz retrabalho e cria previsibilidade para times de crescimento.</p>
  <h2>Plano de execução de {keyword} em 90 dias</h2>
  <ol>
    <li>Mapear intenção por funil e cluster temático.</li>
    <li>Produzir pautas com foco em {sec_a} e {sec_b}.</li>
    <li>Publicar com checklist técnico e monitorar CTR, CAC e ROAS.</li>
  </ol>
  <h2>Checklist operacional</h2>
  <ul>
    <li>Padronizar briefing, tom e critérios de QA.</li>
    <li>Priorizar conteúdos com potencial de {sec_c}.</li>
    <li>Revisar peças com janela editorial semanal.</li>
  </ul>
"""
        elif variant == 1:
            body = f"""
  <p>{keyword} funciona quando produção e distribuição seguem o mesmo protocolo de qualidade. {context_line}</p>
  <h2>Framework prático de {keyword} para crescimento sustentável</h2>
  <p>Times que conectam pauta, criação e auditoria tendem a reduzir custo de aquisição e aumentar tráfego qualificado.</p>
  <h2>Prioridades de {keyword} para 2026</h2>
  <ul>
    <li>Intenção de busca e lacunas reais do mercado.</li>
    <li>Cadência editorial com foco em {sec_a}.</li>
    <li>Governança para {sec_b} e distribuição contínua.</li>
  </ul>
  <h2>Indicadores de validação</h2>
  <p>Monitorar conversão assistida, ganho de posição e impacto em pipeline comercial com leitura quinzenal.</p>
"""
        else:
            body = f"""
  <p>Para marcas orientadas a performance, {keyword} organiza a operação e elimina gargalos entre conteúdo e mídia. {context_line}</p>
  <h2>Onde {keyword} gera vantagem competitiva</h2>
  <p>Quando o processo inclui QA editorial, a operação ganha velocidade sem degradar consistência de marca.</p>
  <h2>Roteiro de implementação de {keyword}</h2>
  <ol>
    <li>Definir arquitetura de temas por objetivo de negócio.</li>
    <li>Executar sprint de produção com foco em {sec_a} e {sec_c}.</li>
    <li>Fechar ciclo com análise de ROI e ajustes de backlog.</li>
  </ol>
  <h2>Risco comum e correção</h2>
  <p>Publicar em volume sem critério técnico aumenta ruído. A correção é usar revisão humana e score mínimo antes de publicar.</p>
"""

        faq_q1 = f"Por que {keyword} é relevante para a operação atual?"
        faq_a1 = f"Porque conecta produção em escala com governança editorial e melhora previsibilidade de resultados."
        faq_q2 = f"Qual o papel da revisão humana em {keyword}?"
        faq_a2 = "Garantir contexto, precisão e aderência de marca antes da publicação."
        faq_q3 = "Quais métricas acompanhar no primeiro ciclo?"
        faq_a3 = "CTR, tráfego qualificado, CAC, ROAS e evolução de posicionamento orgânico."
        faq_q4 = "Quando atualizar os conteúdos publicados?"
        faq_a4 = "A cada ciclo de desempenho, com prioridade para páginas que perderam tração."
        faq_q5 = "Como evitar conteúdo repetitivo?"
        faq_a5 = "Usando clusters distintos, variação de ângulo e auditoria de similaridade por lote."

        html = f"""=== META INFORMATION ===
Meta Title: {meta_title}
Meta Description: {meta_desc}

=== HTML PACKAGE — WORDPRESS READY ===
<div class="sowads-article-body">
  <p><strong>{headline}</strong>. Este conteúdo segue o padrão Sowads: sem H1 no corpo e com foco em leitura escaneável.</p>
{body}
  <p>Em resumo, {keyword} só entrega consistência quando escala e qualidade caminham juntas, com IA e revisão humana.</p>
  <section class=\"sowads-cta\">
    <p><strong>Fale com a Sowads</strong> para estruturar uma operação previsível de conteúdo e mídia, com governança e revisão humana.</p>
  </section>
  <section class=\"faq-section\" itemscope itemtype=\"https://schema.org/FAQPage\">
    <h2>Perguntas frequentes</h2>
    <div itemscope itemprop=\"mainEntity\" itemtype=\"https://schema.org/Question\"><h3 itemprop=\"name\">{faq_q1}</h3><div itemscope itemprop=\"acceptedAnswer\" itemtype=\"https://schema.org/Answer\"><p itemprop=\"text\">{faq_a1}</p></div></div>
    <div itemscope itemprop=\"mainEntity\" itemtype=\"https://schema.org/Question\"><h3 itemprop=\"name\">{faq_q2}</h3><div itemscope itemprop=\"acceptedAnswer\" itemtype=\"https://schema.org/Answer\"><p itemprop=\"text\">{faq_a2}</p></div></div>
    <div itemscope itemprop=\"mainEntity\" itemtype=\"https://schema.org/Question\"><h3 itemprop=\"name\">{faq_q3}</h3><div itemscope itemprop=\"acceptedAnswer\" itemtype=\"https://schema.org/Answer\"><p itemprop=\"text\">{faq_a3}</p></div></div>
    <div itemscope itemprop=\"mainEntity\" itemtype=\"https://schema.org/Question\"><h3 itemprop=\"name\">{faq_q4}</h3><div itemscope itemprop=\"acceptedAnswer\" itemtype=\"https://schema.org/Answer\"><p itemprop=\"text\">{faq_a4}</p></div></div>
    <div itemscope itemprop=\"mainEntity\" itemtype=\"https://schema.org/Question\"><h3 itemprop=\"name\">{faq_q5}</h3><div itemscope itemprop=\"acceptedAnswer\" itemtype=\"https://schema.org/Answer\"><p itemprop=\"text\">{faq_a5}</p></div></div>
  </section>
  <script type=\"application/ld+json\">{{"@context":"https://schema.org","@type":"Article","headline":"{headline}","description":"{meta_desc}","author":{{"@type":"Organization","name":"Sowads"}},"publisher":{{"@type":"Organization","name":"Sowads"}},"datePublished":"2026-01-01T00:00:00Z","dateModified":"2026-01-01T00:00:00Z","mainEntityOfPage":{{"@type":"WebPage","@id":"https://resultsquad.com.br/"}}}}</script>
  <script type=\"application/ld+json\">{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{{"@type":"Question","name":"{faq_q1}","acceptedAnswer":{{"@type":"Answer","text":"{faq_a1}"}}}},{{"@type":"Question","name":"{faq_q2}","acceptedAnswer":{{"@type":"Answer","text":"{faq_a2}"}}}},{{"@type":"Question","name":"{faq_q3}","acceptedAnswer":{{"@type":"Answer","text":"{faq_a3}"}}}},{{"@type":"Question","name":"{faq_q4}","acceptedAnswer":{{"@type":"Answer","text":"{faq_a4}"}}}},{{"@type":"Question","name":"{faq_q5}","acceptedAnswer":{{"@type":"Answer","text":"{faq_a5}"}}}}]}}</script>
</div>
"""
        return self._build_article_record(theme, item_id, version, html, "PENDING_QA")

    def _extract_first_sentence(self, html: str) -> str:
        first_p = re.search(r"<p[^>]*>([\s\S]*?)</p>", html or "", flags=re.I)
        if not first_p:
            return ""
        text = strip_html(first_p.group(1)).strip()
        if not text:
            return ""
        m = re.split(r"(?<=[\.\!\?])\s+", text, maxsplit=1)
        return (m[0] if m else text)[:180].strip()

    def _extract_h2_signature(self, html: str, limit: int = 5) -> str:
        h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", html or "", flags=re.I | re.S)
        normalized = []
        for h in h2s:
            t = self._normalize_text(strip_html(h))
            if t:
                normalized.append(t)
        return " | ".join(normalized[:limit])

    def _collect_diversity_constraints(self, current: Dict[str, dict], target_id: str) -> dict:
        avoid_openings: List[str] = []
        avoid_h2: List[str] = []
        if not current:
            return {"avoid_openings": avoid_openings, "avoid_h2_signatures": avoid_h2}

        rows: List[Tuple[int, str, str]] = []
        for item_id, rec in current.items():
            if item_id == target_id:
                continue
            _, html = self._parse_package(rec.get("content_package", ""))
            first = self._extract_first_sentence(html)
            h2sig = self._extract_h2_signature(html)
            try:
                version = int(rec.get("version", 1))
            except Exception:
                version = 1
            rows.append((version, first, h2sig))

        rows.sort(key=lambda x: x[0], reverse=True)
        for _, first, h2sig in rows[:6]:
            if first:
                avoid_openings.append(first)
            if h2sig:
                avoid_h2.append(h2sig)

        return {
            "avoid_openings": avoid_openings[:4],
            "avoid_h2_signatures": avoid_h2[:4],
        }

    def _pick_narrative_frame(self, item_id: str, version: int) -> Tuple[str, str]:
        idx = int(hashlib.sha1(f"{self.batch_id}:{item_id}:{version}:frame".encode("utf-8")).hexdigest(), 16) % len(
            NARRATIVE_FRAMES
        )
        return NARRATIVE_FRAMES[idx]

    def _pick_visual_mix(self, item_id: str, version: int) -> Tuple[str, List[str]]:
        idx = int(hashlib.sha1(f"{self.batch_id}:{item_id}:{version}:visual".encode("utf-8")).hexdigest(), 16) % len(
            VISUAL_MIXES
        )
        return VISUAL_MIXES[idx]

    def _refine_article_with_critic(
        self,
        draft_output: str,
        theme: dict,
        item_id: str,
        version: int,
        frame_name: str,
        visual_pack_name: str,
        visual_pack_items: List[str],
        diversity_constraints: Optional[dict] = None,
    ) -> str:
        diversity_constraints = diversity_constraints or {}
        avoid_openings = diversity_constraints.get("avoid_openings", [])
        avoid_h2 = diversity_constraints.get("avoid_h2_signatures", [])

        critic_prompt = (
            "Você é um editor crítico de conteúdo SEO/GEO da Sowads.\n"
            "Reescreva o artigo abaixo mantendo o mesmo tema e respeitando OBRIGATORIAMENTE:\n"
            "- Não começar o primeiro parágrafo com 'Em 2026' nem variações equivalentes.\n"
            "- Evitar estrutura rígida repetida; variar abertura, ordem de seções e ritmo.\n"
            "- Garantir 2 a 3 elementos visuais naturais no miolo (após 2º ao 4º parágrafo).\n"
            "- Tabelas simples: células curtas (até 10 palavras), sem reticências, sem texto truncado.\n"
            "- Parágrafos curtos e fluídos (aprox. 30-65 palavras).\n"
            "- Manter 2 blocos obrigatórios do pacote: META INFORMATION e HTML PACKAGE.\n"
            "- Sem H1 no corpo. Sem links externos. FAQ com respostas completas.\n\n"
            f"Frame narrativo alvo: {frame_name}\n"
            f"Pacote visual alvo: {visual_pack_name} -> {', '.join(visual_pack_items)}\n"
            + (f"Aberturas proibidas deste lote: {' || '.join(avoid_openings)}\n" if avoid_openings else "")
            + (f"Assinaturas de H2 proibidas deste lote: {' || '.join(avoid_h2)}\n" if avoid_h2 else "")
            + "\n[ARTIGO DRAFT PARA REFINAR]\n"
            + (draft_output or "")
        )
        try:
            refined = self._gemini_generate_with_retry(
                prompt=critic_prompt,
                temperature=0.45,
                context={
                    "phase": "articles_refine",
                    "agent": "agent_02_article_critic_refiner",
                    "batch_id": self.batch_id,
                    "id": item_id,
                    "version": version,
                },
            )
            if "=== META INFORMATION ===" in refined and "=== HTML PACKAGE — WORDPRESS READY ===" in refined:
                return refined
        except Exception as e:
            self.log("articles", "warn", reason=f"critic_refine_failed: {e}", item_id=item_id, version=version)
        return draft_output

    def _build_article_record(self, theme: dict, item_id: str, version: int, raw_output: str, status: str) -> dict:
        meta_title, meta_desc, package = self._extract_blocks(raw_output)
        slug_base = meta_title or theme["tema_principal"]
        return {
            "batch_id": self.batch_id,
            "id": item_id,
            "version": version,
            "tema_principal": theme["tema_principal"],
            "keyword_primaria": theme["keyword_primaria"],
            "keywords_secundarias": theme["keywords_secundarias"],
            "porte_empresa_alvo": theme["porte_empresa_alvo"],
            "modelo_negocio_alvo": theme["modelo_negocio_alvo"],
            "vertical_alvo": theme["vertical_alvo"],
            "produto_sowads_foco": theme["produto_sowads_foco"],
            "angulo_conteudo": theme["angulo_conteudo"],
            "url_interna": theme.get("url_interna", ""),
            "slug": slugify(slug_base)[:80],
            "meta_title": meta_title,
            "meta_description": meta_desc,
            "content_package": package,
            "status": status,
        }

    def _generate_article(
        self,
        theme: dict,
        item_id: str,
        version: int,
        rewrite_guidance: str = "",
        current_articles: Optional[Dict[str, dict]] = None,
    ) -> dict:
        if self.test_mode:
            rec = self._article_fallback(theme, item_id, version, rewrite_guidance)
            self.log("articles", "success", item_id=item_id, version=version, metrics={"mode": "test_fallback"})
            return rec

        profile_idx = int(
            hashlib.sha1(f"{self.batch_id}-{item_id}-{version}".encode("utf-8")).hexdigest(),
            16,
        ) % len(STRUCTURE_PROFILES)
        profile_name, profile_rule = STRUCTURE_PROFILES[profile_idx]
        narrative_frame_name, narrative_frame_rule = self._pick_narrative_frame(item_id, version)
        visual_pack_name, visual_pack_items = self._pick_visual_mix(item_id, version)
        diversity_constraints = self._collect_diversity_constraints(current_articles or {}, item_id)
        avoid_openings = diversity_constraints.get("avoid_openings", [])
        avoid_h2 = diversity_constraints.get("avoid_h2_signatures", [])

        wrapper = (
            f"ID do Artigo: {item_id}\n"
            f"Batch ID: {self.batch_id}\n"
            f"Version: {version}\n"
            f"Perfil estrutural selecionado: {profile_name}\n"
            f"Frame narrativo selecionado: {narrative_frame_name} ({narrative_frame_rule})\n"
            f"Pacote visual selecionado: {visual_pack_name} ({', '.join(visual_pack_items)})\n"
            + (f"Rewrite guidance: {rewrite_guidance}\n" if rewrite_guidance else "")
            + (f"Aberturas proibidas neste lote: {' || '.join(avoid_openings)}\n" if avoid_openings else "")
            + (f"Assinaturas H2 a evitar neste lote: {' || '.join(avoid_h2)}\n" if avoid_h2 else "")
            + "\n"
            + self._apply_user_template(theme)
        )

        prompt = (
            "[SYSTEM - OBEDECER INTEGRALMENTE]\n"
            + self.system_md
            + "\n\n[CONSTRAINTS OPERACIONAIS DO LOTE]\n"
            + f"- Word count obrigatório entre {self.min_article_words} e {self.max_article_words}.\n"
            + "- Não inserir <h1> dentro do HTML package; o H1 é o título nativo do WordPress.\n"
            + "- O conteúdo no HTML package deve iniciar com introdução e depois H2/H3 (sem H1 no corpo).\n"
            + f"- Perfil estrutural obrigatório deste artigo: {profile_name} ({profile_rule}).\n"
            + "- Estrutura é princípio, não molde fixo: adaptar seções ao tema sem copiar blocos/títulos padronizados.\n"
            + "- Não repetir blocos fixos, nomes padronizados ou ordem idêntica de seções entre temas diferentes.\n"
            + "- Proibido usar headings literais: 'Painel tático', 'Resumo executivo em bullet points', 'Checklist de execução (30 dias)', 'Prioridade 1', 'Prioridade 2', 'Prioridade 3'.\n"
            + "- PROIBIDO começar o primeiro parágrafo com: 'Em 2026', 'Atualmente', 'Nos dias de hoje', 'No cenário atual' ou equivalentes.\n"
            + "- Abertura obrigatória em 2 parágrafos curtos: contexto de decisão + impacto prático no negócio.\n"
            + "- Introdução deve trazer gancho forte e específico; evitar frases vagas e clichês de mercado.\n"
            + "- Usar 2 a 3 recursos visuais por artigo, escolhidos conforme o assunto: lista numerada, bullets, mini-checklist, tabela, blockquote, frases-âncora em negrito.\n"
            + "- Não usar todos os recursos no mesmo artigo; escolha apenas os que aumentam clareza do tema.\n"
            + "- O primeiro recurso visual estrutural (lista/tabela/blockquote/checklist) deve entrar após o 2º, 3º ou 4º parágrafo.\n"
            + "- Evitar bloco visual de apêndice no fim do artigo.\n"
            + "- Tabela com células curtas e objetivas (até 10 palavras por célula; sem reticências, sem texto truncado, sem '...').\n"
            + "- Parágrafos curtos: 30-65 palavras por parágrafo (máximo absoluto 85 palavras).\n"
            + "- Fluidez, clareza, elegância executiva e densidade sem prolixidade são prioritárias.\n"
            + "- Linguagem executiva clara: técnica sem soar acadêmica, pesada ou genérica.\n"
            + "- Incluir seção CTA obrigatória: <section class=\"sowads-cta\">...</section>.\n"
            + "- FAQ obrigatória com 5 a 8 perguntas e respostas completas (2 a 4 frases cada resposta).\n"
            + "- FAQ HTML deve usar itemprop (Question/Answer) e também JSON-LD FAQPage coerente.\n"
            + "- Article JSON-LD obrigatório e completo (headline, description, author, publisher, datePublished, dateModified, mainEntityOfPage).\n"
            + "- Incluir 1 a 3 referências verificáveis citadas em texto simples com fonte + ano (sem hyperlink externo).\n"
            + "- Cada H2 deve começar com um parágrafo-resumo autossuficiente (40-60 palavras) para GEO.\n"
            + "- Incluir mini diagnóstico executivo no formato: sintoma -> causa -> impacto.\n"
            + "- Incluir pelo menos 1 cenário operacional com escala numérica realista (ex.: unidades, páginas, budget, catálogo), sem prometer resultados.\n"
            + "- Incluir obrigatoriamente 1 bloco com subtítulo explícito de exemplo aplicado ('Exemplo prático' ou 'Cenário aplicado').\n"
            + "- Incluir seção de erros críticos a evitar com 4-6 bullet points específicos.\n"
            + "- Aplicar negrito com inteligência: termos técnicos na primeira menção, frases de decisão estratégica e regras operacionais; evitar excesso de negrito.\n"
            + "- Não inserir CSS inline, comentários HTML, placeholders ou texto técnico fora do conteúdo final.\n"
            + "\n\n[FORMATO OBRIGATORIO DE SAIDA]\n"
            + "Retorne EXATAMENTE neste formato:\n"
            + "=== META INFORMATION ===\n"
            + "Meta Title: ...\nMeta Description: ...\n\n"
            + "=== HTML PACKAGE — WORDPRESS READY ===\n"
            + "<div class=\"sowads-article-body\">...</div>\n"
            + "Sem texto fora desses blocos. Sem links externos.\n\n"
            + "[USER]\n"
            + wrapper
        )

        try:
            raw = self._gemini_generate_with_retry(
                prompt=prompt,
                temperature=0.3 if self.test_mode else 0.35,
                context={
                    "phase": "articles",
                    "agent": "agent_02_article_generator",
                    "batch_id": self.batch_id,
                    "id": item_id,
                    "version": version,
                },
            )
            raw = self._refine_article_with_critic(
                draft_output=raw,
                theme=theme,
                item_id=item_id,
                version=version,
                frame_name=narrative_frame_name,
                visual_pack_name=visual_pack_name,
                visual_pack_items=visual_pack_items,
                diversity_constraints=diversity_constraints,
            )
            rec = self._build_article_record(theme, item_id, version, raw, "PENDING_QA")
            if not rec["content_package"]:
                raise ValueError("article output missing required blocks")
            return rec
        except Exception as e:
            self.log("articles", "fail", reason=str(e), item_id=item_id, version=version)
            return self._article_fallback(theme, item_id, version, rewrite_guidance)

    def agent02_generate_articles(self, themes: List[dict], current: Dict[str, dict] = None, rewrite_map: Dict[str, str] = None):
        current = current or {}
        rewrite_map = rewrite_map or {}
        out = dict(current)

        for t in themes:
            item_id = t["id"]
            if item_id in rewrite_map:
                prev = out[item_id]
                version = int(prev["version"]) + 1
                rec = self._generate_article(
                    t,
                    item_id,
                    version,
                    rewrite_map[item_id],
                    current_articles=out,
                )
                out[item_id] = rec
                self.log("articles", "requeued", reason="rewrite_only", item_id=item_id, version=version)
            elif item_id not in out:
                rec = self._generate_article(t, item_id, 1, current_articles=out)
                out[item_id] = rec
                self.log("articles", "success", item_id=item_id, version=1)
        return out

    def _parse_package(self, package: str) -> Tuple[str, str]:
        meta, html, _ = split_content_package(package or "")
        return meta, html

    def _keyword_hits(self, html: str, kw: str) -> Dict[str, bool]:
        text = strip_html(html).lower()
        kwl = kw.lower()
        h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", html, flags=re.I | re.S)
        first_par = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.I | re.S)
        conc = " ".join(first_par[-2:]).lower() if first_par else ""
        return {
            "in_first_par": kwl in strip_html(first_par[0]).lower() if first_par else False,
            "in_h2_count_2": sum(kwl in strip_html(x).lower() for x in h2s) >= 2,
            "in_conclusion": kwl in conc,
            "in_text": kwl in text,
        }

    def _normalize_text(self, text: str) -> str:
        mapping = str.maketrans(
            "áàâãäéèêëíìîïóòôõöúùûüçñ",
            "aaaaaeeeeiiiiooooouuuucn",
        )
        text = (text or "").lower().translate(mapping)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _count_words(self, text: str) -> int:
        norm = self._normalize_text(text)
        if not norm:
            return 0
        return len(norm.split())

    def _phrase_occurrences(self, text: str, phrase: str) -> int:
        t = self._normalize_text(text)
        p = self._normalize_text(phrase)
        if not t or not p:
            return 0
        t_tokens = t.split()
        p_tokens = p.split()
        if not p_tokens or len(p_tokens) > len(t_tokens):
            return 0
        size = len(p_tokens)
        total = 0
        for i in range(0, len(t_tokens) - size + 1):
            if t_tokens[i:i+size] == p_tokens:
                total += 1
        return total

    def _keyword_density_pct(self, text: str, keyword: str) -> float:
        words = self._count_words(text)
        if words <= 0:
            return 0.0
        kw_tokens = self._normalize_text(keyword).split()
        if not kw_tokens:
            return 0.0
        occ = self._phrase_occurrences(text, keyword)
        covered_tokens = occ * len(kw_tokens)
        return round((covered_tokens / words) * 100.0, 4)

    def _token_jaccard(self, a: str, b: str) -> float:
        sa = set(self._normalize_text(a).split())
        sb = set(self._normalize_text(b).split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / max(1, len(sa | sb))

    def _has_repetitive_tail(self, text: str) -> bool:
        tokens = self._normalize_text(text).split()
        if len(tokens) < 80:
            return False
        tail = tokens[-180:]
        for n in (12, 10, 8):
            if len(tail) < n * 2:
                continue
            seen = {}
            for i in range(0, len(tail) - n + 1):
                ng = tuple(tail[i : i + n])
                seen[ng] = seen.get(ng, 0) + 1
                if seen[ng] >= 2:
                    return True
        return False

    def agent03_audit(self, articles: Dict[str, dict]) -> dict:
        items = []
        signature_by_item: Dict[str, str] = {}
        signature_counts: Counter = Counter()

        # Detect repeated structural fingerprints inside the same run.
        for aid, article in articles.items():
            _, html_tmp = self._parse_package(article.get("content_package", ""))
            h2_tmp = re.findall(r"<h2[^>]*>(.*?)</h2>", html_tmp, flags=re.I | re.S)
            h2_norm = [
                self._normalize_text(strip_html(h)).strip()
                for h in h2_tmp
                if self._normalize_text(strip_html(h)).strip()
            ]
            signature = "|".join(h2_norm[:6])
            if signature and len(h2_norm) >= 3:
                signature_by_item[aid] = signature
                signature_counts[signature] += 1

        for item_id, a in articles.items():
            reason_codes = []
            issues = []
            score = 100

            cp = a.get("content_package", "")
            has_m1 = "=== META INFORMATION ===" in cp
            has_m2 = "=== HTML PACKAGE — WORDPRESS READY ===" in cp
            if not (has_m1 and has_m2):
                reason_codes.append("missing_blocks")
                issues.append("Pacote sem 2 blocos obrigatórios.")
                score -= 40

            meta, html = self._parse_package(cp)
            plain_text = strip_html(html)
            word_count = self._count_words(plain_text)
            kw_density = self._keyword_density_pct(plain_text, a.get("keyword_primaria", ""))
            table_count = len(re.findall(r"<table[\s>]", html, flags=re.I))
            ul_count = len(re.findall(r"<ul[\s>]", html, flags=re.I))
            ol_count = len(re.findall(r"<ol[\s>]", html, flags=re.I))
            blockquote_count = len(re.findall(r"<blockquote[\s>]", html, flags=re.I))
            list_count = ul_count + ol_count
            html_len = max(1, len(html))
            table_pos = html.lower().find("<table")
            ul_pos = html.lower().find("<ul")
            ol_pos = html.lower().find("<ol")
            blockquote_pos = html.lower().find("<blockquote")
            list_positions = [p for p in (ul_pos, ol_pos) if p >= 0]
            first_list_pos = min(list_positions) if list_positions else -1
            faq_pos = html.lower().find("faq-section")
            checklist_match = re.search(r"<h[2-4][^>]*>\s*[^<]{0,60}checklist[^<]{0,60}</h[2-4]>", html, flags=re.I)
            checklist_pos = checklist_match.start() if checklist_match else -1
            checklist_li_count = len(re.findall(r"<li[^>]*>\s*(?:✅|☑️|✔️|□|\[[ xX]\])", html, flags=re.I))

            strong_snippets = re.findall(r"<strong[^>]*>([\s\S]*?)</strong>", html, flags=re.I)
            strong_count = len(strong_snippets)
            strong_words = sum(self._count_words(strip_html(x)) for x in strong_snippets)
            bold_anchor_count = 0
            for snippet in strong_snippets:
                w = self._count_words(strip_html(snippet))
                if 2 <= w <= 12:
                    bold_anchor_count += 1

            visual_devices = {
                "numbered_list": ol_count > 0,
                "bullets": ul_count > 0,
                "mini_checklist": bool(checklist_match) or checklist_li_count >= 2,
                "table": table_count > 0,
                "blockquote": blockquote_count > 0,
                "bold_anchor": bold_anchor_count >= 2,
            }
            visual_device_count = sum(1 for used in visual_devices.values() if used)

            if len(a.get("meta_title", "")) > 60:
                reason_codes.append("meta_title_too_long")
                issues.append("Meta Title > 60.")
                score -= 8

            if not a.get("meta_description", "").strip():
                reason_codes.append("meta_description_missing")
                issues.append("Meta Description ausente.")
                score -= 10
            if len(a.get("meta_description", "")) > 155:
                reason_codes.append("meta_description_too_long")
                issues.append("Meta Description > 155.")
                score -= 8

            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", a.get("slug", "")):
                reason_codes.append("invalid_slug")
                issues.append("Slug inválido.")
                score -= 12

            if a.get("tema_principal", "").strip() and a.get("meta_title", "").strip():
                title_sim = self._token_jaccard(a.get("tema_principal", ""), a.get("meta_title", ""))
                if title_sim >= 0.9:
                    issues.append("Título do post e Meta Title muito parecidos; variar promessa para evitar duplicação.")
                    score -= 8

            if re.search(r"<a[^>]+href=[\"'](?:https?://|www\.)", html, flags=re.I):
                reason_codes.append("external_link")
                issues.append("Link externo detectado.")
                score -= 18

            if word_count < self.min_article_words:
                reason_codes.append("word_count_low")
                issues.append(f"Word count abaixo do mínimo: {word_count} < {self.min_article_words}.")
                score -= 18
            elif word_count > self.max_article_words:
                reason_codes.append("word_count_high")
                issues.append(f"Word count acima do máximo: {word_count} > {self.max_article_words}.")
                score -= 18

            if kw_density < self.keyword_density_min:
                reason_codes.append("keyword_density_low")
                issues.append(
                    f"Densidade da keyword primária baixa: {kw_density:.2f}% < {self.keyword_density_min:.2f}%."
                )
                score -= 12
            elif kw_density > self.keyword_density_max:
                reason_codes.append("keyword_density_high")
                issues.append(
                    f"Densidade da keyword primária alta: {kw_density:.2f}% > {self.keyword_density_max:.2f}%."
                )
                score -= 12

            h1_count = len(re.findall(r"<h1[\s>].*?</h1>", html, flags=re.I | re.S))
            if h1_count > 0:
                reason_codes.append("body_h1_present")
                issues.append("H1 no corpo do artigo detectado; manter H1 apenas no título nativo do WordPress.")
                score -= 12

            if visual_device_count < 2:
                reason_codes.append("low_visual_structure")
                issues.append(
                    "Estrutura visual pobre: usar 2-3 recursos entre lista numerada, bullets, mini-checklist, tabela, blockquote e frases-âncora em negrito."
                )
                score -= 10
            elif visual_device_count > 3:
                reason_codes.append("visual_overload")
                issues.append("Excesso de elementos visuais: limitar para 2-3 recursos por artigo.")
                score -= 8

            structural_positions = [p for p in (table_pos, first_list_pos, blockquote_pos, checklist_pos) if p >= 0]
            if structural_positions:
                earliest_visual = min(structural_positions)
                p_positions = [m.start() for m in re.finditer(r"<p[\s>]", html, flags=re.I)]
                p2_pos = p_positions[1] if len(p_positions) >= 2 else -1
                p4_pos = p_positions[3] if len(p_positions) >= 4 else -1
                late_by_position = earliest_visual >= 0 and (earliest_visual / html_len) > 0.5
                late_by_paragraph = p4_pos >= 0 and earliest_visual > p4_pos
                late_after_faq = faq_pos >= 0 and earliest_visual >= faq_pos
                if late_by_position or late_by_paragraph or late_after_faq:
                    reason_codes.append("late_visual_structure")
                    issues.append(
                        "Elemento visual estrutural inserido tarde; posicionar após o 2º, 3º ou 4º parágrafo e antes da metade do artigo."
                    )
                    score -= 12
                elif p2_pos >= 0 and earliest_visual >= 0 and earliest_visual < p2_pos:
                    issues.append("Elemento visual estrutural muito cedo; reposicionar após o 2º parágrafo para fluidez.")
                    score -= 3

            if table_count > 0:
                table_block = ""
                table_match = re.search(r"<table[\s\S]*?</table>", html, flags=re.I)
                if table_match:
                    table_block = table_match.group(0)
                has_grid_style = bool(re.search(r"#d1d5db|#b7b7b7|border", table_block, flags=re.I))
                if not has_grid_style:
                    issues.append("Tabela sem estilo de grade legível (linhas/bordas cinza visíveis).")
                    score -= 4
                verbose_cells = 0
                ellipsis_cells = 0
                for cell in re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", table_block, flags=re.I):
                    cell_raw = strip_html(cell)
                    cell_words = self._count_words(cell_raw)
                    if cell_words > 10:
                        verbose_cells += 1
                    if "..." in cell_raw:
                        ellipsis_cells += 1
                if verbose_cells > 0:
                    reason_codes.append("table_verbose")
                    issues.append(
                        f"Tabela com células verbosas ({verbose_cells}); usar texto curto e objetivo nas colunas."
                    )
                    score -= min(8, verbose_cells * 2)
                if ellipsis_cells > 0:
                    reason_codes.append("table_ellipsis")
                    issues.append("Tabela contém reticências ('...'); usar células completas e curtas, sem truncamento.")
                    score -= min(8, ellipsis_cells * 2)

            # Paragraph readability guardrail (avoid giant walls of text).
            long_paragraphs = 0
            for p in re.findall(r"<p[^>]*>([\s\S]*?)</p>", html, flags=re.I):
                ptxt = strip_html(p)
                # Skip script payloads accidentally captured in malformed content.
                if not ptxt or "@context" in ptxt or "@type" in ptxt:
                    continue
                if self._count_words(ptxt) > 70:
                    long_paragraphs += 1
            if long_paragraphs > 0:
                reason_codes.append("long_paragraphs")
                issues.append(f"Parágrafos longos detectados ({long_paragraphs}); quebrar em blocos menores.")
                score -= min(16, long_paragraphs * 4)

            # Require practical example/case block to reduce generic IA pattern.
            example_markers = [
                r"\bexemplo pr[aá]tico\b",
                r"\bcen[aá]rio aplicado\b",
                r"\bmini-?caso\b",
                r"\bcaso real\b",
                r"\bna pr[aá]tica\b",
            ]
            if not any(re.search(marker, html, flags=re.I) for marker in example_markers):
                reason_codes.append("examples_missing")
                issues.append("Falta exemplo prático/mini-caso operacional; adicionar bloco aplicado ao contexto do tema.")
                score -= 12

            first_chunk = strip_html(html[:900]).lower()
            if "?" not in first_chunk and not re.search(r"\b\d{2,4}\b", first_chunk):
                issues.append("Introdução fraca: incluir gancho de decisão (pergunta ou contexto numérico concreto).")
                score -= 5

            if word_count > 0:
                bold_ratio = strong_words / word_count
            else:
                bold_ratio = 0.0
            if strong_count > max(14, word_count // 75) or bold_ratio > 0.09:
                reason_codes.append("bold_overuse")
                issues.append("Excesso de negrito no corpo; destacar apenas termos técnicos, decisões estratégicas e regras operacionais.")
                score -= 8

            faq_ok = ("faq" in html.lower() and "FAQPage" in html)
            if not faq_ok:
                reason_codes.append("faq_missing")
                issues.append("FAQ HTML/JSON-LD ausente.")
                score -= 10
            else:
                faq_semantic_ok = bool(
                    re.search(r"<section[^>]*faq-section[^>]*itemscope[^>]*FAQPage", html, flags=re.I)
                    and re.search(r"itemprop=[\"']mainEntity[\"']", html, flags=re.I)
                    and re.search(r"itemprop=[\"']acceptedAnswer[\"']", html, flags=re.I)
                )
                if not faq_semantic_ok:
                    reason_codes.append("faq_html_semantic_missing")
                    issues.append("FAQ HTML sem marcação semântica completa (FAQPage/Question/Answer).")
                    score -= 10

                faq_pairs = len(
                    re.findall(
                        r"<h3[^>]*>[\s\S]*?</h3>\s*<p[^>]*>[\s\S]*?</p>",
                        html,
                        flags=re.I,
                    )
                ) + len(re.findall(r"itemprop=[\"']acceptedAnswer[\"']", html, flags=re.I))
                if faq_pairs < 5:
                    reason_codes.append("faq_answers_missing")
                    issues.append("FAQ com perguntas sem respostas suficientes (mínimo 5 pares Q/A).")
                    score -= 12

            if "\"@type\":\"Article\"" not in html and '"@type": "Article"' not in html:
                reason_codes.append("article_schema_missing")
                issues.append("Article JSON-LD ausente.")
                score -= 10
            else:
                article_jsonld_ok = all(
                    token in html
                    for token in (
                        '"@type":"Article"',
                        "headline",
                        "description",
                        "datePublished",
                        "dateModified",
                        "author",
                        "publisher",
                        "mainEntityOfPage",
                    )
                ) or all(
                    token in html
                    for token in (
                        '"@type": "Article"',
                        "headline",
                        "description",
                        "datePublished",
                        "dateModified",
                        "author",
                        "publisher",
                        "mainEntityOfPage",
                    )
                )
                if not article_jsonld_ok:
                    reason_codes.append("article_schema_incomplete")
                    issues.append("Article JSON-LD incompleto (faltam campos mandatórios).")
                    score -= 10

            has_steps = bool(re.search(r"<ol[\s>]|passo a passo|\bpasso\b", html, flags=re.I))
            has_howto = "HowTo" in html
            if has_howto and not has_steps:
                reason_codes.append("howto_without_steps")
                issues.append("HowTo schema sem passos reais.")
                score -= 8

            if not re.search(r"<section[^>]*class=[\"'][^\"']*sowads-cta[^\"']*[\"']", html, flags=re.I):
                reason_codes.append("cta_missing")
                issues.append("Seção CTA obrigatória ausente (<section class=\"sowads-cta\">).")
                score -= 8

            # GEO: H2 block must open with a self-sufficient summary paragraph.
            weak_h2_blocks = 0
            h2_iter = list(re.finditer(r"<h2[^>]*>[\s\S]*?</h2>", html, flags=re.I))
            for idx, m in enumerate(h2_iter):
                h2_label = strip_html(m.group(0)).lower()
                if "perguntas frequentes" in h2_label:
                    continue
                start = m.end()
                end = h2_iter[idx + 1].start() if idx + 1 < len(h2_iter) else len(html)
                section_chunk = html[start:end]
                first_p = re.search(r"<p[^>]*>([\s\S]*?)</p>", section_chunk, flags=re.I)
                if not first_p:
                    weak_h2_blocks += 1
                    continue
                p_words = self._count_words(strip_html(first_p.group(1)))
                if p_words < 35 or p_words > 80:
                    weak_h2_blocks += 1
            if weak_h2_blocks > 0:
                reason_codes.append("geo_block_weak")
                issues.append(
                    f"{weak_h2_blocks} blocos H2 sem resumo autossuficiente (35-80 palavras no 1º parágrafo)."
                )
                score -= min(12, weak_h2_blocks * 2)

            source_pattern = re.compile(
                r"(google search central|google|ahrefs|semrush|bain|gartner|statista|search console|search engine journal)[^\\n\\r]{0,45}(2024|2025|2026)",
                flags=re.I,
            )
            source_pattern_rev = re.compile(
                r"(2024|2025|2026)[^\\n\\r]{0,45}(google search central|google|ahrefs|semrush|bain|gartner|statista|search console|search engine journal)",
                flags=re.I,
            )
            if not (source_pattern.search(html) or source_pattern_rev.search(html)):
                reason_codes.append("sources_missing")
                issues.append("Faltam referências verificáveis no texto (fonte + ano).")
                score -= 8

            experience_pattern = re.compile(
                r"(\d{2,4}\s*(paginas|página|unidades|providers|jogos)|r\\$\\s*\\d|budget\\s*mensal|catalogo\\s*com\\s*\\d)",
                flags=re.I,
            )
            if not experience_pattern.search(strip_html(html)):
                issues.append("Adicionar contexto operacional real (Experience) com escala numérica do cenário.")
                score -= 4

            opening_text = strip_html(html[:600]).lower()
            if any(g in opening_text for g in GENERIC_OPENINGS):
                reason_codes.append("generic_opening")
                issues.append("Abertura genérica proibida.")
                score -= 10
            first_par = re.search(r"<p[^>]*>([\s\S]*?)</p>", html, flags=re.I)
            first_par_norm = self._normalize_text(strip_html(first_par.group(1))) if first_par else ""
            if any(first_par_norm.startswith(x) for x in BANNED_OPENING_STARTS):
                reason_codes.append("hard_opening_banned")
                issues.append("Primeiro parágrafo inicia com padrão proibido ('Em 2026'/'Atualmente'/similares).")
                score -= 16

            temporal_text = strip_html(html).lower()
            # Allow source-year citations (e.g., "Bain, 2025"), but block contextual present-time framing in 2024/2025.
            if re.search(r"\b(hoje|atualmente|neste ano|em)\s+20(24|25)\b", temporal_text):
                reason_codes.append("temporal_incoherence")
                issues.append("Ano incoerente com referência 2026.")
                score -= 12

            if "```" in html or re.search(r"={8,}", html):
                reason_codes.append("malformed_tail")
                issues.append("Artefatos de saída detectados (``` ou separadores ====) no HTML.")
                score -= 20

            if self._has_repetitive_tail(plain_text):
                reason_codes.append("repetitive_tail")
                issues.append("Trecho final com repetição excessiva de frases/padrões.")
                score -= 18

            normalized_plain = self._normalize_text(plain_text)
            fixed_block_markers = [
                "painel tatico",
                "resumo executivo em bullet points",
                "checklist de execucao 30 dias",
                "frente objetivo pratico indicador principal ritmo de revisao",
            ]
            if any(marker in normalized_plain for marker in fixed_block_markers):
                reason_codes.append("fixed_blocks_detected")
                issues.append("Bloco fixo/padronizado detectado; remover template rígido e adaptar a estrutura ao tema.")
                score -= 14

            sig = signature_by_item.get(item_id, "")
            if sig and signature_counts.get(sig, 0) > 1:
                reason_codes.append("repeated_structure_pattern")
                issues.append("Padrão estrutural de H2 repetido neste lote; variar a arquitetura do artigo para o tema.")
                score -= 12

            # heuristic for numbers/percent without Fonte/ano nearby
            for m in re.finditer(r"\b\d{1,3}%\b", html):
                window = html[max(0, m.start() - 120): m.end() + 120].lower()
                if "fonte" not in window and "202" not in window:
                    reason_codes.append("stat_without_source")
                    issues.append("Percentual sem fonte próxima.")
                    score -= 5
                    break

            hits = self._keyword_hits(html, a["keyword_primaria"])
            if not hits["in_first_par"]:
                score -= 6
                issues.append("Keyword primária fora do 1o parágrafo.")
            if not hits["in_h2_count_2"]:
                score -= 5
                issues.append("Keyword primária em menos de 2 H2.")
            if not hits["in_conclusion"]:
                score -= 3

            if not re.search(r"\bROAS\b|\bCTR\b|\bCAC\b|\bSEO\b", html):
                score -= 3
            if not re.search(r"R\$|franquia|budget|empresa", html, flags=re.I):
                score -= 3

            score = max(0, min(100, score))
            flag = score < self.threshold or bool(CRITICAL_REASON_CODES.intersection(reason_codes))

            guidance = ""
            if flag:
                guidance = (
                    "Reescrever apenas os pontos reprovados: "
                    + "; ".join(sorted(set(issues))[:8])
                    + ". Mantenha 2 blocos obrigatórios e sem links externos."
                )

            items.append(
                {
                    "id": item_id,
                    "version": int(a["version"]),
                    "seo_geo_score": score,
                    "metrics": {
                        "word_count": word_count,
                        "keyword_density_pct": round(kw_density, 4),
                        "min_article_words": self.min_article_words,
                        "max_article_words": self.max_article_words,
                        "keyword_density_min_pct": self.keyword_density_min,
                        "keyword_density_max_pct": self.keyword_density_max,
                        "table_count": table_count,
                        "ul_count": ul_count,
                        "ol_count": ol_count,
                        "blockquote_count": blockquote_count,
                        "checklist_li_count": checklist_li_count,
                        "bold_anchor_count": bold_anchor_count,
                        "strong_count": strong_count,
                        "strong_ratio_pct": round(bold_ratio * 100.0, 2),
                        "visual_device_count": visual_device_count,
                        "visual_devices": [k for k, v in visual_devices.items() if v],
                        "structure_signature_repeats": int(signature_counts.get(signature_by_item.get(item_id, ""), 0)),
                        "table_first_pos_pct": round((table_pos / html_len) * 100.0, 2) if table_pos >= 0 else None,
                        "list_first_pos_pct": round((first_list_pos / html_len) * 100.0, 2) if first_list_pos >= 0 else None,
                        "long_paragraphs": long_paragraphs,
                    },
                    "flags": {
                        "flag_rewrite": flag,
                        "reason_codes": sorted(set(reason_codes)),
                    },
                    "issues": sorted(set(issues)),
                    "rewrite_guidance": guidance,
                }
            )
            self.log("audit", "success", item_id=item_id, version=int(a["version"]), metrics={"score": score, "flag": flag})

        out = {"batch_id": self.batch_id, "threshold": self.threshold, "items": items}
        write_json(self.base / "outputs/audits" / f"{self.batch_id}_seo_audit.json", out)
        write_json(self.batch_dir / "seo_audit.json", out)
        return out

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return [t for t in text.split() if len(t) > 2]

    def _jaccard_3gram(self, a: str, b: str) -> float:
        def grams(s: str):
            toks = self._tokenize(s)
            return set(tuple(toks[i:i+3]) for i in range(max(0, len(toks)-2)))
        ga, gb = grams(a), grams(b)
        if not ga or not gb:
            return 0.0
        return len(ga & gb) / max(1, len(ga | gb))

    def _cosine_bow(self, a: str, b: str) -> float:
        ca = Counter(self._tokenize(a))
        cb = Counter(self._tokenize(b))
        if not ca or not cb:
            return 0.0
        common = set(ca.keys()) & set(cb.keys())
        dot = sum(ca[t] * cb[t] for t in common)
        na = sum(v * v for v in ca.values()) ** 0.5
        nb = sum(v * v for v in cb.values()) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _load_history(self) -> List[dict]:
        out = []
        if not self.history_file.exists():
            return out
        for line in self.history_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    def agent04_similarity(self, articles: Dict[str, dict]) -> dict:
        history = self._load_history()
        ids = list(articles.keys())
        texts = {i: strip_html(self._parse_package(articles[i]["content_package"])[1]) for i in ids}

        items = []
        for i in ids:
            best_score = 0.0
            conflicts = []
            ai = articles[i]
            ti = texts[i]

            # within batch
            for j in ids:
                if i == j:
                    continue
                aj = articles[j]
                tj = texts[j]
                jac = self._jaccard_3gram(ti, tj)
                cos = self._cosine_bow(ti, tj)
                sem = 1.0 if ai["keyword_primaria"].lower() == aj["keyword_primaria"].lower() else 0.0
                score = (jac * 0.45 + cos * 0.45 + sem * 0.10) * 100.0
                best_score = max(best_score, score)
                if score >= 20:
                    conflicts.append({"other_id": j, "score": round(score, 2), "reason": "batch_overlap"})

            # vs history
            for h in history[-400:]:
                excerpt = h.get("excerpt", "")
                if not excerpt:
                    continue
                jac = self._jaccard_3gram(ti, excerpt)
                cos = self._cosine_bow(ti, excerpt)
                sem = 1.0 if ai["keyword_primaria"].lower() == str(h.get("keyword_primaria", "")).lower() else 0.0
                score = (jac * 0.45 + cos * 0.45 + sem * 0.10) * 100.0
                best_score = max(best_score, score)
                if score >= 22:
                    conflicts.append({"other_id": h.get("id", "history"), "score": round(score, 2), "reason": "history_overlap"})

            best_score = round(best_score, 2)
            if best_score > 60:
                status = "rewrite"
            elif best_score >= 40:
                status = "risk"
            else:
                status = "ok"

            flag = best_score > 60
            guidance = ""
            if flag:
                guidance = "Reduzir sobreposição semântica: mudar abordagem, headings, exemplos e intenção sem perder keyword foco."

            item = {
                "id": i,
                "version": int(ai["version"]),
                "similarity_score": best_score,
                "status": status,
                "conflicts": sorted(conflicts, key=lambda x: x["score"], reverse=True)[:8],
                "flag_similarity": flag,
                "rewrite_guidance": guidance,
            }
            items.append(item)
            self.log("similarity", "success", item_id=i, version=int(ai["version"]), metrics={"score": best_score, "status": status})

        out = {
            "batch_id": self.batch_id,
            "policy": {"risk_threshold": 40, "rewrite_threshold": 60},
            "items": items,
        }
        write_json(self.base / "outputs/similarity" / f"{self.batch_id}_similarity.json", out)
        write_json(self.batch_dir / "similarity_report.json", out)
        return out

    def agent05_image_prompts(self, approved_articles: Dict[str, dict]) -> List[dict]:
        rows = []
        for item_id, a in approved_articles.items():
            theme = a["tema_principal"]
            article_text = self._extract_article_context_for_image(a.get("content_package", ""), max_chars=2200)
            prompt = self._build_image_prompt(a, article_text)
            rows.append(
                {
                    "id": item_id,
                    "article_title": theme,
                    "slug": a.get("slug", ""),
                    "dimensions": "1200x630",
                    "style": "Sowads premium marketing ops",
                    "prompt": prompt,
                    "negative_prompt": (
                        "text overlays, letters, words, logo, watermark, brand name, UI screenshot, "
                        "street signs with readable text, license plates, store fronts with readable names, "
                        "vehicle grille emblems, car badges, dashboard numbers, odometers, speedometers, "
                        "financial statements with numbers, card numbers, invoice text, "
                        "billboards, newspaper headlines, subtitle text, caption text, "
                        "pure landscape, nature panorama without people, empty sky, empty road, "
                        "generic stock-photo handshake, legal document close-up, low resolution, blur, "
                        "noise artifacts, duplicated faces, deformed hands, extra fingers, cartoon style, "
                        "pixel art, clipping, oversaturation, purple palette dominance, dystopian mood"
                    ),
                }
            )
            self.log("image-prompts", "success", item_id=item_id, version=int(a["version"]))

        path1 = self.base / "outputs/image-prompts" / f"{self.batch_id}_image_prompts.csv"
        path2 = self.batch_dir / "image_prompts.csv"
        write_csv(path1, rows, IMAGE_PROMPT_COLUMNS)
        write_csv(path2, rows, IMAGE_PROMPT_COLUMNS)
        return rows

    def _extract_article_context_for_image(self, content_package: str, max_chars: int = 2200) -> str:
        # Use article body (not only title/meta wrapper) as semantic source for image prompt grounding.
        _, html = self._parse_package(content_package or "")
        raw = html if html else (content_package or "")

        # Remove common wrapper tokens and markdown fences that can pollute semantic extraction.
        raw = re.sub(r"```(?:html)?", " ", raw, flags=re.I)
        raw = raw.replace("```", " ")
        raw = re.sub(r"===\s*META INFORMATION\s*===", " ", raw, flags=re.I)
        raw = re.sub(r"===\s*HTML PACKAGE[^=]*===", " ", raw, flags=re.I)

        # Prefer dedicated article-body root, fallback to legacy <article>.
        body_match = re.search(
            r"<div\b[^>]*class=[\"'][^\"']*sowads-article-body[^\"']*[\"'][^>]*>(.*?)</div>",
            raw,
            flags=re.I | re.S,
        )
        if body_match:
            raw = body_match.group(1)
        else:
            article_match = re.search(r"<article\b[^>]*>(.*?)</article>", raw, flags=re.I | re.S)
            if article_match:
                raw = article_match.group(1)

        # Remove non-visual/script blocks before converting to plain text.
        raw = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
        text = strip_html(raw)

        # Remove leftovers from metadata labels if present in plain text.
        text = re.sub(r"\bMeta Title:\s*[^\n]+", " ", text, flags=re.I)
        text = re.sub(r"\bMeta Description:\s*[^\n]+", " ", text, flags=re.I)
        text = re.sub(r"\bSlug:\s*[^\n]+", " ", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return ""
        return text[:max_chars]

    def _build_image_prompt(self, article: dict, article_excerpt: str) -> str:
        title = article.get("tema_principal", "").strip()
        keyword = article.get("keyword_primaria", "").strip()
        secondary = [k.strip() for k in article.get("keywords_secundarias", "").split("|") if k.strip()]
        secondary_txt = ", ".join(secondary[:4]) if secondary else "content operations, media intelligence, editorial workflow"
        vertical = article.get("vertical_alvo", "Geral").strip()
        vertical_lc = vertical.lower()
        business_model = article.get("modelo_negocio_alvo", "B2B").strip()
        company_size = article.get("porte_empresa_alvo", "Média Empresa").strip()
        angle = article.get("angulo_conteudo", "Educacional").strip()
        product_focus = article.get("produto_sowads_foco", "Ambos os pilares").strip()
        excerpt = re.sub(r"\s+", " ", article_excerpt).strip()

        vertical_rules = ""
        if "automotivo" in vertical_lc:
            vertical_rules = (
                "Vertical-specific rule (Automotivo): avoid hero shots of branded cars. "
                "If a vehicle appears, use neutral side/rear silhouettes only, with no visible grille badges, no logos, "
                "no readable plate characters, no dashboard labels, and no identifiable brand design cues."
            )
        elif "financeiro" in vertical_lc:
            vertical_rules = (
                "Vertical-specific rule (Financeiro): avoid literal money symbolism, no banknote close-ups, "
                "no credit card numbers, no account statements, and no readable compliance/legal text on screens or documents."
            )
        else:
            vertical_rules = (
                "Vertical-specific rule: prioritize executive operations context with human teams and non-readable "
                "decision artifacts over literal product hero shots."
            )

        prompt = f"""
Create a premium featured image for a Portuguese business article from Sowads, with cinematic realism and strategic clarity. 
The article title is "{title}" and the primary concept is "{keyword}". 
Relevant secondary themes include: {secondary_txt}. 
The target context is {vertical} operations, {business_model}, company size {company_size}, with editorial angle "{angle}" and product focus "{product_focus}".

Narrative intent:
Represent high-performance consulting and AI-enabled operations as something concrete, modern, and executive, not abstract gimmicks.
Show a scene that suggests measurable business impact: analysts, planners, media strategists, non-readable performance signals, collaborative decision-making, and structured execution.
The visual must communicate trust, method, sophistication, governance, and scale with human oversight.
The image should feel like an enterprise consulting campaign visual, not a startup cliché.

Brand art direction (Sowads):
Use a restrained, premium palette inspired by Sowads: warm yellow accent (#F5BF00), graphite/dark charcoal neutrals (#4F4F52 / #2F2F33), balanced whites and soft grays.
Yellow should guide visual hierarchy in subtle strategic points (data highlights, edge light, interface markers), never overwhelming the frame.
Avoid purple-first grading and avoid visual drift to random trendy neon.
Typography is not allowed in final output; communicate through composition only.

Composition and camera:
Design for 1200x630 (landscape social share card).
Use a clear foreground-midground-background structure with depth.
Keep a strong focal point that leaves safe breathing areas for future crops.
Prefer 35mm–50mm cinematic framing, medium depth of field, natural lens behavior, no fisheye distortion.
Lighting should be natural plus controlled practical lights, with realistic reflections, mild contrast, and no crushed blacks.

Business realism constraints:
Depict tools and interfaces as believable but non-readable.
No fake logos, no readable brand names, no fake legal seals.
No visible letters or numbers in any part of the image.
No obvious stock-photo handshake posing.
No exaggerated sci-fi holograms.
No generic “robot face” as hero.
Prioritize people and operational context over product close-ups.
If screens appear, they must be out-of-focus or abstract shape-based charts with zero readable digits.
Do not generate landscape-only scenes (nature, skyline, roads, sunsets) without clear business context.
Do not use traffic signs, storefront signs, license plates, dashboard labels, or documents with readable text.
If people appear, they must look focused, credible, and professional, with accurate anatomy.
Hands must be correct and natural.
{vertical_rules}

Semantic alignment with article:
The visual metaphor must reflect this article excerpt:
"{excerpt}"
Translate the excerpt into an operational story frame: planning, prioritization, distributed execution, iterative optimization, and performance accountability.
Favor scenes that imply consulting intelligence + media execution + AI augmentation under human review.

Output quality bar:
Photorealistic, polished, editorial-grade, agency-quality image suitable for a premium consulting website hero/card.
High detail, clean geometry, coherent shadows, realistic materials, and confident executive atmosphere.
No text, no watermark, no logo.
""".strip()

        words = len(prompt.split())
        if words < 400:
            extension = (
                " Extend the scene with richer environmental storytelling: add subtle details of operations rooms, "
                "meeting artifacts, timeline boards, anonymous charts, and non-readable KPI structures. "
                "Keep consistency with the same visual language, preserve realism, and reinforce the message of "
                "consulting-led growth systems with AI support and rigorous human quality control."
            )
            prompt = (prompt + extension).strip()
        return prompt

    def agent06_publish(self, approved_articles: Dict[str, dict], audit_map: Dict[str, dict], sim_map: Dict[str, dict]) -> dict:
        publish_mode = self.cfg.get("publish_mode", "draft")
        published = []
        failed = []

        for item_id, a in approved_articles.items():
            audit = audit_map[item_id]
            sim = sim_map[item_id]
            critical = bool(CRITICAL_REASON_CODES.intersection(audit["flags"]["reason_codes"]))
            if audit["seo_geo_score"] < 80 or sim["similarity_score"] > 60 or critical:
                failed.append(
                    {
                        "id": item_id,
                        "version": int(a["version"]),
                        "error": "blocked_by_policy",
                        "timestamp": now_iso(),
                    }
                )
                append_jsonl(self.publication_logs, {"timestamp": now_iso(), "batch_id": self.batch_id, "id": item_id, "status": "blocked"})
                continue

            if self.test_mode:
                published.append(
                    {
                        "id": item_id,
                        "version": int(a["version"]),
                        "wp_post_id": 0,
                        "status": "dry_run",
                        "timestamp": now_iso(),
                    }
                )
                append_jsonl(self.publication_logs, {"timestamp": now_iso(), "batch_id": self.batch_id, "id": item_id, "status": "dry_run"})
            else:
                # Placeholder real publication path.
                published.append(
                    {
                        "id": item_id,
                        "version": int(a["version"]),
                        "wp_post_id": 0,
                        "status": publish_mode,
                        "timestamp": now_iso(),
                    }
                )
                append_jsonl(self.publication_logs, {"timestamp": now_iso(), "batch_id": self.batch_id, "id": item_id, "status": publish_mode})

        out = {"batch_id": self.batch_id, "published": published, "failed": failed}
        write_json(self.base / "outputs/published" / f"{self.batch_id}_publish_results.json", out)
        write_json(self.batch_dir / "publish_results.json", out)
        self.log("publish", "success", metrics={"published": len(published), "failed": len(failed)})
        return out

    def update_history(self, approved_articles: Dict[str, dict], audit_map: Dict[str, dict], sim_map: Dict[str, dict]):
        entries = []
        for item_id, a in approved_articles.items():
            html = self._parse_package(a["content_package"])[1]
            norm = strip_html(html)
            entry = {
                "id": item_id,
                "version": int(a["version"]),
                "title": a["tema_principal"],
                "slug": a["slug"],
                "keyword_primaria": a["keyword_primaria"],
                "keywords_secundarias": a["keywords_secundarias"],
                "funil": "",
                "angulo_conteudo": a["angulo_conteudo"],
                "vertical": a["vertical_alvo"],
                "porte": a["porte_empresa_alvo"],
                "content_hash": hashlib.sha256(norm.encode("utf-8")).hexdigest(),
                "excerpt": norm[:800],
                "seo_geo_score": audit_map[item_id]["seo_geo_score"],
                "similarity_score": sim_map[item_id]["similarity_score"],
                "timestamp": now_iso(),
            }
            entries.append(entry)
            append_jsonl(self.history_file, entry)

        idx = {"last_batch_id": self.batch_id, "updated_at": now_iso(), "added": len(entries)}
        self.history_index.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

    def run_single_agent(
        self,
        agent_name: str,
        themes_file: str = "",
        articles_file: str = "",
        audit_file: str = "",
        similarity_file: str = "",
        async_output: bool = False,
        job_id: str = "",
    ) -> dict:
        job_id = job_id.strip() or ("ASYNC-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
        files: List[Path] = []
        summary: Dict[str, object] = {
            "agent": agent_name,
            "batch_id": self.batch_id,
            "timestamp": now_iso(),
            "test_mode": self.test_mode,
        }

        if agent_name == "agent01":
            themes = self.agent01_generate_themes()
            files = [
                self.base / "outputs/themes" / f"{self.batch_id}_themes.csv",
                self.batch_dir / "themes.csv",
            ]
            summary["items_total"] = len(themes)

        elif agent_name == "agent02":
            if themes_file:
                themes = self._load_themes_from_csv(self._resolve_input_path(themes_file))
            else:
                themes = self.agent01_generate_themes()
                files.extend(
                    [
                        self.base / "outputs/themes" / f"{self.batch_id}_themes.csv",
                        self.batch_dir / "themes.csv",
                    ]
                )
            article_state = self.agent02_generate_articles(themes)
            write_csv(self.base / "outputs/articles" / f"{self.batch_id}_articles_v1.csv", list(article_state.values()), ARTICLE_COLUMNS)
            write_csv(self.batch_dir / "articles_v1.csv", list(article_state.values()), ARTICLE_COLUMNS)
            write_csv(self.base / "outputs/articles" / f"{self.batch_id}_articles.csv", list(article_state.values()), ARTICLE_COLUMNS)
            files.extend(
                [
                    self.base / "outputs/articles" / f"{self.batch_id}_articles_v1.csv",
                    self.base / "outputs/articles" / f"{self.batch_id}_articles.csv",
                    self.batch_dir / "articles_v1.csv",
                ]
            )
            summary["items_total"] = len(article_state)

        elif agent_name == "agent03":
            if not articles_file:
                raise SystemExit("--articles-file é obrigatório para agent03")
            articles = self._load_articles_from_csv(self._resolve_input_path(articles_file))
            audit = self.agent03_audit(articles)
            files = [
                self.base / "outputs/audits" / f"{self.batch_id}_seo_audit.json",
                self.batch_dir / "seo_audit.json",
            ]
            summary["items_total"] = len(audit.get("items", []))

        elif agent_name == "agent04":
            if not articles_file:
                raise SystemExit("--articles-file é obrigatório para agent04")
            articles = self._load_articles_from_csv(self._resolve_input_path(articles_file))
            similarity = self.agent04_similarity(articles)
            files = [
                self.base / "outputs/similarity" / f"{self.batch_id}_similarity.json",
                self.batch_dir / "similarity_report.json",
            ]
            summary["items_total"] = len(similarity.get("items", []))

        elif agent_name == "agent05":
            if not articles_file:
                raise SystemExit("--articles-file é obrigatório para agent05")
            articles = self._load_articles_from_csv(self._resolve_input_path(articles_file))
            approved = {i: a for i, a in articles.items() if str(a.get("status", "")).upper() == "APPROVED"}
            if not approved:
                approved = articles
            rows = self.agent05_image_prompts(approved)
            files = [
                self.base / "outputs/image-prompts" / f"{self.batch_id}_image_prompts.csv",
                self.batch_dir / "image_prompts.csv",
            ]
            summary["items_total"] = len(rows)

        elif agent_name == "agent06":
            if not articles_file or not audit_file or not similarity_file:
                raise SystemExit("--articles-file, --audit-file e --similarity-file são obrigatórios para agent06")
            articles = self._load_articles_from_csv(self._resolve_input_path(articles_file))
            audit_obj = read_json(self._resolve_input_path(audit_file))
            sim_obj = read_json(self._resolve_input_path(similarity_file))
            audit_map = {x["id"]: x for x in audit_obj.get("items", [])}
            sim_map = {x["id"]: x for x in sim_obj.get("items", [])}
            approved = {i: a for i, a in articles.items() if i in audit_map and i in sim_map}
            pub = self.agent06_publish(approved, audit_map, sim_map)
            files = [
                self.base / "outputs/published" / f"{self.batch_id}_publish_results.json",
                self.batch_dir / "publish_results.json",
            ]
            summary["items_total"] = len(approved)
            summary["publish_results"] = pub

        else:
            raise SystemExit(f"Agente inválido: {agent_name}")

        if async_output:
            out_dir = self._save_async_artifacts(agent_name, job_id, files, summary)
            summary["async_output_dir"] = str(out_dir.relative_to(self.base))

        return summary

    def run(self):
        self.log("pipeline", "start", metrics={"test_mode": self.test_mode})

        themes = self.agent01_generate_themes()

        article_state = self.agent02_generate_articles(themes)

        iteration = 1
        write_csv(self.base / "outputs/articles" / f"{self.batch_id}_articles_v{iteration}.csv", list(article_state.values()), ARTICLE_COLUMNS)
        write_csv(self.batch_dir / f"articles_v{iteration}.csv", list(article_state.values()), ARTICLE_COLUMNS)

        audit = self.agent03_audit(article_state)
        similarity = self.agent04_similarity(article_state)

        for _ in range(self.max_rewrites):
            audit_map = {x["id"]: x for x in audit["items"]}
            sim_map = {x["id"]: x for x in similarity["items"]}

            rewrite_map = {}
            for item_id in article_state.keys():
                if audit_map[item_id]["flags"]["flag_rewrite"]:
                    rewrite_map[item_id] = audit_map[item_id]["rewrite_guidance"]
                elif sim_map[item_id]["flag_similarity"]:
                    rewrite_map[item_id] = sim_map[item_id]["rewrite_guidance"]

            if not rewrite_map:
                break

            article_state = self.agent02_generate_articles(themes, current=article_state, rewrite_map=rewrite_map)
            iteration += 1
            write_csv(self.base / "outputs/articles" / f"{self.batch_id}_articles_v{iteration}.csv", list(article_state.values()), ARTICLE_COLUMNS)
            write_csv(self.batch_dir / f"articles_v{iteration}.csv", list(article_state.values()), ARTICLE_COLUMNS)

            audit = self.agent03_audit(article_state)
            similarity = self.agent04_similarity(article_state)

        # final maps
        audit_map = {x["id"]: x for x in audit["items"]}
        sim_map = {x["id"]: x for x in similarity["items"]}

        approved = {}
        for item_id, a in article_state.items():
            if audit_map[item_id]["seo_geo_score"] >= 80 and not audit_map[item_id]["flags"]["flag_rewrite"] and sim_map[item_id]["similarity_score"] <= 60:
                a["status"] = "APPROVED"
                approved[item_id] = a
            else:
                a["status"] = "REJECTED"

        # persist final article table
        write_csv(self.base / "outputs/articles" / f"{self.batch_id}_articles.csv", list(article_state.values()), ARTICLE_COLUMNS)

        self.agent05_image_prompts(approved)
        publish_results = self.agent06_publish(approved, audit_map, sim_map)
        self.update_history(approved, audit_map, sim_map)

        summary = {
            "batch_id": self.batch_id,
            "items_total": len(article_state),
            "approved": len(approved),
            "rejected": len(article_state) - len(approved),
            "iterations": iteration,
            "test_mode": self.test_mode,
            "publish_results": publish_results,
        }
        write_json(self.batch_dir / "summary.json", summary)
        self.log("pipeline", "success", metrics=summary)
        return summary


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Run SOWADS content engine pipeline")
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]), help="Project root")
    parser.add_argument("--config", default="orchestrator/config.example.json", help="Config JSON path (relative to base or absolute)")
    parser.add_argument(
        "--agent",
        default="all",
        choices=["all", "agent01", "agent02", "agent03", "agent04", "agent05", "agent06"],
        help="Rodar pipeline completo ou agente individual",
    )
    parser.add_argument("--test-mode", action="store_true", help="Force test mode")
    parser.add_argument("--quantity", type=int, default=None, help="Override quantidade_temas")
    parser.add_argument("--themes-file", default="", help="CSV de temas para agent02")
    parser.add_argument("--articles-file", default="", help="CSV de artigos para agent03/04/05/06")
    parser.add_argument("--audit-file", default="", help="JSON de auditoria para agent06")
    parser.add_argument("--similarity-file", default="", help="JSON de similaridade para agent06")
    parser.add_argument("--job-id", default="", help="ID opcional para saída assíncrona")
    parser.add_argument("--async-output", action="store_true", help="Copiar artefatos para outputs/assincronos/{agent}/{job_id}")
    args = parser.parse_args()

    base = Path(args.base).resolve()

    # env precedence: project .env -> parent .env
    load_env_file(base / ".env")
    load_env_file(base.parent / ".env")

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = base / cfg_path
    cfg = load_config(cfg_path)

    if args.test_mode:
        cfg["test_mode"] = True
    if args.quantity is not None:
        cfg["quantidade_temas"] = args.quantity

    needs_gemini = args.agent in {"all", "agent01", "agent02"}
    if needs_gemini and not cfg.get("test_mode", False) and not os.getenv("GEMINI_API_KEY", ""):
        raise SystemExit("GEMINI_API_KEY not configured in environment/.env")

    p = Pipeline(base, cfg)
    if args.agent == "all":
        result = p.run()
    else:
        result = p.run_single_agent(
            agent_name=args.agent,
            themes_file=args.themes_file,
            articles_file=args.articles_file,
            audit_file=args.audit_file,
            similarity_file=args.similarity_file,
            async_output=args.async_output,
            job_id=args.job_id,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
