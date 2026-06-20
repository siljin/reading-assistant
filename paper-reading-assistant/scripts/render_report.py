#!/usr/bin/env python3
"""
render_report.py - Render a structured paper analysis JSON into a self-contained
adaptive HTML report.

Usage:
    python render_report.py --input analysis.json --output report.html [--slug my-paper]

Core model:

    paper source -> analysis.json -> report_plan.sections[] -> report.html

The renderer owns layout and styling. The agent owns content and chooses the
paper-specific explanation shape through report_plan. Old analysis files without
report_plan still render through a conservative fallback plan.

Supported report_plan shape:

{
  "paper": {"title": "...", "authors": [], "venue": "...", "year": 2026, "url": "..."},
  "slug": "...",
  "headline": "One-sentence verdict.",
  "plain_summary": "Short newcomer-friendly summary.",
  "insight_dashboard": {
    "cards": [{"label": "Evidence base", "value": "300+ papers", "caption": "Qualitative survey"}],
    "primary_visuals": [{"type": "bar_chart", "title": "...", "bars": []}]
  },
  "evidence_profile": {
    "claims": [{"claim": "...", "support": 8, "risk": 5, "caption": "..."}]
  },
  "so_what": {
    "research": {"headline": "...", "implications": [], "open_questions": [], "next_actions": []},
    "product": {"headline": "...", "opportunities": [], "guardrails": [], "next_actions": []},
    "business": {"headline": "...", "market_openings": [], "adoption_blockers": [], "risks": [], "next_actions": []}
  },
  "opportunity_matrix": {
    "x_axis": "Feasibility",
    "y_axis": "Strategic value",
    "columns": [],
    "rows": [],
    "cells": []
  },
  "report_plan": {
    "paper_archetype": "method | benchmark | dataset | theory | survey | systems | clinical | product/deployment",
    "reader_goal": "learn field | decide usefulness | reproduce method | evaluate business/product potential",
    "narrative_arc": ["problem_context", "method_walkthrough", "..."],
    "sections": [
      {
        "type": "problem_context",
        "title": "Why this matters",
        "takeaway": "One sharp claim.",
        "content": "Markdown-light prose.",
        "bullets": ["optional bullets"],
        "caveats": ["optional caveats"],
        "visuals": [
          {"type": "flow", "title": "...", "steps": [{"label": "...", "caption": "..."}]},
          {"type": "heatmap", "title": "...", "columns": ["A"], "rows": [{"label": "R", "cells": ["..."]}]},
          {"type": "funnel", "title": "...", "steps": [{"label": "...", "caption": "...", "status": "supported|caution|gap"}]},
          {"type": "matrix", "title": "...", "columns": ["Low", "High"], "rows": ["Value"], "cells": [{"label": "...", "caption": "...", "tone": "good|caution|bad|neutral"}]},
          {"type": "timeline", "title": "...", "items": [{"label": "2026", "title": "...", "caption": "...", "url": "..."}]},
          {"type": "bar_chart", "title": "...", "bars": [{"label": "...", "value": 8, "max": 10, "caption": "..."}]},
          {"type": "line_chart", "title": "...", "points": [{"label": "2024", "value": 4, "caption": "..."}]},
          {"type": "cards", "title": "...", "items": [{"label": "...", "value": "...", "caption": "..."}]},
          {"type": "table", "title": "...", "columns": ["A"], "rows": [["..."]]},
          {"type": "comparison", "title": "...", "items": [{"label": "Before", "text": "..."}, {"label": "After", "text": "..."}]}
        ]
      },
      {
        "type": "learning_path",
        "title": "Read next",
        "papers": [{"title": "...", "url": "...", "why": "...", "read_for": "..."}]
      },
      {
        "type": "quiz",
        "title": "Check your understanding",
        "questions": [{"category": "...", "question": "...", "choices": [], "answer": "...", "explanation": "..."}]
      }
    ]
  }
}

Legacy personal-workflow fields are ignored; the artifact is a static visual
briefing generated from the structured analysis.
"""

import argparse
import html
import json
import mimetypes
import os
import re
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from report_config import DEFAULT_CONFIG_PATH, email_smtp_settings, load_app_config


def esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:60] or "paper"


def section_class(section_type: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", section_type or "section").strip("-")
    return clean or "section"


def section_anchor(section_type: str) -> str:
    return f"section-{section_class(section_type)}"


def md_to_html(text: str) -> str:
    """Tiny markdown subset: bold, italic, inline code, bullets, paragraphs."""
    if not text:
        return ""
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    lines = text.splitlines()
    out: list[str] = []
    para: list[str] = []
    in_list = False

    def flush_para():
        if para:
            out.append("<p>" + " ".join(para).strip() + "</p>")
            para.clear()

    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped):
            flush_para()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + re.sub(r"^[-*]\s+", "", stripped) + "</li>")
        elif not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            flush_para()
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            para.append(stripped)
    if in_list:
        out.append("</ul>")
    flush_para()
    return "\n".join(out)


def render_link(url: str, label: str) -> str:
    if not url:
        return ""
    return f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a>'


def render_source_button(url: str, label: str = "Open paper") -> str:
    if not url:
        return ""
    return f'<a class="source-button" href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a>'


ARCHETYPE_MODULES = {
    "survey": [
        ("Field map", "Map the topic space and its major branches."),
        ("Evidence heatmap", "Separate consensus from thin or speculative evidence."),
        ("Opportunity matrix", "Translate the field map into build, research, and business bets."),
    ],
    "method": [
        ("Architecture flow", "Show the algorithm, model, or system pipeline."),
        ("Result and ablation bars", "Explain what improved and which component mattered."),
        ("Implementation feasibility", "Estimate requirements, effort, and adoption risk."),
    ],
    "benchmark": [
        ("Evaluation setup", "Make the task, metric, and protocol clear first."),
        ("Leaderboard comparison", "Compare systems without hiding benchmark caveats."),
        ("Usefulness matrix", "Show where the benchmark is valid or misleading."),
    ],
    "dataset": [
        ("Data pipeline", "Show collection, filtering, labeling, and release shape."),
        ("Coverage and bias map", "Expose what the dataset includes and misses."),
        ("Use-case matrix", "Connect the data asset to practical applications."),
    ],
    "theory": [
        ("Assumptions map", "Make the claim's prerequisites explicit."),
        ("Claim intuition ladder", "Translate formal claims into reader intuition."),
        ("Applicability limits", "Show where the theory does and does not travel."),
    ],
    "systems": [
        ("Architecture diagram", "Show services, workload, and operational boundaries."),
        ("Performance trade-offs", "Compare latency, cost, scale, and reliability."),
        ("Adoption readiness", "Translate performance into deployment constraints."),
    ],
    "clinical": [
        ("Workflow map", "Place the model inside care delivery."),
        ("Safety and evidence matrix", "Separate study evidence from deployment readiness."),
        ("Adoption readiness", "Surface regulatory, workflow, and liability risks."),
    ],
    "product/deployment": [
        ("Workflow map", "Place the model inside the user or business process."),
        ("Safety and evidence matrix", "Separate study evidence from deployment readiness."),
        ("Adoption readiness", "Surface operational, legal, and liability risks."),
    ],
}


def archetype_modules(archetype: str) -> list[tuple[str, str]]:
    clean = (archetype or "").lower()
    return ARCHETYPE_MODULES.get(clean, [
        ("Core claims", "Show the paper's load-bearing ideas."),
        ("Evidence profile", "Calibrate how strongly the paper supports those ideas."),
        ("So-what lenses", "Translate the paper into research, product, and business implications."),
    ])


def render_hero(analysis: dict, slug: str) -> str:
    paper = analysis.get("paper", {})
    plan = analysis.get("report_plan", {}) or {}
    title = paper.get("title") or "Untitled paper"
    headline = analysis.get("headline") or "A structured visual briefing for this paper."
    author_list = paper.get("authors") or []
    if len(author_list) > 5:
        authors = ", ".join(author_list[:5]) + f", et al. ({len(author_list)} authors)"
    else:
        authors = ", ".join(author_list)
    meta_bits = []
    if paper.get("venue"):
        meta_bits.append(str(paper["venue"]))
    if paper.get("year"):
        meta_bits.append(str(paper["year"]))
    archetype = plan.get("paper_archetype")
    if archetype:
        meta_bits.append(str(archetype).title())
    meta = " / ".join(meta_bits)
    link = render_link(paper.get("url", ""), "Open paper")
    source_button = render_source_button(paper.get("url", ""))
    code_button = render_source_button(paper.get("code_url", ""), "Open code")
    data_button = render_source_button(paper.get("data_url", ""), "Open data")
    reader_goal = plan.get("reader_goal") or "understand and evaluate the paper"
    archetype_label = str(archetype or "paper").title()

    return f"""
    <section class="hero adaptive-section section-title" aria-labelledby="title">
      <div>
        <div class="eyebrow">Research paper visual briefing</div>
        <h1 id="title">{esc(title)}</h1>
        <p class="hero-lede">{esc(headline)}</p>
        <div class="hero-actions">
          <span class="pill">{esc(reader_goal)}</span>
          {f'<span class="pill muted-pill">{esc(meta)}</span>' if meta else ''}
          {source_button}
          {code_button}
          {data_button}
        </div>
        <p class="source-line">
          {f'{esc(authors)}<br>' if authors else ''}
          {link}
        </p>
      </div>
      <aside class="hero-board">
        <div class="label">Paper at a glance</div>
        <p class="hero-board-title">{esc(archetype_label)} briefing for {esc(reader_goal)}.</p>
        <p>The report uses a shared visual system, but the insight modules adapt to the paper type.</p>
        <p class="slug">Slug: <code>{esc(slug)}</code></p>
      </aside>
    </section>
    """


def render_insight_dashboard(analysis: dict, anchor_id: str = "section-insight_dashboard") -> str:
    plan = analysis.get("report_plan", {}) or {}
    paper = analysis.get("paper", {}) or {}
    dashboard = analysis.get("insight_dashboard", {}) or {}
    archetype = (plan.get("paper_archetype") or "paper").lower()
    cards = list(dashboard.get("cards") or [])

    if not cards:
        cards = [
            {
                "label": "Paper type",
                "value": archetype.title() if archetype else "Paper",
                "caption": "The visual modules below are selected from the paper archetype.",
            },
            {
                "label": "Evidence base",
                "value": paper.get("venue") or "Structured analysis",
                "caption": "Use the paper-specific caveats before treating claims as settled.",
            },
            {
                "label": "Reader goal",
                "value": plan.get("reader_goal") or "Understand and evaluate",
                "caption": "The dashboard points different readers toward the right deep dive.",
            },
        ]

    card_visual = render_cards_visual({"items": cards})
    modules = "".join(
        f"""
        <article class="module-card">
          <strong>{esc(label)}</strong>
          <p>{esc(caption)}</p>
        </article>
        """
        for label, caption in archetype_modules(archetype)
    )
    visuals = []
    for visual in dashboard.get("primary_visuals") or []:
        rendered = render_visual(visual)
        if rendered:
            visuals.append(rendered)
    evidence = render_evidence_profile(analysis.get("evidence_profile") or {})
    opportunity = render_opportunity_matrix(analysis.get("opportunity_matrix") or {})
    body = "\n".join([card_visual, f'<div class="adaptive-module-grid">{modules}</div>', *visuals, evidence, opportunity])

    return f"""
    <section class="insight-dashboard adaptive-section" id="{esc(anchor_id)}" aria-labelledby="{esc(anchor_id)}-title">
      <div class="section-head">
        <div>
          <div class="eyebrow">insight dashboard</div>
          <h2 id="{esc(anchor_id)}-title">Paper at a glance, then the real implications</h2>
        </div>
        <p class="section-summary">A fast map of what this paper is, what kind of evidence it offers, and which insight modules matter for this archetype.</p>
      </div>
      <div class="section-body">{body}</div>
    </section>
    """


def render_evidence_profile(profile: dict) -> str:
    claims = profile.get("claims") or []
    if not claims:
        return ""
    cards = []
    for claim in claims:
        support = max(0, min(10, float(claim.get("support", 0) or 0)))
        risk = max(0, min(10, float(claim.get("risk", 0) or 0)))
        cards.append(f"""
        <article class="claim-card">
          <h3>{esc(claim.get("claim", ""))}</h3>
          {f'<p>{esc(claim.get("caption"))}</p>' if claim.get("caption") else ''}
          <div class="claim-bars">
            <div><span>Support</span><b>{support:g}/10</b><div class="bar-track"><span style="width:{support * 10}%"></span></div></div>
            <div><span>Risk</span><b>{risk:g}/10</b><div class="bar-track risk-track"><span style="width:{risk * 10}%"></span></div></div>
          </div>
        </article>
        """)
    return f'<div class="evidence-profile"><div class="visual-title">Evidence profile</div>{"".join(cards)}</div>'


def render_opportunity_matrix(matrix: dict) -> str:
    if not matrix:
        return ""
    visual = {
        "type": "matrix",
        "title": matrix.get("title") or "Opportunity matrix",
        "columns": matrix.get("columns") or [],
        "rows": matrix.get("rows") or [],
        "cells": matrix.get("cells") or [],
    }
    if matrix.get("x_axis") or matrix.get("y_axis"):
        visual["title"] = f'{visual["title"]}: {matrix.get("y_axis", "Value")} x {matrix.get("x_axis", "Feasibility")}'
    return render_visual(visual)


def render_so_what(analysis: dict, anchor_id: str = "section-so_what") -> str:
    so_what = analysis.get("so_what") or {}
    if not so_what:
        return ""
    lens_order = [
        ("research", "Research", ["implications", "open_questions", "next_actions"]),
        ("product", "Product", ["opportunities", "guardrails", "next_actions"]),
        ("business", "Business", ["market_openings", "adoption_blockers", "risks", "next_actions"]),
    ]
    tabs = []
    panels = []
    for i, (key, label, fields) in enumerate(lens_order):
        data = so_what.get(key) or {}
        if not data:
            continue
        tabs.append(f'<button type="button" data-lens-tab="{esc(key)}" aria-controls="lens-{esc(key)}" aria-selected="{str(i == 0).lower()}">{esc(label)}</button>')
        blocks = []
        if data.get("headline"):
            blocks.append(f'<p class="lens-headline">{esc(data["headline"])}</p>')
        for field in fields:
            values = data.get(field) or []
            if isinstance(values, str):
                values = [values]
            if values:
                title = field.replace("_", " ").title()
                blocks.append(f"""
                <div class="lens-list">
                  <div class="label">{esc(title)}</div>
                  <ul>{"".join(f"<li>{esc(value)}</li>" for value in values)}</ul>
                </div>
                """)
        panels.append(f"""
        <article class="lens-panel" id="lens-{esc(key)}" data-lens-panel="{esc(key)}">
          {"".join(blocks)}
        </article>
        """)
    if not tabs or not panels:
        return ""
    return f"""
    <section class="so-what-section adaptive-section" id="{esc(anchor_id)}" aria-labelledby="{esc(anchor_id)}-title">
      <div class="section-head">
        <div>
          <div class="eyebrow">so what</div>
          <h2 id="{esc(anchor_id)}-title">What this means beyond the paper</h2>
        </div>
        <p class="section-summary">The same paper should mean different things to researchers, product builders, and business decision-makers.</p>
      </div>
      <div class="lens-tabs">{"".join(tabs)}</div>
      <div class="lens-panels">{"".join(panels)}</div>
    </section>
    """


def render_summary(analysis: dict, anchor_id: str = "section-plain_summary") -> str:
    summary = analysis.get("plain_summary", "")
    if not summary:
        return ""
    return f"""
    <section class="summary-panel adaptive-section section-plain_summary" id="{esc(anchor_id)}">
      <div class="label">Plain-language summary</div>
      {md_to_html(summary)}
    </section>
    """


def render_visual(visual: dict) -> str:
    visual = normalize_visual(visual)
    vtype = visual.get("type", "cards")
    renderers = {
        "cards": render_cards_visual,
        "flow": render_flow_visual,
        "heatmap": render_heatmap_visual,
        "funnel": render_funnel_visual,
        "matrix": render_matrix_visual,
        "timeline": render_timeline_visual,
        "bar_chart": render_bar_chart_visual,
        "line_chart": render_line_chart_visual,
        "table": render_table_visual,
        "comparison": render_comparison_visual,
    }
    renderer = renderers.get(vtype)
    if not renderer:
        return ""
    body = renderer(visual)
    if not body:
        return ""
    return f'<div class="visual visual-{esc(vtype)}">{body}</div>'


def with_caption_alias(item: dict) -> dict:
    normalized = dict(item)
    if not normalized.get("caption"):
        for key in ("note", "description", "text"):
            if normalized.get(key):
                normalized["caption"] = normalized[key]
                break
    return normalized


def normalize_visual(visual: dict) -> dict:
    normalized = dict(visual or {})
    vtype = normalized.get("type", "cards")
    if vtype == "timeline" and not normalized.get("items") and normalized.get("data"):
        normalized["items"] = [
            with_caption_alias({
                **item,
                "label": item.get("era") or item.get("label", ""),
                "title": item.get("label") or item.get("title") or item.get("era", ""),
            })
            for item in normalized.get("data") or []
        ]
    if vtype in {"flow", "funnel"}:
        if vtype == "funnel" and not normalized.get("steps") and normalized.get("stages"):
            normalized["steps"] = normalized.get("stages")
        normalized["steps"] = [with_caption_alias(step) for step in normalized.get("steps") or []]
    if vtype == "matrix" and not normalized.get("columns") and not normalized.get("rows"):
        coord_cells = normalized.get("cells") or []
        if coord_cells and all(isinstance(cell, dict) and cell.get("x") and cell.get("y") for cell in coord_cells):
            columns = list(dict.fromkeys(str(cell["x"]) for cell in coord_cells))
            rows = list(dict.fromkeys(str(cell["y"]) for cell in coord_cells))
            cell_by_coord = {(str(cell["y"]), str(cell["x"])): cell for cell in coord_cells}
            normalized_cells = []
            for row in rows:
                for column in columns:
                    cell = cell_by_coord.get((row, column), {})
                    items = cell.get("items") or []
                    normalized_cells.append({
                        "label": cell.get("label") or " / ".join(items),
                        "caption": cell.get("caption") or cell.get("note", ""),
                        "tone": cell.get("tone", "neutral"),
                    })
            normalized["columns"] = columns
            normalized["rows"] = rows
            normalized["cells"] = normalized_cells
    return normalized


def visual_title(visual: dict) -> str:
    title = visual.get("title")
    return f'<div class="visual-title">{esc(title)}</div>' if title else ""


def render_cards_visual(visual: dict) -> str:
    items = visual.get("items") or []
    if not items:
        return ""
    cards = []
    for item in items:
        cards.append(f"""
        <div class="metric-card">
          {f'<div class="label">{esc(item.get("label"))}</div>' if item.get("label") else ''}
          {f'<strong>{esc(item.get("value"))}</strong>' if item.get("value") is not None else ''}
          {f'<p>{esc(item.get("caption"))}</p>' if item.get("caption") else ''}
        </div>
        """)
    return f'{visual_title(visual)}<div class="metric-grid">{"".join(cards)}</div>'


def render_flow_visual(visual: dict) -> str:
    steps = visual.get("steps") or []
    if not steps:
        return ""
    nodes = []
    for i, step in enumerate(steps, 1):
        nodes.append(f"""
        <div class="flow-node">
          <span class="step-number">{i}</span>
          <strong>{esc(step.get("label", ""))}</strong>
          {f'<p>{esc(step.get("caption"))}</p>' if step.get("caption") else ''}
        </div>
        """)
    return f'{visual_title(visual)}<div class="flow-grid">{"".join(nodes)}</div>'


def render_heatmap_visual(visual: dict) -> str:
    columns = visual.get("columns") or []
    rows = visual.get("rows") or []
    if not columns or not rows:
        return ""
    cells = ['<div class="heat-cell heat-head">Signal</div>']
    cells += [f'<div class="heat-cell heat-head">{esc(col)}</div>' for col in columns]
    for row in rows:
        cells.append(f'<div class="heat-cell heat-row">{esc(row.get("label", ""))}</div>')
        for value in row.get("cells", []):
            tone = "heat-caution" if str(value).lower() in {"high", "medium", "untested", "gap"} else "heat-win"
            cells.append(f'<div class="heat-cell {tone}">{esc(value)}</div>')
    style = f"--heat-cols:{len(columns) + 1}"
    return f'{visual_title(visual)}<div class="heatmap-grid" style="{style}">{"".join(cells)}</div>'


def render_funnel_visual(visual: dict) -> str:
    steps = visual.get("steps") or []
    if not steps:
        return ""
    rows = []
    for step in steps:
        status = section_class(step.get("status", "neutral"))
        rows.append(f"""
        <div class="funnel-step">
          <strong>{esc(step.get("label", ""))}</strong>
          {f'<p>{esc(step.get("caption"))}</p>' if step.get("caption") else '<p></p>'}
          <span class="status status-{esc(status)}">{esc(step.get("status", "open"))}</span>
        </div>
        """)
    return f'{visual_title(visual)}<div class="funnel-list">{"".join(rows)}</div>'


def render_matrix_visual(visual: dict) -> str:
    columns = visual.get("columns") or []
    rows = visual.get("rows") or []
    cells = visual.get("cells") or []
    if not columns or not rows or not cells:
        return ""
    html_cells = ["<div></div>"]
    html_cells += [f'<div class="axis-label">{esc(col)}</div>' for col in columns]
    idx = 0
    for row in rows:
        html_cells.append(f'<div class="axis-label">{esc(row)}</div>')
        for _ in columns:
            cell = cells[idx] if idx < len(cells) else {}
            idx += 1
            tone = section_class(cell.get("tone", "neutral"))
            html_cells.append(f"""
            <div class="matrix-cell tone-{esc(tone)}">
              <strong>{esc(cell.get("label", ""))}</strong>
              {f'<p>{esc(cell.get("caption"))}</p>' if cell.get("caption") else ''}
            </div>
            """)
    style = f"--matrix-cols:{len(columns) + 1}"
    return f'{visual_title(visual)}<div class="matrix-grid" style="{style}">{"".join(html_cells)}</div>'


def render_timeline_visual(visual: dict) -> str:
    items = visual.get("items") or []
    if not items:
        return ""
    rows = []
    for item in items:
        title = esc(item.get("title", ""))
        if item.get("url"):
            title = render_link(item["url"], title)
        rows.append(f"""
        <div class="timeline-item">
          <span>{esc(item.get("label", ""))}</span>
          <div>
            <strong>{title}</strong>
            {f'<p>{esc(item.get("caption"))}</p>' if item.get("caption") else ''}
          </div>
        </div>
        """)
    return f'{visual_title(visual)}<div class="timeline-list">{"".join(rows)}</div>'


def render_bar_chart_visual(visual: dict) -> str:
    bars = visual.get("bars") or []
    if not bars:
        return ""
    rows = []
    for bar in bars:
        value = float(bar.get("value", 0) or 0)
        max_value = float(bar.get("max", 100) or 100)
        pct = max(0, min(100, round((value / max_value) * 100 if max_value else 0, 2)))
        rows.append(f"""
        <div class="bar-row">
          <div class="bar-title"><span>{esc(bar.get("label", ""))}</span><span>{esc(bar.get("value", ""))}</span></div>
          <div class="bar-track"><span style="width:{pct}%"></span></div>
          {f'<p>{esc(bar.get("caption"))}</p>' if bar.get("caption") else ''}
        </div>
        """)
    return f'{visual_title(visual)}<div class="bar-list">{"".join(rows)}</div>'


def render_line_chart_visual(visual: dict) -> str:
    points = visual.get("points") or []
    if not points:
        return ""
    values = [float(point.get("value", 0) or 0) for point in points]
    max_value = max(float(point.get("max", 0) or 0) for point in points)
    max_value = max(max_value, max(values), 1)
    width = 640
    height = 210
    pad = 34
    usable_w = width - (pad * 2)
    usable_h = height - (pad * 2)
    coords = []
    for i, value in enumerate(values):
        x = pad + (usable_w * (i / (len(points) - 1))) if len(points) > 1 else width / 2
        y = height - pad - ((value / max_value) * usable_h)
        coords.append((round(x, 2), round(y, 2)))
    polyline = " ".join(f"{x},{y}" for x, y in coords)
    circles = "".join(f'<circle cx="{x}" cy="{y}" r="4"></circle>' for x, y in coords)
    labels = []
    for point in points:
        labels.append(f"""
        <div class="line-point">
          <strong>{esc(point.get("label", ""))}</strong>
          <span>{esc(point.get("value", ""))}</span>
          {f'<p>{esc(point.get("caption"))}</p>' if point.get("caption") else ''}
        </div>
        """)
    return f"""
    {visual_title(visual)}
    <svg class="line-chart-svg" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(visual.get("title", "Line chart"))}">
      <line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}"></line>
      <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}"></line>
      <polyline points="{polyline}"></polyline>
      {circles}
    </svg>
    <div class="line-point-grid">{"".join(labels)}</div>
    """


def render_table_visual(visual: dict) -> str:
    columns = visual.get("columns") or []
    rows = visual.get("rows") or []
    if not columns or not rows:
        return ""
    head = "".join(f"<th>{esc(col)}</th>" for col in columns)
    body = []
    for row in rows:
        values = row.get("cells") if isinstance(row, dict) else row
        body.append("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in values) + "</tr>")
    return f'{visual_title(visual)}<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def render_comparison_visual(visual: dict) -> str:
    items = visual.get("items") or []
    rows = visual.get("rows") or []
    if rows:
        columns = list(dict.fromkeys(key for row in rows for key in row.keys()))
        head = "".join(f"<th>{esc(col.replace('_', ' ').title())}</th>" for col in columns)
        body = []
        for row in rows:
            body.append("<tr>" + "".join(f"<td>{esc(row.get(col, ''))}</td>" for col in columns) + "</tr>")
        return f'{visual_title(visual)}<div class="table-wrap comparison-table"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    if not items:
        return ""
    blocks = []
    for item in items:
        blocks.append(f"""
        <div class="compare-card">
          <div class="label">{esc(item.get("label", ""))}</div>
          <p>{esc(item.get("text", ""))}</p>
        </div>
        """)
    return f'{visual_title(visual)}<div class="comparison-grid">{"".join(blocks)}</div>'


def render_learning_path(section: dict) -> str:
    papers = section.get("papers") or []
    if not papers:
        return ""
    cards = []
    for i, paper in enumerate(papers, 1):
        cards.append(f"""
        <article class="learning-card">
          <span class="read-number">{i}</span>
          <h3>{render_link(paper.get("url", ""), paper.get("title", "")) or esc(paper.get("title", ""))}</h3>
          {f'<p>{esc(paper.get("why"))}</p>' if paper.get("why") else ''}
          {f'<p class="why-read"><strong>Read for:</strong> {esc(paper.get("read_for"))}</p>' if paper.get("read_for") else ''}
        </article>
        """)
    return f'<div class="learning-grid">{"".join(cards)}</div>'


def render_quiz(section: dict) -> str:
    questions = section.get("questions") or []
    if not questions:
        return ""
    cards = []
    for i, q in enumerate(questions, 1):
        choices = "".join(f"<li>{esc(choice)}</li>" for choice in q.get("choices", []))
        cards.append(f"""
        <article class="quiz-card">
          <div class="quiz-topic">
            <span>{esc(q.get("category", "Question"))}</span>
            <div class="label">Question {i}</div>
          </div>
          <div>
            <h3>{esc(q.get("question", ""))}</h3>
            <ol class="choices" type="A">{choices}</ol>
            <details class="answer">
              <summary>Show answer</summary>
              <p><strong>Correct:</strong> {esc(q.get("answer", ""))}</p>
              {f'<p>{esc(q.get("explanation"))}</p>' if q.get("explanation") else ''}
            </details>
          </div>
        </article>
        """)
    return f'<div class="quiz-grid">{"".join(cards)}</div>'


def render_generic_section(section: dict, anchor_id: str | None = None) -> str:
    stype = section_class(section.get("type", "section"))
    anchor_id = anchor_id or section_anchor(stype)
    title_id = f"{anchor_id}-title"
    title = section.get("title") or stype.replace("_", " ").title()
    takeaway = section.get("takeaway", "")

    if stype == "learning_path":
        body = render_learning_path(section)
    elif stype == "quiz":
        body = render_quiz(section)
    else:
        pieces = []
        if section.get("content"):
            pieces.append(md_to_html(section["content"]))
        if section.get("bullets"):
            pieces.append("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in section["bullets"]) + "</ul>")
        for visual in section.get("visuals") or []:
            rendered = render_visual(visual)
            if rendered:
                pieces.append(rendered)
        if section.get("caveats"):
            caveats = "".join(f"<li>{esc(x)}</li>" for x in section["caveats"])
            pieces.append(f'<div class="caveat-box"><div class="label">Caveats</div><ul>{caveats}</ul></div>')
        body = "\n".join(pieces)

    if not body.strip():
        return ""

    return f"""
    <section class="adaptive-section section-{esc(stype)}" id="{esc(anchor_id)}" aria-labelledby="{esc(title_id)}">
      <div class="section-head">
        <div>
          <div class="eyebrow">{esc(stype.replace("_", " "))}</div>
          <h2 id="{esc(title_id)}">{esc(title)}</h2>
        </div>
        {f'<p class="section-summary">{esc(takeaway)}</p>' if takeaway else ''}
      </div>
      <div class="section-body">{body}</div>
    </section>
    """


def legacy_sections(analysis: dict) -> list[dict]:
    sections = []
    if analysis.get("plain_summary"):
        sections.append({
            "type": "plain_summary",
            "title": "Plain-language summary",
            "takeaway": analysis.get("headline", ""),
            "content": analysis.get("plain_summary", ""),
        })
    eli5 = analysis.get("eli5") or {}
    if eli5.get("analogy") or eli5.get("text"):
        sections.append({
            "type": "problem_context",
            "title": "Explain it simply",
            "takeaway": eli5.get("analogy", ""),
            "content": eli5.get("text", ""),
        })
    if analysis.get("methods"):
        sections.append({
            "type": "method_walkthrough",
            "title": "What they actually did",
            "content": analysis.get("methods", ""),
        })
    if analysis.get("results"):
        cards = []
        for result in analysis.get("results") or []:
            cards.append({
                "label": result.get("claim", ""),
                "value": result.get("evidence", ""),
                "caption": result.get("caveat", ""),
            })
        sections.append({
            "type": "results_interpretation",
            "title": "Results and caveats",
            "visuals": [{"type": "cards", "items": cards}],
        })
    limitations = analysis.get("limitations") or {}
    caveats = (limitations.get("stated") or []) + (limitations.get("unstated") or [])
    if caveats:
        sections.append({
            "type": "limitations_and_caveats",
            "title": "Limitations",
            "caveats": caveats,
        })
    implications = analysis.get("implications") or {}
    if implications:
        items = []
        for label, values in implications.items():
            if values:
                items.append({
                    "label": label.title(),
                    "value": "",
                    "caption": " ".join(values),
                })
        sections.append({
            "type": "real_world_implications",
            "title": "So what?",
            "visuals": [{"type": "cards", "items": items}],
        })
    return sections


def sections_for_analysis(analysis: dict) -> list[dict]:
    plan = analysis.get("report_plan") or {}
    sections = plan.get("sections") or []
    if sections:
        return sections
    return legacy_sections(analysis)


def split_orientation_sections(sections: list[dict]) -> tuple[list[dict], list[dict]]:
    """Put just enough paper context before insight-heavy visuals."""
    if not sections:
        return [], []
    orientation_types = {"problem_context", "core_contribution"}
    orientation = []
    idx = 0
    while idx < len(sections) and len(orientation) < 2:
        stype = section_class(sections[idx].get("type", "section"))
        if stype not in orientation_types:
            break
        orientation.append(sections[idx])
        idx += 1
    if not orientation:
        orientation = [sections[0]]
        idx = 1
    return orientation, sections[idx:]


def next_anchor_id(base: str, used: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def section_nav_label(section: dict) -> str:
    if section.get("title"):
        return str(section["title"])
    stype = section_class(section.get("type", "section"))
    if stype == "plain_summary":
        return "Plain-language summary"
    return re.sub(r"[-_]+", " ", stype).title()


def build_report_blocks(analysis: dict) -> list[dict]:
    sections = sections_for_analysis(analysis)
    orientation_sections, deep_dive_sections = split_orientation_sections(sections)
    used_ids: set[str] = set()
    blocks: list[dict] = []

    def add_block(base_id: str, label: str, renderer) -> None:
        anchor_id = next_anchor_id(base_id, used_ids)
        html_text = renderer(anchor_id)
        if not html_text.strip():
            return
        used_ids.add(anchor_id)
        blocks.append({
            "id": anchor_id,
            "label": label,
            "html": html_text,
        })

    add_block("section-plain_summary", "Plain-language summary", lambda anchor: render_summary(analysis, anchor))
    for section in orientation_sections:
        add_block(
            section_anchor(section.get("type", "section")),
            section_nav_label(section),
            lambda anchor, item=section: render_generic_section(item, anchor),
        )
    add_block("section-insight_dashboard", "Insight dashboard", lambda anchor: render_insight_dashboard(analysis, anchor))
    add_block("section-so_what", "So what", lambda anchor: render_so_what(analysis, anchor))
    for section in deep_dive_sections:
        add_block(
            section_anchor(section.get("type", "section")),
            section_nav_label(section),
            lambda anchor, item=section: render_generic_section(item, anchor),
        )
    return blocks


def render_section_menu(blocks: list[dict]) -> str:
    entries = [(block["id"], block["label"]) for block in blocks if block.get("id")]
    if not entries:
        return ""
    links = []
    for i, (anchor_id, label) in enumerate(entries):
        active_class = " is-active" if i == 0 else ""
        current = ' aria-current="true"' if i == 0 else ""
        links.append(
            f'<a class="section-link{active_class}" href="#{esc(anchor_id)}" '
            f'data-section-link="{esc(anchor_id)}"{current}>{esc(label)}</a>'
        )
    return f"""
    <nav class="section-menu" aria-label="Report sections">
      <div class="reading-progress-track" role="progressbar" aria-label="Reading progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
        <span id="reading-progress-bar"></span>
      </div>
      <div class="section-menu-links">{"".join(links)}</div>
    </nav>
    """


def build_html(analysis: dict, slug: str) -> str:
    paper = analysis.get("paper", {})
    title = paper.get("title") or "Paper Report"
    blocks = build_report_blocks(analysis)
    html_text = TEMPLATE.format(
        title=esc(title),
        css=CSS,
        hero=render_hero(analysis, slug),
        section_menu=render_section_menu(blocks),
        content="\n".join(block["html"] for block in blocks),
    )
    return "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"


class EmailConfigError(ValueError):
    pass


def parse_dotenv_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def load_dotenv(path: Path, environ: dict | None = None) -> None:
    if environ is None:
        environ = os.environ
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in environ:
            continue
        environ[key] = parse_dotenv_value(value)


def env_file_status(path: Path) -> str:
    if path.exists():
        return f"Loaded local env file: {path}"
    return f"Local env file not found: {path}"


def email_config_from_env(environ: dict | None = None, config: dict | None = None) -> dict:
    if environ is None:
        environ = os.environ
    config = config or load_app_config()
    smtp_settings = email_smtp_settings(config)
    provider_name = (config.get("email") or {}).get("provider")
    provider_settings = ((config.get("email") or {}).get("providers") or {}).get(provider_name, {})
    host_env = smtp_settings.get("host_env", "REPORT_SMTP_HOST")
    port_env = smtp_settings.get("port_env", "REPORT_SMTP_PORT")
    username_env = smtp_settings.get("username_env", "REPORT_SMTP_USERNAME")
    password_env = smtp_settings.get("password_env", "REPORT_SMTP_PASSWORD")
    from_env = smtp_settings.get("from_env", "REPORT_EMAIL_FROM")
    default_host = smtp_settings.get("default_host") or provider_settings.get("host")
    required_email_env = (username_env, password_env, from_env)
    if not default_host:
        required_email_env = (host_env, *required_email_env)
    missing = [key for key in required_email_env if not environ.get(key)]
    if missing:
        raise EmailConfigError("Missing email configuration: " + ", ".join(missing))
    try:
        port = int(environ.get(port_env) or provider_settings.get("port") or smtp_settings.get("default_port", 587))
    except ValueError as exc:
        raise EmailConfigError(f"{port_env} must be an integer.") from exc
    starttls_ports = smtp_settings.get("starttls_ports") or provider_settings.get("starttls_ports", [587])
    return {
        "host": environ.get(host_env) or default_host,
        "port": port,
        "username": environ[username_env],
        "password": environ[password_env],
        "from": environ[from_env],
        "starttls_ports": [int(value) for value in starttls_ports],
    }


def build_report_email(analysis: dict, report_path: Path, sender: str, recipient: str) -> EmailMessage:
    title = (analysis.get("paper") or {}).get("title") or "Paper Report"
    message = EmailMessage()
    message["Subject"] = f"Paper report: {title}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join([
        "Attached is the generated research paper report.",
        "",
        f"Title: {title}",
        f"Report file: {report_path.name}",
        "",
        "Open the attached HTML file in a browser for the full interactive report.",
    ]))
    content_type = mimetypes.guess_type(report_path.name)[0] or "text/html"
    _, subtype = content_type.split("/", 1)
    message.add_attachment(
        report_path.read_text(encoding="utf-8"),
        subtype=subtype,
        filename=report_path.name,
    )
    return message


def send_report_email(
    analysis: dict,
    report_path: Path,
    recipient: str,
    environ: dict | None = None,
    config: dict | None = None,
) -> None:
    email_config = email_config_from_env(environ, config=config)
    message = build_report_email(analysis, report_path, email_config["from"], recipient)
    with smtplib.SMTP(email_config["host"], email_config["port"], timeout=30) as smtp:
        if email_config["port"] in email_config["starttls_ports"]:
            smtp.starttls()
        smtp.login(email_config["username"], email_config["password"])
        smtp.send_message(message)


def resolve_email_recipient(cli_recipient: str | None, environ: dict | None = None) -> str | None:
    if cli_recipient and cli_recipient.strip():
        return cli_recipient.strip()
    if environ is None:
        environ = os.environ
    recipient = environ.get("REPORT_EMAIL_TO")
    return recipient.strip() if recipient and recipient.strip() else None


def email_skip_message(environ: dict | None = None) -> str:
    if environ is None:
        environ = os.environ
    if "REPORT_EMAIL_TO" in environ and not (environ.get("REPORT_EMAIL_TO") or "").strip():
        return "Email delivery skipped: REPORT_EMAIL_TO is blank in .env or environment."
    return "Email delivery skipped: set REPORT_EMAIL_TO in .env or pass --email-to."


CSS = """
:root {
  --paper: #f7f4ed;
  --paper-2: #eef6f3;
  --ink: #17211d;
  --muted: #5d6a63;
  --card: #ffffff;
  --line: #d9dfd8;
  --green: #2e6f4a;
  --green-2: #dcebe4;
  --amber: #b56516;
  --amber-2: #fff0d8;
  --blue: #2d4a8a;
  --blue-2: #e7edf8;
  --red: #9f3f33;
  --red-2: #f8e4df;
  --shadow: 0 18px 45px rgba(43, 55, 48, 0.09);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: linear-gradient(180deg, #fbf8ef 0%, #eef6f3 46%, #f8faf7 100%);
  color: var(--ink);
  line-height: 1.5;
}
a { color: var(--blue); text-decoration: none; }
a:hover { text-decoration: underline; }
code { background: rgba(23, 33, 29, 0.08); border-radius: 4px; padding: 1px 5px; }
.page { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
.hero {
  min-height: auto;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(310px, 0.7fr);
  gap: 30px;
  align-items: center;
  padding: 20px 0 14px;
}
.eyebrow, .label {
  color: var(--green);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}
h1 {
  margin: 10px 0 12px;
  max-width: 820px;
  font-size: clamp(28px, 4vw, 48px);
  line-height: 1.06;
  letter-spacing: 0;
}
.hero-lede { max-width: 720px; margin: 0; color: #2d3732; font-size: clamp(16px, 1.7vw, 19px); }
.hero-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.pill {
  display: inline-flex;
  border: 1px solid rgba(46, 111, 74, 0.2);
  border-radius: 999px;
  padding: 9px 13px;
  background: rgba(255, 255, 255, 0.66);
  color: #26352e;
  font-size: 14px;
  font-weight: 700;
}
.muted-pill { background: var(--amber-2); border-color: #edcf9f; }
.source-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  border-radius: 8px;
  padding: 9px 14px;
  background: var(--ink);
  color: #fff;
  font-weight: 900;
}
.source-button:hover { color: #fff; text-decoration: none; background: #26352e; }
.source-line { margin-top: 18px; color: var(--muted); font-size: 14px; }
.hero-board, .summary-panel, .adaptive-section {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: var(--shadow);
}
.hero-board { padding: 20px; }
.hero-board-title { font-size: 22px; font-weight: 900; line-height: 1.18; margin: 10px 0; }
.hero-board p { color: var(--muted); }
.slug { font-size: 13px; }
.section-menu {
  position: sticky;
  top: 0;
  z-index: 30;
  margin: 6px 0 14px;
  border-bottom: 1px solid rgba(217, 223, 216, 0.86);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 22px rgba(43, 55, 48, 0.08);
  backdrop-filter: blur(14px);
}
.reading-progress-track {
  width: 100%;
  height: 3px;
  overflow: hidden;
  background: rgba(231, 236, 232, 0.9);
}
#reading-progress-bar {
  display: block;
  width: 0%;
  height: 100%;
  background: var(--green);
  transition: width 120ms ease-out;
}
.section-menu-links {
  display: flex;
  gap: 18px;
  overflow-x: auto;
  padding: 5px 2px 6px;
  scroll-padding-inline: 2px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.section-menu-links::-webkit-scrollbar { display: none; height: 0; }
.section-menu-links::-webkit-scrollbar-thumb { background: #c8d1ca; border-radius: 999px; }
.section-link {
  flex: 0 0 auto;
  max-width: min(270px, 72vw);
  overflow: hidden;
  border-bottom: 2px solid transparent;
  padding: 3px 0 5px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 800;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.section-link:hover { text-decoration: none; color: var(--ink); }
.section-link.is-active {
  border-color: var(--blue);
  color: var(--blue);
}
.summary-panel { padding: 22px; margin: 18px 0 28px; }
.summary-panel p { max-width: 880px; font-size: 18px; }
.adaptive-section { margin: 24px 0; padding: 22px; }
.summary-panel, .adaptive-section { scroll-margin-top: 74px; }
.insight-dashboard {
  background: rgba(255, 255, 255, 0.92);
}
.adaptive-module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 10px;
  margin-top: 14px;
}
.module-card, .claim-card, .lens-panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfa;
  padding: 14px;
}
.module-card strong, .claim-card h3 { display: block; margin: 0 0 6px; }
.module-card p, .claim-card p { margin: 0; color: var(--muted); font-size: 14px; }
.evidence-profile {
  margin-top: 16px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
.claim-card + .claim-card { margin-top: 10px; }
.claim-bars {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 12px;
}
.claim-bars span { color: var(--muted); font-size: 12px; font-weight: 900; text-transform: uppercase; }
.claim-bars b { float: right; font-size: 13px; }
.risk-track span { background: var(--amber); }
.lens-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.lens-tabs button {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 14px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  font-weight: 900;
}
.lens-tabs button[aria-selected="true"] {
  background: var(--blue);
  color: #fff;
  border-color: var(--blue);
}
.lens-panels {
  display: grid;
  gap: 10px;
}
.lens-panel[hidden] { display: none; }
.lens-headline {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 900;
}
.lens-list { margin-top: 12px; }
.lens-list ul { margin: 8px 0 0; padding-left: 20px; }
.section-head {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(240px, 0.52fr);
  gap: 24px;
  align-items: end;
  margin-bottom: 18px;
}
.section-head h2 { margin: 6px 0 0; max-width: 780px; font-size: clamp(27px, 4vw, 44px); line-height: 1.08; }
.section-summary { margin: 0; color: var(--muted); font-size: 16px; }
.section-body > p { max-width: 820px; }
.visual {
  margin-top: 16px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
.visual-title { margin-bottom: 12px; color: var(--ink); font-weight: 900; font-size: 18px; }
.metric-grid, .learning-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.metric-card, .learning-card, .flow-node, .compare-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfa;
  padding: 14px;
}
.metric-card strong { display: block; font-size: 26px; line-height: 1.1; margin: 8px 0; }
.metric-card p, .learning-card p, .flow-node p, .compare-card p { margin: 6px 0 0; color: var(--muted); font-size: 14px; }
.flow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}
.step-number, .read-number {
  display: inline-grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  background: var(--green-2);
  color: var(--green);
  font-weight: 900;
}
.flow-node strong { display: block; margin-top: 10px; }
.heatmap-grid {
  display: grid;
  grid-template-columns: repeat(var(--heat-cols), minmax(120px, 1fr));
  gap: 6px;
}
.heat-cell {
  min-height: 54px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfa;
  font-size: 13px;
}
.heat-head { background: var(--ink); color: #fff; font-weight: 900; text-align: center; }
.heat-row { font-weight: 900; }
.heat-win { background: var(--green-2); color: #183529; border-color: #b9d5c6; }
.heat-caution { background: var(--amber-2); color: #6d3f12; border-color: #edcf9f; }
.funnel-list { display: grid; gap: 8px; }
.funnel-step {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr) 112px;
  gap: 12px;
  align-items: center;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfa;
}
.funnel-step p { margin: 0; color: var(--muted); font-size: 14px; }
.status {
  justify-self: end;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 900;
  text-align: center;
  background: var(--blue-2);
  color: var(--blue);
}
.status-supported, .status-good { background: var(--green-2); color: var(--green); }
.status-caution { background: var(--amber-2); color: var(--amber); }
.status-gap, .status-bad { background: var(--red-2); color: var(--red); }
.matrix-grid {
  display: grid;
  grid-template-columns: repeat(var(--matrix-cols), minmax(130px, 1fr));
  gap: 8px;
}
.axis-label {
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 12px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.matrix-cell {
  min-height: 118px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfa;
}
.matrix-cell strong { display: block; margin-bottom: 6px; }
.matrix-cell p { margin: 0; color: var(--muted); font-size: 13px; }
.tone-good { background: var(--green-2); border-color: #b9d5c6; }
.tone-caution { background: var(--amber-2); border-color: #edcf9f; }
.tone-bad { background: var(--red-2); border-color: #e1b9b3; }
.timeline-list { display: grid; gap: 10px; }
.timeline-item {
  display: grid;
  grid-template-columns: 94px minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfa;
}
.timeline-item > span {
  display: inline-flex;
  justify-content: center;
  height: max-content;
  border-radius: 999px;
  padding: 6px 10px;
  background: var(--blue-2);
  color: var(--blue);
  font-weight: 900;
}
.bar-list { display: grid; gap: 12px; }
.bar-title { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 8px; font-weight: 900; }
.bar-track { height: 14px; overflow: hidden; border-radius: 999px; background: #e7ece8; }
.bar-track span { display: block; height: 100%; border-radius: inherit; background: var(--green); }
.bar-row p { margin: 8px 0 0; color: var(--muted); font-size: 13px; }
.line-chart-svg {
  width: 100%;
  min-height: 180px;
  border-radius: 8px;
  background: linear-gradient(180deg, #fbfcfa 0%, #f3f7f5 100%);
}
.line-chart-svg line { stroke: var(--line); stroke-width: 2; }
.line-chart-svg polyline { fill: none; stroke: var(--blue); stroke-width: 4; stroke-linejoin: round; stroke-linecap: round; }
.line-chart-svg circle { fill: #fff; stroke: var(--blue); stroke-width: 3; }
.line-point-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.line-point {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  background: #fbfcfa;
}
.line-point strong, .line-point span { display: block; }
.line-point span { color: var(--blue); font-weight: 900; }
.line-point p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid var(--line); padding: 10px; text-align: left; vertical-align: top; }
th { background: var(--ink); color: #fff; }
.comparison-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.caveat-box {
  margin-top: 16px;
  padding: 14px 16px;
  border-left: 5px solid var(--amber);
  border-radius: 8px;
  background: var(--amber-2);
}
.learning-card { display: grid; gap: 10px; }
.learning-card h3 { margin: 0; font-size: 20px; line-height: 1.18; }
.why-read { padding: 11px; border-radius: 8px; background: var(--paper-2); color: #26352e; }
.quiz-grid { display: grid; gap: 12px; }
.quiz-card {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
.quiz-topic { display: flex; flex-direction: column; gap: 8px; }
.quiz-topic span {
  width: max-content;
  max-width: 100%;
  border-radius: 999px;
  padding: 6px 10px;
  background: var(--blue-2);
  color: var(--blue);
  font-size: 12px;
  font-weight: 900;
}
.quiz-card h3 { margin: 0; font-size: 20px; line-height: 1.25; }
.choices { display: grid; gap: 8px; margin: 14px 0; padding: 0; list-style: none; }
.choices li { padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: #fbfcfa; }
.answer { border-radius: 8px; background: var(--green-2); color: #183529; padding: 10px 12px; }
.answer summary { cursor: pointer; font-weight: 900; }
.answer p { margin: 8px 0 0; }
.footer { padding: 32px 0 56px; color: var(--muted); font-size: 14px; }
@media (max-width: 900px) {
  .hero, .section-head { grid-template-columns: 1fr; }
  .heatmap-grid, .matrix-grid { grid-template-columns: 1fr; }
  .heat-head { text-align: left; }
  .axis-label { place-items: start; }
}
@media (max-width: 640px) {
  .page { width: min(100% - 22px, 1180px); }
  .hero { min-height: auto; padding-top: 28px; }
  .section-menu { margin-top: 4px; }
  .section-menu-links { gap: 14px; padding-block: 5px 6px; }
  .section-link { max-width: 78vw; font-size: 12px; }
  .summary-panel, .adaptive-section { scroll-margin-top: 76px; }
  .funnel-step, .timeline-item, .quiz-card { grid-template-columns: 1fr; }
  .status { justify-self: start; }
}
"""


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<main class="page">
{section_menu}
{hero}
{content}
<footer class="footer">
  Generated from structured analysis as a static visual briefing.
</footer>
</main>
<script>
(() => {{
  const tabs = Array.from(document.querySelectorAll("[data-lens-tab]"));
  if (!tabs.length) return;
  const panels = Array.from(document.querySelectorAll("[data-lens-panel]"));
  const activate = (key) => {{
    tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.lensTab === key)));
    panels.forEach((panel) => {{ panel.hidden = panel.dataset.lensPanel !== key; }});
  }};
  tabs.forEach((tab) => tab.addEventListener("click", () => activate(tab.dataset.lensTab)));
  activate(tabs[0].dataset.lensTab);
}})();
(() => {{
  const links = Array.from(document.querySelectorAll("[data-section-link]"));
  if (!links.length) return;

  const targets = links
    .map((link) => document.getElementById(link.dataset.sectionLink))
    .filter(Boolean);
  const progressBar = document.getElementById("reading-progress-bar");
  const progressTrack = document.querySelector(".reading-progress-track");
  const menu = document.querySelector(".section-menu");

  const setActiveSection = (id) => {{
    links.forEach((link) => {{
      const active = link.dataset.sectionLink === id;
      link.classList.toggle("is-active", active);
      if (active) {{
        link.setAttribute("aria-current", "true");
        link.scrollIntoView({{ block: "nearest", inline: "center" }});
      }} else {{
        link.removeAttribute("aria-current");
      }}
    }});
  }};

  const updateActiveSection = () => {{
    if (!targets.length) return;
    const marker = (menu ? menu.getBoundingClientRect().bottom : 0) + 48;
    let activeTarget = targets[0];

    for (const target of targets) {{
      const rect = target.getBoundingClientRect();
      if (rect.top <= marker && rect.bottom > marker) {{
        activeTarget = target;
        break;
      }}
      if (rect.top <= marker) {{
        activeTarget = target;
      }}
    }}

    setActiveSection(activeTarget.id);
  }};

  links.forEach((link) => {{
    link.addEventListener("click", (event) => {{
      const target = document.getElementById(link.dataset.sectionLink);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({{ behavior: "smooth", block: "start" }});
      window.history.pushState(null, "", `#${{link.dataset.sectionLink}}`);
      setActiveSection(link.dataset.sectionLink);
    }});
  }});

  const updateReadingProgress = () => {{
    const doc = document.documentElement;
    const scrollTop = window.scrollY || doc.scrollTop || 0;
    const scrollable = Math.max(0, doc.scrollHeight - window.innerHeight);
    const percent = scrollable > 0 ? Math.round(Math.min(100, Math.max(0, (scrollTop / scrollable) * 100))) : 100;
    if (progressBar) progressBar.style.width = `${{percent}}%`;
    if (progressTrack) progressTrack.setAttribute("aria-valuenow", String(percent));
  }};

  let navFrame = null;
  const requestNavUpdate = () => {{
    if (navFrame) return;
    navFrame = window.requestAnimationFrame(() => {{
      navFrame = null;
      updateActiveSection();
      updateReadingProgress();
    }});
  }};

  if ("IntersectionObserver" in window) {{
    const observer = new IntersectionObserver(() => {{
      requestNavUpdate();
    }}, {{
      rootMargin: "-30% 0px -58% 0px",
      threshold: [0, 0.12, 0.35, 0.65],
    }});
    targets.forEach((target) => observer.observe(target));
  }}

  updateActiveSection();
  updateReadingProgress();
  window.addEventListener("scroll", requestNavUpdate, {{ passive: true }});
  window.addEventListener("resize", requestNavUpdate);
}})();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to analysis JSON")
    parser.add_argument("--output", required=True, help="Path for generated HTML")
    parser.add_argument("--slug", default=None, help="Slug for display and stable report identity")
    parser.add_argument("--email-to", default=None, help="Email the generated report.html to this recipient")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, type=Path, help="Path to structured generator config JSON")
    parser.add_argument("--env-file", default=DEFAULT_CONFIG_PATH.parents[1] / ".env", type=Path, help="Path to local .env secrets file")
    args = parser.parse_args()

    config = load_app_config(args.config)
    load_dotenv(args.env_file)
    print(env_file_status(args.env_file))

    with open(args.input, encoding="utf-8") as f:
        analysis = json.load(f)

    if not analysis.get("paper", {}).get("title"):
        print("ERROR: analysis.paper.title is required", file=sys.stderr)
        return 1
    if not analysis.get("headline"):
        print("ERROR: analysis.headline is required", file=sys.stderr)
        return 1

    slug = args.slug or analysis.get("slug") or slugify(analysis["paper"]["title"])
    html_text = build_html(analysis, slug)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {output} ({len(html_text):,} bytes) - slug: {slug}")
    email_recipient = resolve_email_recipient(args.email_to)
    if email_recipient:
        print(f"Email delivery configured for {email_recipient}")
        try:
            send_report_email(analysis, output, email_recipient, config=config)
        except EmailConfigError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"ERROR: Email send failed: {exc}", file=sys.stderr)
            return 1
        print(f"Emailed report to {email_recipient}")
    else:
        print(email_skip_message())
    return 0


if __name__ == "__main__":
    sys.exit(main())
