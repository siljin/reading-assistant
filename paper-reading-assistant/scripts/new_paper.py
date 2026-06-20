#!/usr/bin/env python3
"""
new_paper.py — Scaffold a per-paper folder inside the repo.

Everything about one paper lives together under papers/<slug>/ so it travels
with the repo: the source, the structured analysis JSON, and the rendered HTML
report.

    papers/<slug>/
      paper.pdf            (you drop the PDF here, if you have one)
      source.md            (or paste text / a link here)
      analysis.json        (the agent fills this)
      report.html          (render_report.py writes this)

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
    "insight_dashboard": {
        "cards": [{"label": "", "value": "", "caption": ""}],
        "primary_visuals": [],
    },
    "evidence_profile": {
        "claims": [{"claim": "", "support": 0, "risk": 0, "caption": ""}],
    },
    "so_what": {
        "research": {
            "headline": "",
            "implications": [],
            "open_questions": [],
            "next_actions": [],
        },
        "product": {
            "headline": "",
            "opportunities": [],
            "guardrails": [],
            "next_actions": [],
        },
        "business": {
            "headline": "",
            "market_openings": [],
            "adoption_blockers": [],
            "risks": [],
            "next_actions": [],
        },
    },
    "opportunity_matrix": {
        "x_axis": "Feasibility",
        "y_axis": "Strategic value",
        "columns": [],
        "rows": [],
        "cells": [],
    },
    "report_plan": {
        "paper_archetype": "",
        "reader_goal": "",
        "narrative_arc": [],
        "sections": [
            {
                "type": "problem_context",
                "title": "",
                "takeaway": "",
                "content": "",
                "visuals": [],
                "caveats": [],
            },
            {
                "type": "learning_path",
                "title": "Three papers to read next",
                "takeaway": "",
                "papers": [
                    {"title": "", "url": "", "why": "", "read_for": ""}
                ],
            },
            {
                "type": "quiz",
                "title": "Check your understanding",
                "takeaway": "",
                "questions": [
                    {
                        "category": "",
                        "question": "",
                        "choices": ["", "", "", ""],
                        "answer": "",
                        "explanation": "",
                    }
                ],
            },
        ],
    },
}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or "paper"


def write_if_absent(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def scaffold_paper(title: str, slug: str | None = None) -> Path:
    slug = slug or slugify(title)
    folder = PAPERS_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)

    tmpl = json.loads(json.dumps(ANALYSIS_TEMPLATE))
    tmpl["paper"]["title"] = title
    tmpl["slug"] = slug

    write_if_absent(folder / "analysis.json",
                    json.dumps(tmpl, indent=2, ensure_ascii=False))
    write_if_absent(folder / "source.md",
                    f"# Source: {title}\n\n"
                    "Paste the paper text, a source link, DOI, or extraction "
                    "details here. Or drop `paper.pdf` in this folder.\n")
    return folder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--slug", default=None)
    args = ap.parse_args()

    slug = args.slug or slugify(args.title)
    folder = scaffold_paper(args.title, slug)

    created = []
    for name in ["analysis.json", "source.md"]:
        if (folder / name).exists():
            created.append(name)

    print(f"slug: {slug}")
    print(f"folder: {folder}")
    print(f"available: {', '.join(created) if created else '(all files already existed)'}")
    print("\nNext: fill analysis.json, then render:")
    print(f"  python paper-reading-assistant/scripts/render_report.py \\")
    print(f"    --input papers/{slug}/analysis.json \\")
    print(f"    --output papers/{slug}/report.html --slug {slug}")


if __name__ == "__main__":
    main()
