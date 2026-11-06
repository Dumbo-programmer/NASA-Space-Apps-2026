"""
Agnishikha prediction API. Standard library only, so it runs wherever the models run.

    python api/server.py                      # http://127.0.0.1:8000
    python api/server.py --host 0.0.0.0 --port 8000

Endpoints (JSON in, JSON out):
    GET  /health                   status and model versions
    GET  /models                   every model: inputs with NASA-tested ranges, scores, source
    GET  /models/{name}            one model card
    POST /predict/{name}           {"fuel": "Methanol", "o2_pct": 21, ...}  (missing inputs take defaults;
                                   add "explain": false to skip the Shapley breakdown)
    POST /sweep/{name}             {"vary": "co2_pct", "inputs": {...}, "points": 21, "extend": 0.15}

Errors: 404 unknown model or path, 413 body too large, 400 bad JSON, 422 invalid input.
CORS: allowed origins come from IGNIS_ALLOWED_ORIGINS (comma-separated, default "*").
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ignis_api as A  # noqa: E402

MAX_BODY = 64 * 1024
ALLOWED = [o.strip() for o in os.environ.get("IGNIS_ALLOWED_ORIGINS", "*").split(",") if o.strip()]


class Handler(BaseHTTPRequestHandler):
    server_version = "Agnishikha/" + A.API_VERSION
    quiet = False

    # ---------- plumbing ----------
    def _cors(self):
        origin = self.headers.get("Origin")
        if "*" in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, status, payload):
        body = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message):
        self._send(status, {"error": message, "status": status})

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            return None, (413, f"request body must be at most {MAX_BODY} bytes")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}"), None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, (400, "request body is not valid JSON")

    def log_message(self, fmt, *args):
        if not self.quiet:
            sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _route(self):
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        return parts

    # ---------- verbs ----------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parts = self._route()
        try:
            if parts in ([], ["health"]):
                return self._send(200, A.health())
            if parts == ["models"]:
                return self._send(200, A.catalog())
            if len(parts) == 2 and parts[0] == "models":
                return self._send(200, A.model_card(parts[1]))
        except KeyError:
            return self._error(404, f"unknown model; available: {A.MODEL_NAMES}")
        except Exception as e:  # never leak a traceback to the client
            self.log_message("GET %s failed: %r", self.path, e)
            return self._error(500, "internal error")
        return self._error(404, "unknown path; see GET /models")

    def do_POST(self):
        parts = self._route()
        if len(parts) != 2 or parts[0] not in ("predict", "sweep"):
            return self._error(404, "use POST /predict/{model} or POST /sweep/{model}")
        body, err = self._body()
        if err:
            return self._error(*err)
        try:
            fn = A.predict if parts[0] == "predict" else A.sweep
            return self._send(200, fn(parts[1], body))
        except KeyError:
            return self._error(404, f"unknown model; available: {A.MODEL_NAMES}")
        except A.InputError as e:
            return self._error(422, str(e))
        except Exception as e:
            self.log_message("POST %s failed: %r", self.path, e)
            return self._error(500, "internal error")


def make_server(host="127.0.0.1", port=8000, quiet=False):
    Handler.quiet = quiet
    for n in A.MODEL_NAMES:      # load every bundle once at start-up, so the first request is fast
        A._bundle(n)
    return ThreadingHTTPServer((host, port), Handler)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    a = ap.parse_args()
    srv = make_server(a.host, a.port)
    print(f"Agnishikha API {A.API_VERSION} on http://{a.host}:{a.port}  (models: {', '.join(A.MODEL_NAMES)})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
