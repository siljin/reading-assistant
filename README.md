# Reading Assistant

An **agentic paper-reading assistant**. Hand it a paper (arXiv link, PDF, or DOI) and it produces a self-contained HTML briefing that a newcomer can actually follow — an explain-it-simply analogy, a jargon decoder, plain-language figures, optional **interactive demos**, an interactive knowledge graph, a skeptical "is this load-bearing" analysis, **persistent notes**, and a list of **people to reach out to that starts from your own network**.

Everything for a paper lives in the repo under `papers/<slug>/`, so reports and notes travel with it and are diffable in git. This is the foundation of an end-to-end app; the analysis brain ships today as a Claude Code / Claude.ai **skill**.

---

## What you get per paper

```
papers/<slug>/
  paper.pdf          the source PDF (optional; gitignored by default)
  source.md          pasted text / link / where the source lives
  analysis.json      the structured analysis the agent produces
  report.html        the self-contained briefing (open in any browser)
  notes.md           your notes — persist here, committed with the repo
```

The `report.html` is fully self-contained: inlined CSS, knowledge graph via a CDN, demos sandboxed in iframes. Open it directly, or through the local server to get note-saving to disk.

---

## Requirements

- **Python 3.10+** — that's it. The scripts use only the standard library.
- A browser. (The knowledge graph loads `vis-network` from a CDN, so first view of the graph wants internet; everything else works offline.)
- Claude Code or Claude.ai if you want the agent to do the reading/analysis for you.

No `pip install` needed.

---

## Quick start (agent-driven — the normal path)

1. Install the skill (see **Install the skill** below), or open this repo in Claude Code where the skill is already present.
2. Say: *"Read this paper: https://arxiv.org/abs/1706.03762"* (or attach a PDF).
3. The agent scaffolds `papers/<slug>/`, reads the paper, writes `analysis.json`, renders `report.html`, and tells you the headline finding + where to open it.
4. View it with notes that save to disk:
   ```bash
   python paper-reading-assistant/scripts/serve.py
   # open http://localhost:8000/papers/<slug>/report.html
   ```

## Quick start (manual — drive the scripts yourself)

```bash
# 1. scaffold a folder
python paper-reading-assistant/scripts/new_paper.py --title "Attention Is All You Need"

# 2. copy papers/<slug>/analysis.template.json -> analysis.json and fill it in
#    (schema is documented at the top of render_report.py)

# 3. render
python paper-reading-assistant/scripts/render_report.py \
    --input papers/attention-is-all-you-need/analysis.json \
    --output papers/attention-is-all-you-need/report.html \
    --slug attention-is-all-you-need

# 4. serve + open (notes now save to papers/<slug>/notes.md)
python paper-reading-assistant/scripts/serve.py
```

---

## Notes that persist

The report has a Notes editor at the bottom. How it saves depends on how you open it:

- **Through `serve.py`** (`http://localhost:8000/...`) — notes save to `papers/<slug>/notes.md` on disk. Commit it and your notes travel with the repo and are diffable.
- **Opened as a file** (`file://...`) — notes save to your browser's localStorage, and a **Download notes.md** button lets you drop them into the folder manually.

Either way the **Download notes.md** button always works.

---

## Connect your network (people to reach out to)

The assistant doesn't just cite the authors. It **starts from people you already know** and spreads outward to the best-fit contact for the paper.

1. Export your connections from LinkedIn:
   **LinkedIn → Settings → Data privacy → Get a copy of your data → "Connections" → Request archive.**
2. Save the file as `data/connections.csv`. This path is **gitignored** — your contacts stay on your machine and never get committed.
   See `data/connections.example.csv` for the exact shape (LinkedIn prepends a few notes lines, then a header: `First Name,Last Name,URL,Email Address,Company,Position,Connected On`).
3. That's it. When analyzing a paper the agent runs `find_people.py` to rank your connections by fit, then web-searches outward (2nd degree), then adds authors/experts as cold options — warm contacts first.

You can also run the ranker directly:
```bash
python paper-reading-assistant/scripts/find_people.py \
    --keywords "diffusion,image generation" \
    --affiliations "MIT,Google DeepMind" --top 8
```

> Privacy: `connections.csv` is personal data. It is read locally only, never committed (gitignored), and names surface only as private outreach suggestions to you — never published into a shared artifact.

---

## The skill

The analysis brain is a skill whose source lives, unzipped and editable, at
`paper-reading-assistant/`:

```
paper-reading-assistant/
  SKILL.md                       the workflow the agent follows
  references/analysis-rubric.md  how to do the analysis well
  scripts/
    new_paper.py        scaffold papers/<slug>/
    render_report.py    analysis.json -> self-contained report.html
    find_people.py      rank your LinkedIn connections by topic fit
    serve.py            local server: serves reports + saves notes to disk
    build_skill.sh      repackage the folder into paper-reading-assistant.skill
```

### Install the skill

- **Claude.ai / Claude Code (upload):** upload `paper-reading-assistant.skill` (the zip in the repo root). Rebuild it after edits with:
  ```bash
  bash paper-reading-assistant/scripts/build_skill.sh
  ```
- **Claude Code (local):** point your skills directory at `paper-reading-assistant/`, or just open this repo — the agent can read `SKILL.md` directly.

---

## How it works (pipeline)

```
paper (URL/PDF)
   │  acquire + extract            (agent)
   ▼
analysis.json  ──────────────┐
   │  render_report.py        │ find_people.py ← data/connections.csv (local)
   ▼                          ▼
report.html  ◄── people, knowledge graph, demos, notes editor
   │  serve.py
   ▼
browser  ──► notes ──► papers/<slug>/notes.md  (committed with repo)
```

---

## Roadmap (this is the beginning)

This repo is built to grow into a full end-to-end app. Natural next steps:

- A library/index UI over `papers/` (the server already exposes a basic index at `/`).
- Cross-paper knowledge graph (merge per-paper graphs).
- Auto-ingest from a reading queue (RSS / arXiv alerts).
- Embeddings + search across all analyses and notes.
- Richer 2nd-degree network inference.

Contributions should keep the core invariant: **one folder per paper, everything self-contained, the rendered HTML produced only by `render_report.py`.**

---

## Privacy & safety

- `data/connections.csv` and `papers/*/paper.pdf` are gitignored by default. Review `.gitignore` before committing.
- The assistant names paper authors (public, professional capacity) freely. It treats your private connections as local-only outreach hints.
- Demos run in sandboxed iframes (`allow-scripts` only) so embedded JS can't touch the rest of the page or your notes.
