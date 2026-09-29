"""盤中即時市值服務 v1.0.0（常駐於 Mac Studio，由 launchd 啟動）

- 只監聽 127.0.0.1:8765，對外由 `tailscale serve` 以 HTTPS 提供給同一個 Tailscale 網路內的裝置。
- GET /api/live    → 即時市值（快取 60 秒，避免過度查詢）
- GET /api/health  → 健康檢查
- 允許 GitHub Pages 網址跨來源讀取（CORS + Private Network Access）。
"""
from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marketcap as mc  # noqa: E402

HOST, PORT = "127.0.0.1", 8765
CACHE_SECONDS = 60
FX_CACHE_SECONDS = 600
ALLOWED_ORIGINS = {
    "https://ctwu2012-timwu.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}

_lock = threading.Lock()
_cache = {"at": 0.0, "data": None}
_fx_cache = {"at": 0.0, "data": None}


def get_live() -> dict:
    with _lock:
        if _cache["data"] and time.time() - _cache["at"] < CACHE_SECONDS:
            return _cache["data"]
        cfg = mc.load_config()
        if not _fx_cache["data"] or time.time() - _fx_cache["at"] > FX_CACHE_SECONDS:
            _fx_cache["data"], _fx_cache["at"] = mc.get_fx(cfg), time.time()
        fx = _fx_cache["data"]
        quotes, errors = {}, {}
        for u in cfg["units"]:
            try:
                quotes[u["code"]] = mc.fetch_quote(u)
            except Exception as e:  # noqa: BLE001
                errors[u["code"]] = str(e)
        stamp = mc.now_tpe().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "generated": stamp, "mode": "live", "source": "Mac Studio",
            "fx": {k: v for k, v in fx.items() if k != "TWD"},
            "rows": mc.build_rows(cfg, fx, quotes, stamp, "live"),
            "errors": errors,
        }
        _cache["data"], _cache["at"] = data, time.time()
        return data


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path == "/api/health":
            return self._json(200, {"ok": True, "time": mc.now_tpe().isoformat()})
        if path == "/api/live":
            try:
                return self._json(200, get_live())
            except Exception as e:  # noqa: BLE001
                return self._json(500, {"error": str(e)})
        return self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (mc.now_tpe().strftime("%m-%d %H:%M:%S"), fmt % args))


if __name__ == "__main__":
    print(f"live server on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
