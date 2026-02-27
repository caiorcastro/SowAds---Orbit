#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agent_status import build_status


def make_handler(base: Path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/status":
                qs = parse_qs(parsed.query)
                batch_id = (qs.get("batch", [""])[0] or "").strip()
                payload = build_status(base=base, batch_id=batch_id)
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._send(200, raw, "application/json; charset=utf-8")
                return

            if parsed.path in ("/", "/index.html"):
                html_path = Path(__file__).resolve().parent / "agent_status_dashboard.html"
                raw = html_path.read_bytes()
                self._send(200, raw, "text/html; charset=utf-8")
                return

            self._send(404, b"not found", "text/plain; charset=utf-8")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve live SOWADS agent status dashboard")
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    base = Path(args.base).resolve()
    handler = make_handler(base)
    server = HTTPServer((args.host, int(args.port)), handler)
    print(f"Serving status dashboard on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

