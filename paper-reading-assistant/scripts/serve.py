#!/usr/bin/env python3
"""
serve.py — Local web server for the reading-assistant repo.

Two jobs:
  1. Serve the repo's files (so reports open at http://localhost:PORT/...
     instead of file://, which lets notes save to disk and lets demos run).
  2. Persist notes: the report's editor calls this API, and it writes
     plain Markdown to papers/<slug>/notes.md inside the repo.

API:
  GET  /api/notes?slug=<slug>   -> returns papers/<slug>/notes.md (text), 200 or 404
  POST /api/notes?slug=<slug>   -> body is the note text; writes papers/<slug>/notes.md
  GET  /                         -> an index of every paper in papers/
  GET  /<anything else>          -> static file from the repo root

Run from the repo root:
    python paper-reading-assistant/scripts/serve.py            # port 8000
    python paper-reading-assistant/scripts/serve.py --port 8080

Notes are committed with the repo, so they travel with it and survive.
Slugs are sanitized to a single path segment to prevent directory traversal.
"""

import argparse
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Repo root = two levels up from this script (scripts/ -> skill/ -> repo root).
REPO_ROOT = Path(__file__).resolve().parents[2]
PAPERS_DIR = REPO_ROOT / "papers"


def safe_slug(slug: str) -> str:
    """Reduce a slug to one safe path segment (no traversal, no separators)."""
    slug = (slug or "").strip()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-.")
    return slug[:80] or "paper"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    # ---- notes API -------------------------------------------------------

    def _notes_path(self, query) -> Path:
        slug = safe_slug((parse_qs(query).get("slug") or [""])[0])
        return PAPERS_DIR / slug / "notes.md"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/notes":
            path = self._notes_path(parsed.query)
            if path.exists():
                body = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()
            return
        if parsed.path == "/":
            return self._send_index()
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/notes":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            path = self._notes_path(parsed.query)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self.end_headers()

    # ---- index of papers -------------------------------------------------

    def _send_index(self):
        rows = []
        if PAPERS_DIR.exists():
            for d in sorted(PAPERS_DIR.iterdir()):
                if not d.is_dir():
                    continue
                report = d / "report.html"
                has_notes = (d / "notes.md").exists()
                link = (f'<a href="/papers/{d.name}/report.html">{d.name}</a>'
                        if report.exists() else d.name)
                rows.append(f"<li>{link} {'📝' if has_notes else ''}</li>")
        listing = "".join(rows) or "<li><em>No papers yet. Add one with new_paper.py.</em></li>"
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Reading Assistant — papers</title>
<style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:48px auto;padding:0 20px;color:#1a1a1a}}
h1{{font-size:24px}} li{{margin:8px 0}} a{{color:#2d4a8a}}</style></head>
<body><h1>Reading Assistant</h1><p>Papers in this repo:</p><ul>{listing}</ul></body></html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # quieter console


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Serving {REPO_ROOT} at http://localhost:{args.port}")
    print(f"  Index:  http://localhost:{args.port}/")
    print("  Ctrl-C to stop. Notes save to papers/<slug>/notes.md")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
