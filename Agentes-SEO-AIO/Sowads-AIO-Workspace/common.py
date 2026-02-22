import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def load_env_file(path: str) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def extract_first_json_array(raw_text: str):
    start = raw_text.find("[")
    end = raw_text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Nao encontrei array JSON valido na resposta.")
    candidate = raw_text[start : end + 1]
    return json.loads(candidate)


def extract_first_json_object(raw_text: str):
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Nao encontrei objeto JSON valido na resposta.")
    candidate = raw_text[start : end + 1]
    return json.loads(candidate)


class GeminiClient:
    def __init__(self, model_env_key: str):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.api_base = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").strip()
        self.model = os.getenv(model_env_key, "gemini-2.5-flash").strip()
        self.delay_seconds = float(os.getenv("REQUEST_DELAY_SECONDS", "0.6"))

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY nao configurada. Defina no ambiente ou no .env.local.")

    def generate_text(self, prompt: str, temperature: float = 0.5) -> str:
        endpoint = f"{self.api_base}/models/{self.model}:generateContent?key={urllib.parse.quote(self.api_key)}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Erro HTTP Gemini ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Erro de rede Gemini: {exc}") from exc

        parsed = json.loads(body)
        candidates = parsed.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Resposta Gemini sem candidates: {body}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
        if not text:
            raise RuntimeError(f"Resposta Gemini sem texto: {body}")

        time.sleep(self.delay_seconds)
        return text
