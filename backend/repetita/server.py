from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .api import analyse_payload, model_family_payload, safe_pass_payload

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
SAMPLE_PATH = PROJECT_ROOT / "sample-data" / "adversarial-professional.md"


class RepetitaHandler(BaseHTTPRequestHandler):
    server_version = "RepetitaGravity/0.1"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid Content-Length") from error
        if length <= 0 or length > 5_100_000:
            raise ValueError("Request body is empty or too large")
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ValueError("Request body is not valid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok", "service": "repetita-gravity"})
            return
        if path == "/api/sample":
            self._json(HTTPStatus.OK, {"text": SAMPLE_PATH.read_text(encoding="utf-8")})
            return
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (FRONTEND_ROOT / relative).resolve()
        if FRONTEND_ROOT.resolve() not in target.parents and target != FRONTEND_ROOT.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        handlers = {
            "/api/analyse": analyse_payload,
            "/api/safe-pass": safe_pass_payload,
            "/api/model-family": model_family_payload,
        }
        handler = handlers.get(path)
        if handler is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
            return
        try:
            self._json(HTTPStatus.OK, handler(self._read_json()))
        except ValueError as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:  # Fail closed at the HTTP boundary.
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Processing failed: {error}"})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Repetita Gravity MVP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), RepetitaHandler)
    print(f"Repetita Gravity listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
