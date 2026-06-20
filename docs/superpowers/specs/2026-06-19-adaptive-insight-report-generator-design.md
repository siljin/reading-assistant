# Adaptive Insight Report Generator Design

## Goal

Upgrade the reusable paper report generator so every new report opens as an insight-driven briefing, not a long text summary. The shared experience should feel consistent across papers, while the actual modules adapt to the paper archetype. The so-what layer is a primary output: readers should understand what the paper means for research, products, and business decisions.

## Current Problems

The current LLM agents survey report exposes four weaknesses in the generator:

- The paper source link is present but visually easy to miss.
- The report is prose-heavy before the reader gets a usable mental map.
- Several intended visuals do not render because the analysis JSON uses fields such as `data`, `note`, `rows`, and `stages` while the renderer expects fields such as `items`, `caption`, `columns`, and `steps`.
- Research, product, and business implications exist mostly as paragraphs, so the so-what layer is not decision-grade.

## Design Principles

- Use one visual design system across all reports: dashboard opening, strong paper link, readable cards, charts, matrices, tabs, and expandable details.
- Adapt the insight modules by paper archetype. A survey, method paper, benchmark, dataset paper, theory paper, systems paper, and clinical/product paper should not all use the same section sequence.
- Put the so-what layer near the top, after the reader has enough context to interpret it.
- Prefer visual explanations when they reduce cognitive load: field maps, maturity bars, evidence heatmaps, opportunity matrices, timelines, flows, and tables.
- Keep the deep-dive prose, but make it secondary to the first-screen orientation and decision layer.
- Avoid silent visual failures. Unknown or alias visual schemas should either normalize or render a clear fallback.

## Shared Report Shell

Every report should include:

- **Paper At A Glance**: title, venue/year, archetype, source link, code/data links when present, one-sentence verdict, evidence base, and reader goal.
- **Insight Dashboard**: a compact first-screen set of metrics and visuals chosen by archetype.
- **So-What Layer**: explicit Research, Product, and Business lenses with implications, risks, opportunities, and next actions.
- **Interactive Reading Controls**: tabs for reader lenses, expandable claim cards, quiz answer reveals, and optional reader-goal filters.
- **Deep Dive Sections**: adaptive explanatory sections already supported by `report_plan.sections`.

## Archetype Adaptation

The generator should choose modules by `report_plan.paper_archetype`.

| Archetype | Primary Insight Modules |
| --- | --- |
| `survey` | Field map, taxonomy heatmap, maturity bar chart, consensus/disagreement map, opportunity matrix, so-what lenses |
| `method` | Architecture or algorithm flow, novelty comparison, result/ablation bars, implementation feasibility, adoption risks |
| `benchmark` | Evaluation setup, leaderboard/table, metric comparison bars, benchmark caveats, usefulness matrix |
| `dataset` | Data pipeline, coverage/distribution charts, bias/risk heatmap, use-case matrix, maintenance/licensing implications |
| `theory` | Assumptions map, claim-to-intuition ladder, dependency graph, limits of applicability, research implications |
| `systems` | Architecture diagram, workload/performance trade-off charts, operational constraints, adoption readiness |
| `clinical` or `product/deployment` | Workflow map, study/evidence quality, safety/regulatory matrix, adoption readiness, business/liability risks |

If an archetype is missing or unknown, the generator should use a conservative default: paper-at-a-glance, core claims, evidence profile, limitations, so-what lenses, learning path, and quiz.

## Analysis Schema Changes

Extend `analysis.json` with optional structured blocks that the renderer can use when present:

```json
{
  "insight_dashboard": {
    "cards": [
      {"label": "Evidence base", "value": "300+ papers", "caption": "Qualitative survey"}
    ],
    "primary_visuals": []
  },
  "so_what": {
    "research": {
      "headline": "",
      "implications": [],
      "open_questions": [],
      "next_actions": []
    },
    "product": {
      "headline": "",
      "opportunities": [],
      "guardrails": [],
      "next_actions": []
    },
    "business": {
      "headline": "",
      "market_openings": [],
      "adoption_blockers": [],
      "risks": [],
      "next_actions": []
    }
  },
  "opportunity_matrix": {
    "x_axis": "Feasibility",
    "y_axis": "Strategic value",
    "cells": []
  },
  "evidence_profile": {
    "claims": [
      {"claim": "", "support": 0, "risk": 0, "caption": ""}
    ]
  }
}
```

These fields are additive. Existing `report_plan.sections[].visuals` remains supported.

## Visual Schema Normalization

Before rendering a visual, the renderer should normalize common aliases:

- `timeline.data[]` becomes `timeline.items[]`.
- `era` becomes `label`.
- `note`, `description`, and `text` become `caption` where appropriate.
- `flow.steps[].note` becomes `flow.steps[].caption`.
- `comparison.rows[]` can render as a comparison table when `items[]` is absent.
- `matrix` visuals with `x_label`, `y_label`, and coordinate-style cells should render as a matrix instead of disappearing.
- `funnel.stages[]` becomes `funnel.steps[]`.

The renderer should include tests for every alias above so future reports do not silently lose visuals.

## Interaction Design

The generated HTML remains self-contained and static. Interaction should use inline, dependency-free JavaScript:

- Lens tabs for Research, Product, and Business.
- Expandable claim cards for evidence and caveats.
- Quiz answer reveals, preserving the current behavior.
- Optional filter chips for reader goals such as Beginner, Builder, Researcher, and Investor.

The page must remain useful with JavaScript disabled: all content should be present in the HTML, with interaction only improving navigation and focus.

## Data Flow

```text
paper source
  -> analysis.json
  -> archetype-specific insight blocks
  -> renderer normalization
  -> shared report shell
  -> adaptive infographic modules
  -> self-contained report.html
```

The agent remains responsible for extracting real paper insights. The renderer is responsible for robust layout, visual normalization, interaction, and consistent presentation.

## Testing

Add focused tests that prove:

- The paper source link is prominent and rendered when `paper.url` exists.
- Survey reports render an insight dashboard, so-what lenses, field-map style visuals, and an opportunity matrix.
- Method, benchmark, dataset, theory, systems, and clinical/product archetypes can each render their expected primary modules without forcing the survey layout.
- Visual schema aliases render instead of disappearing.
- Existing legacy analysis files still render through the fallback path.
- The generated HTML includes interaction affordances without requiring external assets.

## Out Of Scope

- Calling an LLM API from the renderer.
- Downloading papers or changing paper acquisition.
- Replacing the static HTML artifact with a hosted app.
- Retrofitting every existing report automatically. Existing reports update only when re-rendered.

## Success Criteria

- A newcomer can understand the paper's domain, core claims, and field map within the first screen and first two sections.
- A practitioner can identify what to build, research, avoid, or validate next without reading every paragraph.
- The so-what layer is visible, structured, and specific for research, product, and business audiences.
- New reports share a polished visual system but adapt their insight modules by paper archetype.
- No intended visual disappears silently because of minor schema differences.
