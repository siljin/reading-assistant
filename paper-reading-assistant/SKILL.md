---
name: paper-reading-assistant
description: Acquire an academic paper (arXiv link, PDF, OpenReview URL, or other source), extract its content, and produce a self-contained, beginner-friendly HTML report that simplifies, deeply analyzes, and contextualizes it — with an explain-it-simply analogy, a jargon decoder, plain-language figures, optional interactive demos/simulations, a knowledge graph, "so what" implications, persistent in-repo notes, and a list of people to reach out to that starts from the user's own LinkedIn network. Everything for a paper is saved inside the repo under papers/<slug>/. Use whenever the user shares a paper URL or PDF and asks to read, summarize, analyze, "break down", "make sense of", "explain", "go deep on", or "brief someone on" it, even if they don't say "report".
---

# Paper Reading Assistant

Turn a paper into a sharp briefing that a *newcomer* can follow and an expert still respects. Two audiences in one report: someone with zero background gets an analogy, a jargon decoder, and a playable demo; the practitioner gets the skeptical "is this load-bearing" analysis.

This skill is the engine of an end-to-end repo. Each paper gets a folder under `papers/<slug>/` holding its source, analysis JSON, rendered `report.html`, and persistent `notes.md`. The repo is meant to be used by anyone who clones it — keep everything self-contained and documented (see the repo `README.md`).

## Repo layout you operate in

```
papers/<slug>/        source.md / paper.pdf, analysis.json, report.html, notes.md
data/connections.csv  the user's LinkedIn export (gitignored, PII — local only)
paper-reading-assistant/scripts/   render_report.py, find_people.py, serve.py, new_paper.py
```

Resolve script paths relative to this skill folder. The repo root is two levels above `scripts/`.

## Workflow

0. **Scaffold** the paper folder.
1. **Acquire** the paper content and save the source into the folder.
2. **Extract** bibliographic data, structure, claims, methods, results, limitations.
3. **Simplify** — write the ELI5 analogy, jargon decoder, and plan any demos. (This is a first-class goal, not a nicety.)
4. **Analyze** with a skeptical lens (see `references/analysis-rubric.md`).
5. **Find people** — start from the user's own network, then spread out.
6. **Render** the HTML report via `scripts/render_report.py`.
7. **Persist & present** — save into the repo, start the server, point the user at it.

Do not skip steps. The script is the *only* path to the HTML — do not hand-write HTML.

---

## Step 0: Scaffold

```bash
python paper-reading-assistant/scripts/new_paper.py --title "<paper title>" [--slug <slug>]
```

This creates `papers/<slug>/` with `analysis.template.json`, `source.md`, and `notes.md`. Use the printed slug for everything downstream.

## Step 1: Acquire the paper

Determine the source from what the user provided:

- **arXiv URL** (e.g. `arxiv.org/abs/2401.12345`): fetch the abstract page first for metadata, then the HTML version if available (`arxiv.org/html/2401.12345`), falling back to the PDF (`arxiv.org/pdf/2401.12345`).
- **OpenReview / ACL / ACM / IEEE / NeurIPS / blog post URL**: web_fetch the canonical page.
- **PDF uploaded**: read it via the `pdf-reading` skill. Also copy the PDF into `papers/<slug>/paper.pdf` so the paper lives in the repo.
- **Just a title or DOI**: web_search to locate the canonical source, then proceed.

Prefer HTML over PDF when both exist — cleaner section structure and resolvable figure/table references. Save a copy or pointer of the source into `papers/<slug>/source.md`. If acquisition fails (paywall, broken link, OCR-only scan), tell the user what failed and ask them to paste text or upload a PDF.

## Step 2: Extract

Capture the *claims and evidence*, not the prose.

- **Bibliographic**: title, authors (with affiliations if visible), venue, year, link, code/data URLs. Capture affiliations carefully — Step 5 needs them.
- **The actual contribution**: in one sentence, what is now true that wasn't before this paper?
- **Methods**: datasets, architecture, experimental setup, key design choices. Note standard vs. novel.
- **Results**: headline numbers, baselines, metrics. Exact numbers where they matter.
- **Limitations**: stated and unstated.
- **Related work positioning**: which prior works does it define itself against?

## Step 3: Simplify (make it understandable to a newcomer)

The original failure mode of paper summaries is being readable only to people who already get it. Fix that with concrete, populated fields in the analysis JSON:

- **`eli5`** — one vivid **analogy** ("it's like…") plus 2–3 jargon-free sentences. A smart 12th-grader should finish it knowing what the paper does and why anyone cares. No "leveraging", "novel framework", "SOTA".
- **`glossary`** — 4–10 terms a newcomer would trip on, each with a one-line plain definition. These render as a tap-to-expand "jargon decoder".
- **`figures`** — when the paper has a key figure, add an entry with a **plain-language caption** that says what the picture is *telling you*, not what it depicts. (Use a URL in `src`, or omit `src` and just write the caption.)
- **`demos`** — when a concept benefits from interaction, author a tiny self-contained HTML+JS widget (a slider, a toggle, a canvas animation) that lets the reader *feel* the mechanism. Examples: a slider showing how temperature changes a softmax; a toggle comparing attention vs. no-attention; an animation of gradient descent steps. Keep each demo standalone (inline `<script>`), runs in a sandboxed iframe. Prefer one good demo over three weak ones; skip if nothing genuinely clarifies.

Plain-language summary still belongs in `plain_summary` (≈150 words). Re-explain, don't translate.

## Step 4: Analyze (the skeptical core)

Read `references/analysis-rubric.md` before drafting. Headline goals: what's novel vs. incremental, where claims are load-bearing, implementation feasibility, three-bucket "so what", and an 8–15 node knowledge graph. Tone: a trusted colleague briefing you on whether it's worth your time — not a reviewer, fan, or press release.

## Step 5: Find people — start from the user's network, then spread out

Do **not** just list authors. Lead with people the user already knows.

1. **Mine the user's own network.** If `data/connections.csv` exists (the user's LinkedIn export), run:
   ```bash
   python paper-reading-assistant/scripts/find_people.py \
       --keywords "<topic keywords, comma-sep>" \
       --affiliations "<author affiliations, comma-sep>" --top 8
   ```
   This ranks the user's connections by topical/affiliation fit, locally (the CSV is PII and gitignored). Top hits become **1st-degree** people with `connection_path: "1st-degree: your connection"`.
   If the file is missing, tell the user how to add it (README → "Connect your network") and continue with the steps below.

2. **Spread out to 2nd degree.** For the strongest 1st-degree matches, web-search who *they* visibly collaborate with / who works in this exact area at their org. Surface those as `connection_path: "2nd-degree: via <your connection>"`. The aim is the *best-fit* person for this paper, reachable through a warm intro — not necessarily someone you know directly.

3. **Then add cold but high-value contacts**: authors (first + senior), a known critic or competing lab, a practitioner who built the production version. Mark these `connection_path: "cold: <reason reachable>"` or omit the path.

For each person: `name`, `role`, `why` (one sentence), `connection_path`, and either a `linkedin` URL or a `search_hint`. **Never fabricate URLs** — leave `linkedin` null and give a `search_hint` when unsure. Aim for 4–6 people, warm ones first.

## Step 6: Render the HTML

Write the populated analysis to `papers/<slug>/analysis.json` (schema is documented at the top of `render_report.py`), then:

```bash
python paper-reading-assistant/scripts/render_report.py \
    --input papers/<slug>/analysis.json \
    --output papers/<slug>/report.html \
    --slug <slug>
```

The script produces a self-contained HTML file (CSS inlined, knowledge graph via vis-network from CDN, demos in sandboxed iframes, notes editor wired for persistence). If the script errors, read the error, fix the JSON, re-run. Do not work around it by writing HTML.

## Step 7: Persist & present

Everything is already in `papers/<slug>/` — it lives in the repo and travels with it. Notes persist to `papers/<slug>/notes.md` automatically when the report is opened through the local server:

```bash
python paper-reading-assistant/scripts/serve.py
# then open http://localhost:8000/papers/<slug>/report.html
```

Tell the user this in one or two lines: the headline finding (the single sharpest thing), and the path to open. Keep chat short — the report holds the rest. If the user committed earlier reports, their notes are right there in `notes.md`, diffable in git.

---

## Tone reminders

- Two audiences: newcomer-friendly *and* skeptical. The simplify sections carry the first; the analysis carries the second. Don't let either crowd out the other.
- Pointed > comprehensive. If something is uninteresting, say less, not more.
- Calibrated. Say "well-supported" or "load-bearing on one experiment" — whichever is true.
- Demos must clarify, not decorate. No demo beats a confusing demo.
- Never include private/personal details about non-public individuals. Paper authors named in their professional capacity are fine. The user's own connections data stays local (gitignored) — surface a name only as an outreach suggestion to the user, never publish it into a shared artifact beyond their own repo.
