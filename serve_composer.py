"""Run Hex Path Composer locally so Export SVG can write each export into its own folder.

    python serve_composer.py                         # saves into ./exports
    python serve_composer.py --exports "D:/hex/exports" --port 9000 --no-browser

Every press of Export SVG creates a new folder <exports>/<date>_<cols>x<rows>_seed<seed>/; if that name is
taken, _2, _3 … is added, so nothing is ever overwritten. The exports folder can sit outside the repo
(--exports or the HEX_EXPORTS environment variable). Each folder holds:
    hex_paths.svg   paths and their offset copies only, 1:1 scale (1 unit = 1 mm), 0.5 mm lines
    layout.svg      the whole board: cell outlines, lit tiles, paths, open ends, numbers
    config.json     grid size, seed, options, lit cells and every tile's number and lines
  plus, with Save all files:
    hex_tiles.dxf   tile outlines + paths as true arcs
    tiles.csv       one row per placed tile
Only listens on 127.0.0.1. Stop it with Ctrl+C.
"""
import argparse
import json
import os
import re
import socket
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{1,2}x\d{1,2}_seed\d{1,7}$")
ALLOWED_FILES = {"hex_paths.svg", "layout.svg", "config.json", "hex_tiles.dxf", "tiles.csv"}
MAX_BYTES = 50 * 1024 * 1024


class Handler(SimpleHTTPRequestHandler):
    exports = os.path.join(ROOT, "exports")

    def do_POST(self):
        if self.path != "/save":
            return self.reply(404, {"error": "Unknown address"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BYTES:
            return self.reply(413, {"error": "Request is empty or too large"})
        try:
            body = json.loads(self.rfile.read(length))
            folder, files = body["folder"], body["files"]
        except (ValueError, KeyError, TypeError):
            return self.reply(400, {"error": "Request is not valid JSON with folder and files"})
        if not isinstance(folder, str) or not FOLDER_RE.match(folder):
            return self.reply(400, {"error": f"Folder name {folder!r} is not date_gridsize_seed"})
        if not isinstance(files, dict) or not files or not set(files) <= ALLOWED_FILES:
            return self.reply(400, {"error": "Unexpected file names"})
        os.makedirs(self.exports, exist_ok=True)
        target, n = os.path.join(self.exports, folder), 1
        while True:  # a fresh folder for every save
            try:
                os.mkdir(target)
                break
            except FileExistsError:
                n += 1
                target = os.path.join(self.exports, f"{folder}_{n}")
        for name, text in files.items():
            with open(os.path.join(target, name), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(str(text))
        rel = target.replace(os.sep, "/") + "/"
        print(f"saved {rel} ({', '.join(sorted(files))})", flush=True)
        return self.reply(200, {"path": rel})

    def end_headers(self):  # always serve the page as it is on disk, never a cached copy
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def reply(self, code, data):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):  # keep the console to saves and errors
        if args and str(args[1]) >= "400":
            super().log_message(fmt, *args)


class Server(ThreadingHTTPServer):
    # Windows lets several servers share a port when address reuse is on, and requests then reach any of
    # them. Take the port exclusively so the page and its saves always come from this process.
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    ap.add_argument("--exports", default=os.environ.get("HEX_EXPORTS", os.path.join(ROOT, "exports")),
                    help="folder that receives the export folders (default: ./exports beside this script)")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    Handler.exports = os.path.abspath(args.exports)
    handler = partial(Handler, directory=ROOT)
    for port in range(args.port, args.port + 20):  # the next free port if this one is taken
        try:
            server = Server(("127.0.0.1", port), handler)
            break
        except OSError:
            print(f"Port {port} is in use by another program, trying {port + 1}", flush=True)
    else:
        raise SystemExit(f"No free port between {args.port} and {args.port + 19}")
    url = f"http://localhost:{port}/hex-path-composer.html"
    print(f"Hex Path Composer at {url}\nSaving into {Handler.exports}\nPress Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
