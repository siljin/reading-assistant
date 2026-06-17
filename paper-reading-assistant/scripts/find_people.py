#!/usr/bin/env python3
"""
find_people.py — Rank YOUR LinkedIn connections by fit to a paper's topic.

This is the deterministic, local, PII-safe first pass behind the skill's
"people to reach out to" step. It reads your LinkedIn connections export and
surfaces the people in YOUR network whose company/title best match the paper's
topic — so outreach starts from your own graph instead of from cold authors.

The agent then takes this ranked list and "spreads out": for the top in-network
people it can web-search who THEY know in the area (2nd degree), and it still
adds authors / adjacent experts as cold options — but your warm connections lead.

Input file (default: data/connections.csv) is the standard LinkedIn export.
Get it from: LinkedIn → Settings → Data Privacy → Get a copy of your data →
"Connections". Columns (LinkedIn's own header, sometimes preceded by notes rows):

    First Name,Last Name,URL,Email Address,Company,Position,Connected On

Example synthetic row:

    Sam,Lee,https://linkedin.com/in/sample,,Acme Labs,ML Researcher,14 Mar 2023

The file is gitignored — it contains personal data and must stay local.

Usage:
    python find_people.py --keywords "diffusion,image generation,RLHF" \\
                          --affiliations "MIT,Google DeepMind" \\
                          --top 8
Output: JSON list of {name, company, position, url, score, matched_on}.
"""

import argparse
import csv
import json
import sys
from pathlib import Path


def load_connections(path: Path) -> list[dict]:
    """Read a LinkedIn Connections.csv. LinkedIn sometimes prefixes the file with
    a few 'Notes:' lines before the real header, so skip until we find it."""
    if not path.exists():
        print(f"ERROR: {path} not found. Drop your LinkedIn 'Connections.csv' "
              f"export there (see data/connections.example.csv).", file=sys.stderr)
        sys.exit(1)

    with path.open(newline="", encoding="utf-8-sig") as f:
        lines = f.readlines()
    # Find the header line that starts the real table.
    start = 0
    for i, line in enumerate(lines):
        if line.lower().startswith("first name,"):
            start = i
            break
    rows = []
    reader = csv.DictReader(lines[start:])
    for r in reader:
        rows.append({k.strip(): (v or "").strip() for k, v in r.items() if k})
    return rows


def score_connection(conn: dict, keywords: list[str], affiliations: list[str]) -> tuple[int, list[str]]:
    """Cheap, explainable scoring. Company/affiliation hits weigh more than title
    keyword hits, because a shared org is a stronger warm-intro signal."""
    haystack_company = (conn.get("Company", "")).lower()
    haystack_title = (conn.get("Position", "")).lower()
    score = 0
    matched = []
    for aff in affiliations:
        a = aff.strip().lower()
        if a and a in haystack_company:
            score += 5
            matched.append(f"company~{aff}")
    for kw in keywords:
        k = kw.strip().lower()
        if not k:
            continue
        if k in haystack_title:
            score += 3
            matched.append(f"title~{kw}")
        elif k in haystack_company:
            score += 1
            matched.append(f"company-kw~{kw}")
    return score, matched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connections", default="data/connections.csv",
                    help="Path to LinkedIn Connections.csv (default: data/connections.csv)")
    ap.add_argument("--keywords", default="",
                    help="Comma-separated topic keywords from the paper")
    ap.add_argument("--affiliations", default="",
                    help="Comma-separated affiliations of the authors")
    ap.add_argument("--top", type=int, default=8, help="How many to return")
    args = ap.parse_args()

    keywords = [k for k in args.keywords.split(",") if k.strip()]
    affiliations = [a for a in args.affiliations.split(",") if a.strip()]

    conns = load_connections(Path(args.connections))
    scored = []
    for c in conns:
        s, matched = score_connection(c, keywords, affiliations)
        if s > 0:
            name = f"{c.get('First Name','')} {c.get('Last Name','')}".strip()
            scored.append({
                "name": name,
                "company": c.get("Company", ""),
                "position": c.get("Position", ""),
                "url": c.get("URL", ""),
                "score": s,
                "matched_on": matched,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    result = scored[: args.top]
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result:
        print("\n(no in-network matches — agent should fall back to authors + "
              "web-searched adjacent experts)", file=sys.stderr)


if __name__ == "__main__":
    main()
