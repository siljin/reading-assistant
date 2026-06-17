#!/usr/bin/env python3
"""
new_paper.py — Scaffold a per-paper folder inside the repo.

Everything about one paper lives together under papers/<slug>/ so it travels
with the repo: the source, the analysis JSON, the rendered HTML report, and the
persistent notes.

    papers/<slug>/
      paper.pdf            (you drop the PDF here, if you have one)
      source.md            (or paste text / a link here)
      analysis.json        (the agent fills this; see analysis.template.json)
      report.html          (render_report.py writes this)
      notes.md             (your notes; serve.py keeps this in sync)

Usage:
    python paper-reading-assistant/scripts/new_paper.py \\
        --title "Attention Is All You Need" [--slug attention]

Prints the slug and the folder path. Safe to re-run; never clobbers existing files.
"""

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAPERS_DIR = REPO_ROOT / "papers"

ANALYSIS_TEMPLATE = {
    "paper": {
        "title": "",
        "authors": [],
        "affiliations": [],
        "venue": "",
        "year": None,
        "url": "",
        "code_url": "",
        "data_url": None,
    },
    "slug": "",
    "headline": "",
    "eli5": {"analogy": "", "text": ""},
    "plain_summary": "",
    "glossary": [{"term": "", "plain": ""}],
    "figures": [],
    "demos": [],
    "novelty": {"type": "", "before": "", "after": ""},
    "methods": "",
    "results": [{"claim": "", "evidence": "", "caveat": ""}],
    "limitations": {"stated": [], "unstated": []},
    "implementation": {"feasibility": "", "requirements": [], "cheapest_validation": ""},
    "implications": {"research": [], "practice": [], "personal": []},
    "knowledge_graph": {"nodes": [], "edges": []},
    "people": [],
}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or "paper"


def write_if_absent(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--slug", default=None)
    args = ap.parse_args()

    slug = args.slug or slugify(args.title)
    folder = PAPERS_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)

    tmpl = json.loads(json.dumps(ANALYSIS_TEMPLATE))
    tmpl["paper"]["title"] = args.title
    tmpl["slug"] = slug

    created = []
    if write_if_absent(folder / "analysis.template.json",
                        json.dumps(tmpl, indent=2, ensure_ascii=False)):
        created.append("analysis.template.json")
    if write_if_absent(folder / "source.md",
                        f"# Source: {args.title}\n\n"
                        "Paste the paper text, a link, or notes about where the "
                        "PDF lives here. Or drop `paper.pdf` in this folder.\n"):
        created.append("source.md")
    if write_if_absent(folder / "notes.md", f"# Notes — {args.title}\n\n"):
        created.append("notes.md")

    print(f"slug: {slug}")
    print(f"folder: {folder}")
    print(f"created: {', '.join(created) if created else '(all files already existed)'}")
    print("\nNext: fill analysis.template.json -> analysis.json, then render:")
    print(f"  python paper-reading-assistant/scripts/render_report.py \\")
    print(f"    --input papers/{slug}/analysis.json \\")
    print(f"    --output papers/{slug}/report.html --slug {slug}")


if __name__ == "__main__":
    main()
