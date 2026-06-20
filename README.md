# Reading Assistant

An **agentic paper-reading assistant**. Hand it a paper (arXiv link, PDF, DOI, or uploaded source) and it produces a self-contained, visual HTML briefing that adapts to that paper instead of forcing every paper into the same template.

The core pipeline is:

```text
paper -> analysis.json -> adaptive report_plan -> renderer -> report.html
```

Everything for a paper lives in the repo under `papers/<slug>/`, so the source pointer, structured analysis, insight dashboard, so-what layer, and generated artifact are easy to review and diff.

---

## What you get per paper

```text
papers/<slug>/
  paper.pdf          optional source PDF, gitignored by default
  source.md          pasted text, source link, DOI, or extraction notes
  analysis.json      canonical structured analysis, including report_plan
  report.html        generated self-contained briefing
```

The `report.html` is static and self-contained: inline CSS, no personal-data APIs, and no runtime database. Open it directly in a browser.

---

## Requirements

- Python 3.10+
- A browser
- Codex/Claude or another agent if you want paper acquisition and analysis filled in for you

No `pip install` is required for the included scripts.

---

## Quick Start

Agent-driven:

1. Ask the assistant to run the orchestrator, for example: `Use the reading assistant orchestrator to pull one paper with profiles/medical-ai.json, complete analysis.json, render report.html, and verify it.`
2. The assistant follows `paper-reading-assistant/ORCHESTRATOR.md`, writes `analysis.json`, renders `report.html`, and tells you where to open it.
3. Open `papers/<slug>/report.html` directly in your browser.

Manual:

```bash
python paper-reading-assistant/scripts/new_paper.py --title "Attention Is All You Need"

# Fill papers/<slug>/analysis.json.
# The report_plan controls the adaptive section order.

python paper-reading-assistant/scripts/render_report.py \
  --input papers/<slug>/analysis.json \
  --output papers/<slug>/report.html \
  --slug <slug>
```

Automatic pull:

```bash
python paper-reading-assistant/scripts/pull_paper.py --profile profiles/medical-ai.json --dry-run
python paper-reading-assistant/scripts/pull_paper.py --profile profiles/medical-ai.json
```

The puller selects exactly one eligible paper per run using OpenAlex metadata, writes `source.md` and starter `analysis.json`, and records the selected paper in `papers/.pulled.json` so recurring runs do not pick the same paper again. Profiles can optionally add curated trend signals, currently `dair-ai-weekly` from DAIR.AI's AI Papers of the Week, but OpenAlex remains the primary discovery source. It does not download PDFs or call an LLM API; report completion remains agent-assisted.

Agent-orchestrated end-to-end flow:

```bash
python paper-reading-assistant/scripts/workflow_status.py --latest
python paper-reading-assistant/scripts/workflow_status.py --slug <slug>
```

`workflow_status.py` is a read-only helper for the chat agent. It reports whether a paper is `staged`, `analysis-incomplete`, `ready-to-render`, or `rendered`. The LLM reasoning happens only when the chat agent reads `source.md` and completes `analysis.json`; no repo script calls a model.

---

## Adaptive Reports

`analysis.json` is the canonical source. Its `report_plan` tells the renderer what shape best fits the paper:

- `paper_archetype`: method, benchmark, dataset, theory, survey, systems, clinical, product/deployment, etc.
- `reader_goal`: learn the field, decide usefulness, reproduce the method, evaluate product potential, etc.
- `narrative_arc`: the ordered story for this specific paper.
- `sections[]`: typed blocks with title, takeaway, content, caveats, and optional visuals.

The renderer keeps a consistent visual shell, but the paper decides the body and top-level insight modules. A survey paper can emphasize field maps, maturity bars, and opportunity matrices. A method paper can emphasize architecture and ablations. A benchmark paper can emphasize task setup and comparisons. A dataset paper can emphasize collection, coverage, bias, and use cases. A theory paper can emphasize assumptions, claims, intuition, and open questions.

The newer insight layer is additive to `report_plan`:

```text
insight_dashboard     early cards and primary visuals after reader orientation
evidence_profile      claim support/risk bars
so_what               research, product, and business lenses
opportunity_matrix    value/feasibility or readiness/risk map
```

The so-what layer is intentionally first-class, but it should appear after the reader has the paper context needed to understand it. A report should say what the paper means for research direction, product decisions, and business opportunity or risk.

Supported section types include:

```text
problem_context
core_contribution
method_walkthrough
architecture_or_pipeline
experiment_design
results_interpretation
limitations_and_caveats
real_world_implications
business_or_product_insight
learning_path
quiz
```

Supported visual primitives include cards, tables, flow diagrams, charts, matrices, timelines, comparison blocks, learning paths, and MCQs. Use visuals when they explain the section better than prose.

---

## Skill Source

The agent workflow lives at `paper-reading-assistant/`:

```text
paper-reading-assistant/
  ORCHESTRATOR.md                 end-to-end chat-agent workflow
  SKILL.md                       workflow for paper-to-report generation
  references/analysis-rubric.md  analysis and report-plan guidance
  scripts/
    new_paper.py        scaffold papers/<slug>/
    pull_paper.py       select one paper from a topic profile
    render_report.py    analysis.json -> report.html
    workflow_status.py validate workflow readiness
```

---

## Pipeline

```text
paper URL/PDF/text
   │
   ▼
source.md + extracted facts
   │
   ▼
analysis.json
   ├─ bibliographic metadata
   ├─ explanation + skeptical analysis
   └─ report_plan.sections[]
        │
        ▼
render_report.py
        │
        ▼
report.html
```

Automatic discovery uses this same path:

```text
profiles/<topic>.json
   │
   ▼
pull_paper.py  ──► OpenAlex search + optional curated enrichment + scoring rubric
   │
   ├─► papers/.pulled.json  (dedupe ledger)
   ▼
papers/<slug>/source.md + analysis.json
```

Selection score is out of 100:

- Relevance: 35
- Citation signal: 17
- Recency/trend: 18
- Curated popularity: 10
- Source credibility: 8
- Accessibility: 7
- Novelty/diversity: 5

---

## Roadmap

- Library/index UI over `papers/`
- Cross-paper search over `analysis.json`
- Reusable ingestion for reading queues
- More visual primitives and richer browser verification
- Optional PDF extraction helpers

The invariant: one folder per paper, `analysis.json` as the canonical source, and `report.html` generated by `render_report.py`.

---

## Privacy & Safety

- `papers/*/paper.pdf` is gitignored by default because papers can be large or copyrighted.
- Generated reports are static HTML artifacts with no personal notes or outreach workflow.
