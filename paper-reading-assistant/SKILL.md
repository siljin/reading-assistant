---
name: paper-reading-assistant
description: Acquire an academic paper (arXiv link, PDF, OpenReview URL, DOI, or other source), extract its content, and produce a self-contained, beginner-friendly, visually rich HTML report. Use a paper-specific report_plan so method, benchmark, dataset, theory, systems, survey, clinical, and deployment papers can each be explained with the structure and visuals that fit them best. Everything for a paper is saved under papers/<slug>/. Use whenever the user shares a paper and asks to read, summarize, analyze, break down, explain, go deep on, or brief someone on it.
---

# Paper Reading Assistant

Turn a paper into a sharp briefing that a newcomer can follow and a practitioner still respects. The report should be concise, visual, skeptical, and useful for real decisions.

The core model is:

```text
paper -> analysis.json -> adaptive report_plan -> render_report.py -> report.html
```

Each paper folder holds the source pointer, canonical analysis JSON, and generated HTML:

```text
papers/<slug>/        source.md / paper.pdf, analysis.json, report.html
paper-reading-assistant/scripts/   new_paper.py, render_report.py
```

Resolve script paths relative to this skill folder. The repo root is two levels above `scripts/`.

## Workflow

0. **Scaffold** the paper folder.
1. **Acquire** the paper content and save the source pointer or extracted text.
2. **Extract** bibliographic data, structure, claims, methods, results, limitations, and related work.
3. **Classify** the paper and choose the best explanation shape.
4. **Simplify** for a newcomer: analogy, jargon decoder, plain-language summary.
5. **Analyze** with a skeptical lens using `references/analysis-rubric.md`.
6. **Plan the report** in `analysis.json.report_plan`.
7. **Render** the HTML report through `scripts/render_report.py`.
8. **Present** the headline finding and local path.

Do not hand-write the final HTML. The renderer is the path to `report.html`.

---

## Step 0: Scaffold

```bash
python paper-reading-assistant/scripts/new_paper.py --title "<paper title>" [--slug <slug>]
```

This creates `papers/<slug>/` with `analysis.json` and `source.md`. Use the printed slug downstream.

## Step 1: Acquire the Paper

Determine the source from what the user provided:

- **arXiv URL**: fetch the abstract page for metadata, then the HTML version when available, falling back to the PDF.
- **OpenReview / ACL / ACM / IEEE / NeurIPS / blog post URL**: fetch the canonical page.
- **PDF uploaded**: extract text and copy the PDF into `papers/<slug>/paper.pdf` when useful.
- **Title or DOI**: search for the canonical source, then proceed.

Prefer HTML over PDF when both exist because section structure and references are cleaner. Save the source link, DOI, extraction notes, or pasted text into `papers/<slug>/source.md`. If acquisition fails, tell the user what failed and ask for pasted text or a PDF.

## Step 2: Extract

Capture claims and evidence, not just prose:

- Bibliographic metadata: title, authors, affiliations, venue, year, paper URL, code/data URLs.
- The actual contribution: one sentence saying what is now believable that was not before.
- Methods: datasets, architecture, experimental setup, key design choices, and what is standard vs. new.
- Results: headline numbers, baselines, metrics, and exact values where they matter.
- Limitations: stated and unstated.
- Related work positioning: what the paper builds on or argues against.

## Step 3: Classify the Paper

Choose `report_plan.paper_archetype` and `report_plan.reader_goal` before drafting sections.

Common archetypes:

- **method**: problem -> architecture -> algorithm steps -> ablations -> limitations -> implementation notes
- **benchmark**: task setup -> dataset/eval protocol -> result comparisons -> caveats -> field implications
- **dataset**: source -> collection pipeline -> coverage/distribution -> bias/risk -> use cases
- **theory**: problem -> assumptions -> theorem/claim -> intuition -> implications -> open questions
- **clinical/deployment**: workflow -> study design -> outcomes -> safety gaps -> product/regulatory implications
- **survey**: field map -> taxonomy -> consensus -> disagreements -> future directions
- **systems**: architecture -> workload -> trade-offs -> performance -> operational constraints

Repeatability means consistent generation mechanics, not identical section order.

## Step 4: Simplify

Fill these fields concretely:

- **`eli5`**: one vivid analogy plus two or three jargon-free sentences.
- **`glossary`**: four to ten terms a newcomer would trip on, each with a one-line practical definition.
- **`plain_summary`**: around 150 words that re-explain the paper rather than translating the abstract.
- **`figures` / `demos`**: include only when they clarify. A demo should teach a mechanism faster than prose.

## Step 5: Analyze

Read `references/analysis-rubric.md` before drafting. Focus on novelty, load-bearing claims, evidence quality, feasibility, limitations, implications, and business/product relevance when appropriate.

## Step 6: Build `report_plan`

Add a `report_plan` object to `analysis.json`:

```json
{
  "paper_archetype": "method",
  "reader_goal": "learn field and evaluate usefulness",
  "narrative_arc": ["problem_context", "architecture_or_pipeline", "results_interpretation"],
  "sections": []
}
```

Each section should contain:

```json
{
  "type": "problem_context",
  "title": "",
  "takeaway": "",
  "content": "",
  "bullets": [],
  "caveats": [],
  "visuals": []
}
```

Use these section types as building blocks:

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

Choose visuals per section. Do not force a heatmap, funnel, or matrix if another representation explains the paper better. Supported visual primitives include:

```text
cards
table
flow
bar_chart
matrix
timeline
comparison
heatmap
funnel
```

Every report should usually end with:

- **`learning_path`**: three suggested papers for learning the field.
- **`quiz`**: five MCQs testing paper comprehension, field understanding, business insight, product insight, and general research context.

## Step 7: Render

Write the populated analysis to `papers/<slug>/analysis.json`, then:

```bash
python paper-reading-assistant/scripts/render_report.py \
  --input papers/<slug>/analysis.json \
  --output papers/<slug>/report.html \
  --slug <slug>
```

If rendering fails, fix the JSON and re-run. Do not bypass the renderer.

## Step 8: Present

Tell the user the headline finding and the `papers/<slug>/report.html` path to open directly in a browser. Keep chat short; the report carries the detail.

---

## Tone Reminders

- Newcomer-friendly and skeptical at the same time.
- Pointed over exhaustive.
- Calibrated claims beat press-release language.
- Visuals must explain, not decorate.
- Never include private personal details about non-public individuals.
