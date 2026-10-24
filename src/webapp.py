"""Loopback-only synthetic Safety Shift Navigator UI; no live service by default."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .safety_shift import InputError, fixture, live_triage, offline_triage, validate_case
from .handoff_agent import handoff_catalogue, live_handoff, offline_handoff

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    "/": (ROOT / "web" / "index.html", "text/html; charset=utf-8"),
    "/app.js": (ROOT / "web" / "app.js", "text/javascript; charset=utf-8"),
    "/style.css": (ROOT / "web" / "style.css", "text/css; charset=utf-8"),
}
MAX_BYTES = 4096
POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "connect-src 'self'; img-src 'self'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'none'"
)


class Handler(BaseHTTPRequestHandler):
    server_version = "SafetyShiftLocal/1.0"
    sys_version = ""

    def log_message(self, fmt, *args):
        # Do not echo case text, origins, raw URLs, or model responses to logs.
        return

    def _reply(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", POLICY)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: dict):
        self._reply(status, json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _allowed_host(self):
        port=self.server.server_port
        return self.headers.get("Host","") in (
            f"127.0.0.1:{port}",f"localhost:{port}")

    def do_GET(self):
        if not self._allowed_host():
            self._json(403,{"error":"HOST_DENIED"})
            return
        url=urllib.parse.urlsplit(self.path)
        if url.scheme or url.netloc or len(self.path)>2048:
            self._json(400,{"error":"INVALID_LOCAL_URL"})
            return
        path=url.path
        if url.query and path.startswith("/api/"):
            self._json(400,{"error":"API_QUERY_DENIED"})
            return
        if path == "/api/handoffs":
            self._json(200,{
                "scenarios":handoff_catalogue(),
                "provider_ready":bool(os.environ.get("NEBIUS_API_KEY")
                    and os.environ.get("NEBIUS_SANDBOX_ZERO_SPEND_APPROVED")=="YES"),
                "source_truth":"ORIGINAL_SYNTHETIC_RUNBOOK_AND_SIGNALS",
                "model":"nvidia/Nemotron-3_5-Lightning",
                "real_calls":0,
            })
            return
        if path == "/api/fixture":
            self._json(200, {"case": fixture(), "provenance": "SYNTHETIC_FIXTURE_ONLY"})
            return
        if path not in ASSETS:
            self._json(404, {"error": "NOT_FOUND"})
            return
        file_path, content_type = ASSETS[path]
        self._reply(200, file_path.read_bytes(), content_type)

    def do_POST(self):
        if not self._allowed_host():
            self._json(403,{"error":"HOST_DENIED"})
            return
        if self.path not in {"/api/triage","/api/handoff"}:
            self._json(404, {"error": "NOT_FOUND"})
            return
        origin = self.headers.get("Origin", "")
        if origin not in ("", "http://127.0.0.1:" + str(self.server.server_port),
                          "http://localhost:" + str(self.server.server_port)):
            self._json(403, {"error": "ORIGIN_DENIED"})
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            self._json(415, {"error": "JSON_ONLY"})
            return
        size = self.headers.get("Content-Length", "")
        if not size.isdecimal() or not (1 <= int(size) <= MAX_BYTES):
            self._json(413, {"error": "BODY_SIZE_DENIED"})
            return
        body = self.rfile.read(int(size))
        try:
            inp = json.loads(body)
            if not isinstance(inp, dict):
                raise InputError("request object required")
            if self.path=="/api/handoff":
                if set(inp)!={"mode","scenario_id"}:
                    raise InputError("handoff fields must be fixed")
                if inp["mode"]=="synthetic":
                    out=offline_handoff(inp["scenario_id"])
                elif inp["mode"]=="provider":
                    out=live_handoff(inp["scenario_id"])
                else:
                    raise InputError("unsupported provider mode")
                self._json(200,out)
                return
            if set(inp)!={"mode","case"}:
                raise InputError("triage fields must be fixed")
            case = validate_case(inp["case"])
            if inp["mode"] == "synthetic":
                out = offline_triage(case)
            elif inp["mode"] == "provider":
                # Never runs without a separate no-spend approval environment gate.
                out = live_triage(case)
            else:
                raise InputError("unknown mode")
        except (InputError, ValueError, TypeError):
            self._json(422, {"error": "INVALID_OR_BLOCKED_INPUT"})
            return
        # Provider secrets are never echoed; usage is only the provider's usage metadata.
        self._json(200, out)

    def do_OPTIONS(self):
        self._json(405, {"error": "CORS_NOT_SUPPORTED"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8878)
    args = ap.parse_args()
    if not (1024 <= args.port <= 65535):
        ap.error("choose a loopback port between 1024 and 65535")
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print("SAFETY_SHIFT_LOCAL_UI=http://127.0.0.1:" + str(args.port), flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
