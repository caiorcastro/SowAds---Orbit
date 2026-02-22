#!/usr/bin/env python3
import argparse
import base64
import csv
import hashlib
import json
import os
import posixpath
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import urllib.error
import urllib.parse
import urllib.request


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: List[dict], columns: List[str]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


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


def parse_batch_id_from_filename(name: str) -> str:
    # pattern expected: BATCH-YYYYMMDD-HHMMSS_image_prompts.csv
    if name.startswith("BATCH-") and "_image_prompts.csv" in name:
        return name.split("_image_prompts.csv", 1)[0]
    return "BATCH-UNKNOWN"


def ext_from_mime(mime_type: str) -> str:
    mapping = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
    }
    return mapping.get((mime_type or "").lower(), "png")


def read_prompts(csv_path: Path) -> List[dict]:
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def estimate_tokens(text: str) -> int:
    return max(1, int(round(len(text) / 4)))


def ext_from_url(url: str, fallback: str = "png") -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        suffix = Path(posixpath.basename(parsed.path)).suffix.lower().lstrip(".")
        if suffix in {"png", "jpg", "jpeg", "webp"}:
            return "jpg" if suffix == "jpeg" else suffix
    except Exception:
        pass
    return fallback


def download_bytes(url: str, timeout: int = 240, headers: Optional[Dict[str, str]] = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def extract_first_json_object(text: str) -> Optional[dict]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    raw = m.group(0).strip()
    try:
        return json.loads(raw)
    except Exception:
        return None


class GeminiImageValidator:
    def __init__(self, base: Path):
        self.base = base
        self.enabled = os.getenv("IMAGE_VALIDATION_ENABLED", "true").strip().lower() in {"1", "true", "yes", "y"}
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.api_base = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").strip()
        self.model = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")).strip()
        self.delay_seconds = float(os.getenv("REQUEST_DELAY_SECONDS", "0.6"))
        self.gemini_log_file = base / "data/logs/gemini_calls.jsonl"
        # Balanced defaults: reject only clearly problematic cases (strange text / generic landscape).
        self.min_no_text_score = int(os.getenv("IMAGE_VALIDATION_MIN_NO_TEXT", "60"))
        self.min_relevance_score = int(os.getenv("IMAGE_VALIDATION_MIN_RELEVANCE", "60"))
        self.min_business_score = int(os.getenv("IMAGE_VALIDATION_MIN_BUSINESS_SCENE", "40"))
        self.max_detected_text_chars = int(os.getenv("IMAGE_VALIDATION_MAX_DETECTED_TEXT_CHARS", "80"))

        default_input = float(os.getenv("GEMINI_INPUT_COST_PER_1M_USD", "0.0"))
        default_output = float(os.getenv("GEMINI_OUTPUT_COST_PER_1M_USD", "0.0"))
        self.input_cost_per_1m = float(os.getenv("GEMINI_IMAGE_VALIDATION_INPUT_COST_PER_1M_USD", str(default_input)))
        self.output_cost_per_1m = float(os.getenv("GEMINI_IMAGE_VALIDATION_OUTPUT_COST_PER_1M_USD", str(default_output)))

    def _cost_block(self, prompt_tokens: Optional[int], output_tokens: Optional[int], prompt: str, out_text: str) -> dict:
        estimated_by_heuristic = False
        if prompt_tokens is None:
            prompt_tokens = estimate_tokens(prompt)
            estimated_by_heuristic = True
        if output_tokens is None:
            output_tokens = estimate_tokens(out_text)
            estimated_by_heuristic = True
        est = (prompt_tokens / 1_000_000.0) * self.input_cost_per_1m + (output_tokens / 1_000_000.0) * self.output_cost_per_1m
        return {
            "prompt_tokens": int(prompt_tokens),
            "output_tokens": int(output_tokens),
            "input_cost_per_1m_usd": self.input_cost_per_1m,
            "output_cost_per_1m_usd": self.output_cost_per_1m,
            "estimated_cost_usd": round(float(est), 8),
            "estimated_by_heuristic": estimated_by_heuristic,
            "pricing_configured": (self.input_cost_per_1m > 0.0 or self.output_cost_per_1m > 0.0),
        }

    def _compose_validation_prompt(self, article_title: str, keyword: str, prompt_used: str) -> str:
        return (
            "You are a strict image QA validator for a B2B marketing website.\n"
            "Evaluate if this generated image is valid as a featured image.\n\n"
            f"Article title: {article_title}\n"
            f"Primary keyword: {keyword}\n\n"
            "Validation rules (all mandatory):\n"
            "1) No visible text, letters, numbers, logos, watermarks, brand marks, UI labels, signage, plates.\n"
            "2) No generic landscape-only scene. Must show business context related to operations, strategy, media, analytics, planning, consulting, or execution.\n"
            "3) Must be semantically aligned with the article title/keyword and not random.\n"
            "4) Must look photorealistic and professionally composed for enterprise editorial use.\n\n"
            "Return STRICT JSON only:\n"
            "{\n"
            "  \"pass\": true|false,\n"
            "  \"scores\": {\n"
            "    \"no_visible_text_or_logo\": 0-100,\n"
            "    \"semantic_relevance\": 0-100,\n"
            "    \"business_context_clarity\": 0-100,\n"
            "    \"photorealism\": 0-100\n"
            "  },\n"
            "  \"detected_text\": \"string with detected readable text or empty\",\n"
            "  \"issues\": [\"issue1\", \"issue2\"],\n"
            "  \"correction_prompt\": \"one short sentence to fix failures\"\n"
            "}\n\n"
            "Prompt used to generate image (for reference):\n"
            f"{prompt_used[:2200]}"
        )

    def validate(
        self,
        image_bytes: bytes,
        mime_type: str,
        batch_id: str,
        item_id: str,
        article_title: str,
        keyword: str,
        prompt_used: str,
    ) -> dict:
        if not self.enabled:
            return {
                "pass": True,
                "scores": {
                    "no_visible_text_or_logo": 100,
                    "semantic_relevance": 100,
                    "business_context_clarity": 100,
                    "photorealism": 100,
                },
                "detected_text": "",
                "issues": [],
                "correction_prompt": "",
                "raw_response": "",
            }

        endpoint = f"{self.api_base}/models/{self.model}:generateContent?key={urllib.parse.quote(self.api_key)}"
        text_prompt = self._compose_validation_prompt(article_title, keyword, prompt_used)
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": text_prompt},
                        {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(image_bytes).decode("ascii")}},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.0},
        }

        started_at = now_iso()
        t0 = time.time()
        status_code = 0
        raw_body = ""
        response_text = ""
        usage = {}
        error_text = ""

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                status_code = int(getattr(resp, "status", 200))
                raw_body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status_code = int(getattr(e, "code", 0) or 0)
            raw_body = e.read().decode("utf-8", errors="replace")
            error_text = f"Gemini HTTP {status_code}"
        except urllib.error.URLError as e:
            error_text = f"Gemini network error: {e}"

        verdict = {
            "pass": False,
            "scores": {
                "no_visible_text_or_logo": 0,
                "semantic_relevance": 0,
                "business_context_clarity": 0,
                "photorealism": 0,
            },
            "detected_text": "",
            "issues": ["validation_error"],
            "correction_prompt": "Regenerate with zero visible text and stronger business context tied to the article.",
            "raw_response": "",
        }

        if not error_text:
            try:
                body = json.loads(raw_body)
                usage = body.get("usageMetadata", {}) if isinstance(body, dict) else {}
                parts = (((body.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
                response_text = "\n".join([str(p.get("text", "")) for p in parts if p.get("text")]).strip()
                verdict_obj = extract_first_json_object(response_text) or {}
                scores = verdict_obj.get("scores") or {}
                detected_text = str(verdict_obj.get("detected_text", "") or "").strip()
                issues = verdict_obj.get("issues") if isinstance(verdict_obj.get("issues"), list) else []
                correction = str(verdict_obj.get("correction_prompt", "") or "").strip()
                no_text = int(scores.get("no_visible_text_or_logo", 0) or 0)
                relevance = int(scores.get("semantic_relevance", 0) or 0)
                business = int(scores.get("business_context_clarity", 0) or 0)
                photo = int(scores.get("photorealism", 0) or 0)
                issues_lc = " ".join([str(i).lower() for i in issues[:8]])

                hard_fail = (
                    ("landscape" in issues_lc and business < 55)
                    or ("generic nature" in issues_lc and business < 55)
                    or (("readable text" in issues_lc or "visible text" in issues_lc) and no_text < 50)
                    or (bool(detected_text and len(detected_text) > self.max_detected_text_chars) and no_text < 50)
                )
                auto_pass = (
                    no_text >= self.min_no_text_score
                    and relevance >= self.min_relevance_score
                    and business >= self.min_business_score
                    and photo >= 60
                    and not hard_fail
                )
                declared_pass = bool(verdict_obj.get("pass"))
                verdict = {
                    "pass": bool(declared_pass and auto_pass),
                    "scores": {
                        "no_visible_text_or_logo": no_text,
                        "semantic_relevance": relevance,
                        "business_context_clarity": business,
                        "photorealism": photo,
                    },
                    "detected_text": detected_text,
                    "issues": issues[:8],
                    "correction_prompt": correction or "Regenerate with zero text/logo and explicit business operational scene tied to the article.",
                    "raw_response": response_text,
                }
            except Exception as e:
                error_text = f"Validation parse error: {e}"

        latency_ms = int((time.time() - t0) * 1000)
        append_jsonl(
            self.gemini_log_file,
            {
                "timestamp": started_at,
                "completed_at": now_iso(),
                "latency_ms": latency_ms,
                "provider": "gemini",
                "model": self.model,
                "phase": "image-validation",
                "agent": "agent_05_image_validator",
                "batch_id": batch_id,
                "id": item_id,
                "version": 0,
                "http_status_code": status_code or 0,
                "success": (not bool(error_text)),
                "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                "request": {
                    "prompt_sha256": hashlib.sha256(text_prompt.encode("utf-8")).hexdigest(),
                    "prompt_text": text_prompt,
                    "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
                    "mime_type": mime_type,
                },
                "response_raw": raw_body,
                "response_text": response_text,
                "usage_metadata": usage,
                "cost_estimate": self._cost_block(usage.get("promptTokenCount"), usage.get("candidatesTokenCount"), text_prompt, response_text),
                "error": error_text,
            },
        )

        time.sleep(self.delay_seconds)
        if error_text:
            # Fail closed: if validator errors, we do not silently accept broken image.
            return {
                "pass": False,
                "scores": verdict["scores"],
                "detected_text": "",
                "issues": ["validation_unavailable", error_text],
                "correction_prompt": "Regenerate with strict no-text and explicit business context.",
                "raw_response": response_text,
            }
        return verdict


class GeminiImageRenderer:
    def __init__(self, base: Path):
        self.base = base
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.api_base = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").strip()
        self.model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image").strip()
        self.delay_seconds = float(os.getenv("REQUEST_DELAY_SECONDS", "0.6"))
        self.gemini_log_file = base / "data/logs/gemini_calls.jsonl"

        default_input = float(os.getenv("GEMINI_INPUT_COST_PER_1M_USD", "0.0"))
        default_output = float(os.getenv("GEMINI_OUTPUT_COST_PER_1M_USD", "0.0"))
        self.input_cost_per_1m = float(os.getenv("GEMINI_IMAGE_INPUT_COST_PER_1M_USD", str(default_input)))
        self.output_cost_per_1m = float(os.getenv("GEMINI_IMAGE_OUTPUT_COST_PER_1M_USD", str(default_output)))

    def _cost_block(self, prompt_tokens: Optional[int], output_tokens: Optional[int], prompt: str, out_text: str) -> dict:
        estimated_by_heuristic = False
        if prompt_tokens is None:
            prompt_tokens = estimate_tokens(prompt)
            estimated_by_heuristic = True
        if output_tokens is None:
            output_tokens = estimate_tokens(out_text)
            estimated_by_heuristic = True
        est = (prompt_tokens / 1_000_000.0) * self.input_cost_per_1m + (output_tokens / 1_000_000.0) * self.output_cost_per_1m
        return {
            "prompt_tokens": int(prompt_tokens),
            "output_tokens": int(output_tokens),
            "input_cost_per_1m_usd": self.input_cost_per_1m,
            "output_cost_per_1m_usd": self.output_cost_per_1m,
            "estimated_cost_usd": round(float(est), 8),
            "estimated_by_heuristic": estimated_by_heuristic,
            "pricing_configured": (self.input_cost_per_1m > 0.0 or self.output_cost_per_1m > 0.0),
        }

    def generate(self, prompt: str, batch_id: str, item_id: str) -> Tuple[List[dict], dict]:
        endpoint = f"{self.api_base}/models/{self.model}:generateContent?key={urllib.parse.quote(self.api_key)}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        started_at = now_iso()
        t0 = time.time()
        status_code = 0
        raw_body = ""
        response_text = ""
        usage = {}

        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                status_code = int(getattr(resp, "status", 200))
                raw_body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status_code = int(getattr(e, "code", 0) or 0)
            raw_body = e.read().decode("utf-8", errors="replace")
            latency_ms = int((time.time() - t0) * 1000)
            append_jsonl(
                self.gemini_log_file,
                {
                    "timestamp": started_at,
                    "completed_at": now_iso(),
                    "latency_ms": latency_ms,
                    "provider": "gemini",
                    "model": self.model,
                    "phase": "image-generation",
                    "agent": "agent_05_image_render",
                    "batch_id": batch_id,
                    "id": item_id,
                    "version": 0,
                    "http_status_code": status_code,
                    "success": False,
                    "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                    "request": {
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "prompt_text": prompt,
                    },
                    "response_raw": raw_body,
                    "response_text": "",
                    "usage_metadata": {},
                    "cost_estimate": self._cost_block(None, None, prompt, ""),
                    "error": f"Gemini HTTP {status_code}",
                },
            )
            raise RuntimeError(f"Gemini HTTP {status_code}: {raw_body}") from e
        except urllib.error.URLError as e:
            latency_ms = int((time.time() - t0) * 1000)
            append_jsonl(
                self.gemini_log_file,
                {
                    "timestamp": started_at,
                    "completed_at": now_iso(),
                    "latency_ms": latency_ms,
                    "provider": "gemini",
                    "model": self.model,
                    "phase": "image-generation",
                    "agent": "agent_05_image_render",
                    "batch_id": batch_id,
                    "id": item_id,
                    "version": 0,
                    "http_status_code": 0,
                    "success": False,
                    "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                    "request": {
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "prompt_text": prompt,
                    },
                    "response_raw": "",
                    "response_text": "",
                    "usage_metadata": {},
                    "cost_estimate": self._cost_block(None, None, prompt, ""),
                    "error": f"Gemini network error: {e}",
                },
            )
            raise RuntimeError(f"Gemini network error: {e}") from e

        data = json.loads(raw_body)
        usage = data.get("usageMetadata", {}) if isinstance(data, dict) else {}
        candidates = data.get("candidates", [])
        if not candidates:
            latency_ms = int((time.time() - t0) * 1000)
            append_jsonl(
                self.gemini_log_file,
                {
                    "timestamp": started_at,
                    "completed_at": now_iso(),
                    "latency_ms": latency_ms,
                    "provider": "gemini",
                    "model": self.model,
                    "phase": "image-generation",
                    "agent": "agent_05_image_render",
                    "batch_id": batch_id,
                    "id": item_id,
                    "version": 0,
                    "http_status_code": status_code or 200,
                    "success": False,
                    "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                    "request": {
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "prompt_text": prompt,
                    },
                    "response_raw": raw_body,
                    "response_text": "",
                    "usage_metadata": usage,
                    "cost_estimate": self._cost_block(usage.get("promptTokenCount"), usage.get("candidatesTokenCount"), prompt, ""),
                    "error": "No candidates",
                },
            )
            raise RuntimeError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        image_parts: List[dict] = []
        text_parts: List[str] = []
        for part in parts:
            if "text" in part:
                text_parts.append(str(part.get("text", "")))
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                image_parts.append({"mime_type": inline.get("mimeType", "image/png"), "data_b64": inline.get("data", "")})

        response_text = "\n".join([t for t in text_parts if t]).strip()
        latency_ms = int((time.time() - t0) * 1000)
        append_jsonl(
            self.gemini_log_file,
            {
                "timestamp": started_at,
                "completed_at": now_iso(),
                "latency_ms": latency_ms,
                "provider": "gemini",
                "model": self.model,
                "phase": "image-generation",
                "agent": "agent_05_image_render",
                "batch_id": batch_id,
                "id": item_id,
                "version": 0,
                "http_status_code": status_code or 200,
                "success": True,
                "endpoint": f"{self.api_base}/models/{self.model}:generateContent",
                "request": {
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "prompt_text": prompt,
                },
                "response_raw": raw_body,
                "response_text": response_text,
                "usage_metadata": usage,
                "cost_estimate": self._cost_block(usage.get("promptTokenCount"), usage.get("candidatesTokenCount"), prompt, response_text),
                "error": "",
            },
        )
        time.sleep(self.delay_seconds)
        return image_parts, {"usage_metadata": usage, "response_text": response_text}


class ReplicateImageRenderer:
    def __init__(self, base: Path):
        self.base = base
        self.api_token = os.getenv("REPLICATE_API_TOKEN", "").strip()
        self.api_base = os.getenv("REPLICATE_API_BASE", "https://api.replicate.com/v1").strip()
        self.model = os.getenv("REPLICATE_MODEL", "black-forest-labs/flux-1.1-pro").strip()
        self.version = os.getenv("REPLICATE_VERSION", "11yss2r0gnrge0cjf05rk4np6r").strip()
        self.use_version = os.getenv("REPLICATE_USE_VERSION", "false").strip().lower() in {"1", "true", "yes", "y"}
        self.delay_seconds = float(os.getenv("REQUEST_DELAY_SECONDS", "0.6"))
        self.poll_seconds = float(os.getenv("REPLICATE_POLL_SECONDS", "1.5"))
        self.timeout_seconds = int(os.getenv("REPLICATE_TIMEOUT_SECONDS", "300"))
        self.aspect_ratio = os.getenv("REPLICATE_ASPECT_RATIO", "16:9").strip()
        self.output_format = os.getenv("REPLICATE_OUTPUT_FORMAT", "webp").strip()
        self.output_quality = int(os.getenv("REPLICATE_OUTPUT_QUALITY", "80"))
        self.safety_tolerance = int(os.getenv("REPLICATE_SAFETY_TOLERANCE", "2"))
        self.prompt_upsampling = os.getenv("REPLICATE_PROMPT_UPSAMPLING", "true").strip().lower() in {"1", "true", "yes", "y"}
        self.replicate_log_file = base / "data/logs/replicate_calls.jsonl"
        self.cost_per_image = float(os.getenv("REPLICATE_COST_PER_IMAGE_USD", "0.10"))

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, batch_id: str, item_id: str) -> Tuple[List[dict], dict]:
        started_at = now_iso()
        t0 = time.time()
        prediction_id = ""
        poll_count = 0
        create_http_status = 0
        final_http_status = 0
        create_body = ""
        final_body = ""
        status = ""
        error_text = ""

        create_payload = {
            "input": {
                "prompt": prompt,
                "aspect_ratio": self.aspect_ratio,
                "output_format": self.output_format,
                "output_quality": self.output_quality,
                "safety_tolerance": self.safety_tolerance,
                "prompt_upsampling": self.prompt_upsampling,
            },
        }
        if self.use_version and self.version:
            create_payload["version"] = self.version
            create_endpoint = f"{self.api_base}/predictions"
        else:
            create_endpoint = f"{self.api_base}/models/{self.model}/predictions"

        for _attempt in range(3):
            create_req = urllib.request.Request(
                create_endpoint,
                data=json.dumps(create_payload).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            try:
                with urllib.request.urlopen(create_req, timeout=120) as resp:
                    create_http_status = int(getattr(resp, "status", 200))
                    create_body = resp.read().decode("utf-8")
                    break
            except urllib.error.HTTPError as e:
                create_http_status = int(getattr(e, "code", 0) or 0)
                create_body = e.read().decode("utf-8", errors="replace")
                if create_http_status == 429:
                    retry_after = 5
                    try:
                        body_obj = json.loads(create_body)
                        retry_after = int(body_obj.get("retry_after", 5))
                    except Exception:
                        retry_after = 5
                    time.sleep(max(1, retry_after))
                    continue
                error_text = f"Replicate HTTP {create_http_status}"
                break
            except urllib.error.URLError as e:
                error_text = f"Replicate network error: {e}"
                break

        if not create_body and not error_text:
            error_text = f"Replicate create failed (HTTP {create_http_status})"

        data = {}
        if create_body:
            try:
                data = json.loads(create_body)
            except Exception:
                data = {}

        prediction_id = str(data.get("id", "")).strip()
        status = str(data.get("status", "")).strip()
        final_data = data

        if not error_text and prediction_id:
            prediction_url = f"{self.api_base}/predictions/{prediction_id}"
            while status in {"starting", "processing"}:
                if time.time() - t0 > self.timeout_seconds:
                    error_text = f"Replicate timeout after {self.timeout_seconds}s"
                    break
                time.sleep(self.poll_seconds)
                poll_count += 1
                poll_req = urllib.request.Request(prediction_url, headers=self._headers(), method="GET")
                try:
                    with urllib.request.urlopen(poll_req, timeout=120) as resp:
                        final_http_status = int(getattr(resp, "status", 200))
                        final_body = resp.read().decode("utf-8")
                except urllib.error.HTTPError as e:
                    final_http_status = int(getattr(e, "code", 0) or 0)
                    final_body = e.read().decode("utf-8", errors="replace")
                    error_text = f"Replicate poll HTTP {final_http_status}"
                    break
                except urllib.error.URLError as e:
                    error_text = f"Replicate poll network error: {e}"
                    break

                try:
                    final_data = json.loads(final_body)
                except Exception:
                    final_data = {}
                status = str(final_data.get("status", "")).strip()
                if status in {"failed", "canceled"}:
                    err = final_data.get("error")
                    error_text = f"Replicate prediction {status}: {err}" if err else f"Replicate prediction {status}"
                    break

            if status == "succeeded" and not error_text:
                final_data = final_data or data
            elif not error_text and status and status != "succeeded":
                error_text = f"Replicate terminal status: {status}"
        elif not error_text:
            error_text = "Replicate did not return prediction id"

        output_urls: List[str] = []
        if not error_text:
            out = final_data.get("output")
            if isinstance(out, str) and out:
                output_urls = [out]
            elif isinstance(out, list):
                output_urls = [str(x) for x in out if x]
            elif isinstance(out, dict) and out.get("url"):
                output_urls = [str(out.get("url"))]

            if not output_urls:
                error_text = "Replicate returned no output image URL"

        latency_ms = int((time.time() - t0) * 1000)
        append_jsonl(
            self.replicate_log_file,
            {
                "timestamp": started_at,
                "completed_at": now_iso(),
                "latency_ms": latency_ms,
                "provider": "replicate",
                "model": self.model,
                "version_id": self.version,
                "phase": "image-generation",
                "agent": "agent_05_image_render",
                "batch_id": batch_id,
                "id": item_id,
                "prediction_id": prediction_id,
                "poll_count": poll_count,
                "http_status_code": final_http_status or create_http_status,
                "success": not bool(error_text),
                "endpoint": create_endpoint,
                "request": {
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "prompt_text": prompt,
                    "payload": create_payload,
                },
                "response_raw": {
                    "create": create_body,
                    "final": final_body,
                },
                "response_text": status,
                "usage_metadata": {},
                "cost_estimate": {
                    "estimated_cost_usd": round(self.cost_per_image * len(output_urls), 8),
                    "cost_per_image_usd": self.cost_per_image,
                    "images_count": len(output_urls),
                    "estimated_by_heuristic": False,
                    "pricing_configured": self.cost_per_image > 0.0,
                },
                "error": error_text,
            },
        )

        if error_text:
            raise RuntimeError(error_text)

        time.sleep(self.delay_seconds)
        return [{"url": url} for url in output_urls], {"response_text": status, "usage_metadata": {}}


def render_from_csv(
    base: Path,
    csv_path: Path,
    provider: str = "gemini",
    overwrite: bool = False,
    limit: int = 0,
    validate_images: bool = True,
    max_attempts: int = 3,
) -> dict:
    if not csv_path.exists():
        raise SystemExit(f"CSV de prompts não encontrado: {csv_path}")

    rows = read_prompts(csv_path)
    if limit > 0:
        rows = rows[:limit]

    batch_id = parse_batch_id_from_filename(csv_path.name)
    out_dir = base / "outputs/generated-images" / batch_id
    batch_images_dir = base / "data/batches" / batch_id / "images"
    all_attempts_dir = out_dir / "_all_attempts"
    batch_attempts_dir = batch_images_dir / "_all_attempts"
    ensure_dir(out_dir)
    ensure_dir(batch_images_dir)
    ensure_dir(all_attempts_dir)
    ensure_dir(batch_attempts_dir)

    provider = (provider or "gemini").strip().lower()
    if provider == "replicate":
        renderer = ReplicateImageRenderer(base)
        if not renderer.api_token:
            raise SystemExit("REPLICATE_API_TOKEN não configurada no ambiente/.env")
    elif provider == "gemini":
        renderer = GeminiImageRenderer(base)
        if not renderer.api_key:
            raise SystemExit("GEMINI_API_KEY não configurada no ambiente/.env")
    else:
        raise SystemExit(f"Provider não suportado: {provider}. Use gemini|replicate")
    validator = GeminiImageValidator(base)
    if validate_images and validator.enabled and not validator.api_key:
        raise SystemExit("Validação de imagens ativa, mas GEMINI_API_KEY não está configurada.")

    def image_part_to_bytes(part: dict) -> Tuple[bytes, str, str]:
        if part.get("data_b64"):
            mime_type = part.get("mime_type", "image/png")
            ext = ext_from_mime(mime_type)
            img_bytes = base64.b64decode(part.get("data_b64", ""))
            return img_bytes, ext, mime_type
        if part.get("url"):
            ext = ext_from_url(str(part.get("url")), fallback=getattr(renderer, "output_format", "webp"))
            img_bytes = download_bytes(str(part.get("url")))
            mime = "image/webp" if ext == "webp" else ("image/jpeg" if ext == "jpg" else "image/png")
            return img_bytes, ext, mime
        raise RuntimeError("Formato de retorno de imagem não reconhecido")

    manifest_rows: List[dict] = []
    ok = 0
    fail = 0

    for row in rows:
        item_id = (row.get("id") or "").strip()
        if not item_id:
            continue
        article_title = (row.get("article_title") or "").strip()
        slug = (row.get("slug") or "").strip()
        prompt = (row.get("prompt") or "").strip()
        negative_prompt = (row.get("negative_prompt") or "").strip()
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}\n\nNegative prompt: {negative_prompt}"

        existing = list(out_dir.glob(f"{item_id}_*.png")) + list(out_dir.glob(f"{item_id}_*.jpg")) + list(out_dir.glob(f"{item_id}_*.webp"))
        if existing and not overwrite:
            manifest_rows.append(
                {
                    "id": item_id,
                    "article_title": article_title,
                    "slug": slug,
                    "status": "skipped_exists",
                    "images_saved": len(existing),
                    "primary_image": existing[0].name,
                    "output_dir": str(out_dir),
                    "error": "",
                }
            )
            continue

        try:
            attempts_used = 0
            validation_issues: List[str] = []
            final_parts: List[dict] = []
            last_generated_parts: List[dict] = []
            used_soft_fallback = False
            active_prompt = full_prompt

            for attempt in range(1, max(1, max_attempts) + 1):
                attempts_used = attempt
                image_parts, _meta = renderer.generate(active_prompt, batch_id=batch_id, item_id=item_id)
                if not image_parts:
                    raise RuntimeError("Modelo não retornou imagem")
                last_generated_parts = image_parts

                # Keep every generated attempt (for later manual/automated curation).
                for idx, part in enumerate(image_parts, start=1):
                    try:
                        img_bytes_attempt, ext_attempt, _mime_attempt = image_part_to_bytes(part)
                        attempt_name = f"{item_id}_a{attempt:02d}_{idx:02d}.{ext_attempt}"
                        (all_attempts_dir / attempt_name).write_bytes(img_bytes_attempt)
                        (batch_attempts_dir / attempt_name).write_bytes(img_bytes_attempt)
                    except Exception:
                        pass

                if not validate_images:
                    final_parts = image_parts
                    break

                first_bytes, _first_ext, first_mime = image_part_to_bytes(image_parts[0])
                keyword = (row.get("keyword_primaria") or "").strip()
                verdict = validator.validate(
                    image_bytes=first_bytes,
                    mime_type=first_mime,
                    batch_id=batch_id,
                    item_id=item_id,
                    article_title=article_title,
                    keyword=keyword,
                    prompt_used=active_prompt,
                )

                if verdict.get("pass"):
                    final_parts = image_parts
                    validation_issues = verdict.get("issues") or []
                    break

                validation_issues = verdict.get("issues") or []
                correction = str(verdict.get("correction_prompt", "")).strip()
                correction_chunks: List[str] = []
                if correction:
                    correction_chunks.append(correction)
                if attempt >= 2:
                    correction_chunks.append(
                        "Switch to safe scene: executive team in strategy room, human-focused composition, "
                        "non-readable abstract data lights only, no text-like UI, no dashboards with numbers, "
                        "no vehicle front grilles, no badges, no logos, no plates, no documents, no signage."
                    )
                correction_chunks.append(
                    "Hard requirement: absolutely no readable text, logos, UI labels, signs, plates, "
                    "watermark, or brand marks. Avoid landscape-only scenes."
                )
                active_prompt = (
                    f"{full_prompt}\n\nCritical correction for retry:\n"
                    + "\n".join(correction_chunks)
                )

            if not final_parts:
                if last_generated_parts:
                    # Soft fallback: keep the best effort generated image instead of dropping the post.
                    final_parts = last_generated_parts
                    used_soft_fallback = True
                else:
                    raise RuntimeError(
                        "Imagem reprovada na validação automática após "
                        f"{attempts_used} tentativas. Issues: {', '.join(validation_issues[:5])}"
                    )

            saved_files = []
            for idx, part in enumerate(final_parts, start=1):
                img_bytes, ext, _mime = image_part_to_bytes(part)
                fname = f"{item_id}_{idx:02d}.{ext}"
                p1 = out_dir / fname
                p2 = batch_images_dir / fname
                p1.write_bytes(img_bytes)
                p2.write_bytes(img_bytes)
                saved_files.append(fname)

            manifest_rows.append(
                {
                    "id": item_id,
                    "article_title": article_title,
                    "slug": slug,
                    "status": "success_soft" if used_soft_fallback else "success",
                    "images_saved": len(saved_files),
                    "primary_image": saved_files[0],
                    "output_dir": str(out_dir),
                    "attempts_used": attempts_used,
                    "validation_issues": " | ".join(validation_issues[:5]),
                    "error": "",
                }
            )
            ok += 1
        except Exception as e:
            manifest_rows.append(
                {
                    "id": item_id,
                    "article_title": article_title,
                    "slug": slug,
                    "status": "failed",
                    "images_saved": 0,
                    "primary_image": "",
                    "output_dir": str(out_dir),
                    "attempts_used": attempts_used if "attempts_used" in locals() else 0,
                    "validation_issues": " | ".join(validation_issues[:5]) if "validation_issues" in locals() else "",
                    "error": str(e),
                }
            )
            fail += 1

    manifest_csv = out_dir / f"{batch_id}_images_manifest.csv"
    write_csv(
        manifest_csv,
        manifest_rows,
        [
            "id",
            "article_title",
            "slug",
            "status",
            "images_saved",
            "primary_image",
            "output_dir",
            "attempts_used",
            "validation_issues",
            "error",
        ],
    )

    summary = {
        "batch_id": batch_id,
        "csv": str(csv_path),
        "provider": provider,
        "total_prompts": len(rows),
        "success": ok,
        "failed": fail,
        "manifest_csv": str(manifest_csv),
        "images_dir": str(out_dir),
    }
    return summary


def latest_prompt_csv(base: Path) -> Path:
    prompts_dir = base / "outputs/image-prompts"
    files = sorted(prompts_dir.glob("BATCH-*_image_prompts.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise SystemExit(f"Nenhum CSV encontrado em: {prompts_dir}")
    return files[0]


def main():
    parser = argparse.ArgumentParser(description="Render images from image-prompts CSV")
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]), help="Project root")
    parser.add_argument("--csv", default="", help="CSV específico de prompts")
    parser.add_argument("--latest", action="store_true", help="Usar CSV mais recente de outputs/image-prompts")
    parser.add_argument("--all", action="store_true", help="Processar todos os CSVs em outputs/image-prompts")
    parser.add_argument("--provider", default=os.getenv("IMAGE_PROVIDER", "gemini"), help="Provider: gemini|replicate")
    parser.add_argument("--overwrite", action="store_true", help="Sobrescrever imagens existentes")
    parser.add_argument("--limit", type=int, default=0, help="Limitar quantidade de prompts por CSV")
    parser.add_argument("--no-validate", action="store_true", help="Desligar validação automática de imagem")
    parser.add_argument("--max-attempts", type=int, default=int(os.getenv("IMAGE_VALIDATION_MAX_ATTEMPTS", "3")), help="Máximo de tentativas de geração por prompt")
    args = parser.parse_args()

    base = Path(args.base).resolve()
    load_env_file(base / ".env")
    load_env_file(base.parent / ".env")

    csv_paths: List[Path] = []
    if args.all:
        csv_paths = sorted((base / "outputs/image-prompts").glob("BATCH-*_image_prompts.csv"))
    elif args.csv:
        p = Path(args.csv)
        if not p.is_absolute():
            p = (base / args.csv).resolve()
        csv_paths = [p]
    else:
        # default to latest for convenience
        csv_paths = [latest_prompt_csv(base)]

    results = []
    for csv_path in csv_paths:
        results.append(
            render_from_csv(
                base,
                csv_path,
                provider=args.provider,
                overwrite=args.overwrite,
                limit=args.limit,
                validate_images=(not args.no_validate),
                max_attempts=args.max_attempts,
            )
        )

    print(json.dumps({"runs": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
