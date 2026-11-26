"""Lightweight web server for Hex Path Composer (local PC or home NAS).

Serves hex-path-composer.html (at /) and hex-path-tiles.html (at /tiles) and
provides POST /api/export so any browser on your network can save cut-ready
exports directly into <DATA_ROOT>/exports/<date>_<cols>x<rows>_seed<seed>/.

DATA_ROOT resolution order (Method in the Cloud, Data at Local):
  1. --data-dir CLI flag
  2. HEX_DATA_DIR environment variable
  3. ~/.config/hex-path-tiles/config.json  ({"data_dir": "..."})
  4. ./data beside this script (git-ignored)

Usage:
  python server.py                          # http://127.0.0.1:8765
  python server.py --host 0.0.0.0           # accessible on your home LAN / NAS
  python server.py --data-dir /path/to/data # custom DATA_ROOT
"""
import argparse
import json
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
USER_CONFIG = Path.home() / ".config" / "hex-path-tiles" / "config.json"
FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[A-Za-z0-9_-]{3,64}$")
ALLOWED_FILES = {"hex_paths.svg", "layout.svg", "config.json", "tiles.csv", "hex_tiles.dxf"}
MAX_BYTES = 50 * 1024 * 1024


def resolve_data_root(cli_dir=None):
    """Resolve DATA_ROOT following CLI -> env -> user config -> local fallback."""
    if cli_dir:
        return Path(cli_dir).expanduser().resolve()
    env_dir = os.environ.get("HEX_DATA_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    if USER_CONFIG.is_file():
        try:
            cfg = json.loads(USER_CONFIG.read_text(encoding="utf-8"))
            if cfg.get("data_dir"):
                return Path(cfg["data_dir"]).expanduser().resolve()
        except (OSError, ValueError):
            pass
    return (ROOT / "data").resolve()


class LocalStorageProvider:
    """Writes non-overwriting export folders under <DATA_ROOT>/exports/."""

    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.exports_dir = data_root / "exports"

    def save_export(self, folder_name: str, files: dict[str, str]) -> dict:
        if not isinstance(folder_name, str) or not FOLDER_RE.match(folder_name):
            raise ValueError(f"Invalid folder name: {folder_name!r}")
        if not isinstance(files, dict) or not files or not set(files) <= ALLOWED_FILES:
            raise ValueError("Unexpected or empty file set")

        self.exports_dir.mkdir(parents=True, exist_ok=True)
        n = 1
        while True:
            name = folder_name if n == 1 else f"{folder_name}_{n}"
            target = self.exports_dir / name
            try:
                target.mkdir(exist_ok=False)
                break
            except FileExistsError:
                n += 1

        for fname, content in files.items():
            (target / fname).write_text(str(content), encoding="utf-8", newline="\n")

        return {
            "ok": True,
            "folder": name,
            "path": f"exports/{name}/",
            "files": sorted(files.keys()),
        }


class ComposerHandler(SimpleHTTPRequestHandler):
    storage: LocalStorageProvider = None

    def _send_json(self, code: int, payload: dict):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/status":
            return self._send_json(200, {
                "ok": True,
                "mode": "server",
                "exports": "exports/",
            })
        if path == "/":
            self.path = "/hex-path-composer.html"
        elif path in ("/tiles", "/tiles/"):
            self.path = "/hex-path-tiles.html"
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/export":
            return self._send_json(404, {"ok": False, "error": "Not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BYTES:
            return self._send_json(413, {"ok": False, "error": "Request empty or too large"})
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self.storage.save_export(body.get("folder", ""), body.get("files", {}))
            print(f"[export] saved {result['path']} ({', '.join(result['files'])})", flush=True)
            return self._send_json(200, result)
        except ValueError as exc:
            return self._send_json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            return self._send_json(500, {"ok": False, "error": str(exc)})

    def log_message(self, fmt, *args):
        if args and str(args[1]) >= "400":
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description="Serve Hex Path Composer for local or home NAS use.")
    ap.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"),
                    help="Bind address (default: 127.0.0.1; use 0.0.0.0 for LAN / NAS)")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")),
                    help="Port to listen on (default: 8765)")
    ap.add_argument("--data-dir", default=None,
                    help="External DATA_ROOT folder (exports go into <DATA_ROOT>/exports/)")
    args = ap.parse_args()

    data_root = resolve_data_root(args.data_dir)
    ComposerHandler.storage = LocalStorageProvider(data_root)
    handler = partial(ComposerHandler, directory=str(ROOT))
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print(f"Hex Path Composer serving at http://{args.host}:{args.port}/", flush=True)
    print(f"3D Tile Viewer at          http://{args.host}:{args.port}/tiles", flush=True)
    print(f"Saving exports into        {ComposerHandler.storage.exports_dir}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    main()
