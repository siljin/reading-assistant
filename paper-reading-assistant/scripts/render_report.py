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
import re
import sys
from pathlib import Path


def esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:60] or "paper"


def section_class(section_type: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", section_type or "section").strip("-")
    return clean or "section"


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


def render_hero(analysis: dict, slug: str) -> str:
    paper = analysis.get("paper", {})
    plan = analysis.get("report_plan", {}) or {}
    title = paper.get("title") or "Untitled paper"
    headline = analysis.get("headline") or "A structured visual briefing for this paper."
    authors = ", ".join(paper.get("authors") or [])
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
    reader_goal = plan.get("reader_goal") or "understand and evaluate the paper"

    return f"""
    <section class="hero adaptive-section section-title" aria-labelledby="title">
      <div>
        <div class="eyebrow">Research paper visual briefing</div>
        <h1 id="title">{esc(title)}</h1>
        <p class="hero-lede">{esc(headline)}</p>
        <div class="hero-actions">
          <span class="pill">{esc(reader_goal)}</span>
          {f'<span class="pill muted-pill">{esc(meta)}</span>' if meta else ''}
        </div>
        <p class="source-line">
          {f'{esc(authors)}<br>' if authors else ''}
          {link}
        </p>
      </div>
      <aside class="hero-board">
        <div class="label">Report recipe</div>
        <p class="hero-board-title">Adaptive structure, consistent design.</p>
        <p>This page is generated from <code>analysis.json</code>. The paper decides the section order; the renderer keeps the layout readable.</p>
        <p class="slug">Slug: <code>{esc(slug)}</code></p>
      </aside>
    </section>
    """


def render_summary(analysis: dict) -> str:
    summary = analysis.get("plain_summary", "")
    if not summary:
        return ""
    return f"""
    <section class="summary-panel adaptive-section section-plain_summary">
      <div class="label">Plain-language summary</div>
      {md_to_html(summary)}
    </section>
    """


def render_visual(visual: dict) -> str:
    vtype = visual.get("type", "cards")
    renderers = {
        "cards": render_cards_visual,
        "flow": render_flow_visual,
        "heatmap": render_heatmap_visual,
        "funnel": render_funnel_visual,
        "matrix": render_matrix_visual,
        "timeline": render_timeline_visual,
        "bar_chart": render_bar_chart_visual,
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


def render_generic_section(section: dict) -> str:
    stype = section_class(section.get("type", "section"))
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
    <section class="adaptive-section section-{esc(stype)}" aria-labelledby="section-{esc(stype)}">
      <div class="section-head">
        <div>
          <div class="eyebrow">{esc(stype.replace("_", " "))}</div>
          <h2 id="section-{esc(stype)}">{esc(title)}</h2>
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


def build_html(analysis: dict, slug: str) -> str:
    paper = analysis.get("paper", {})
    title = paper.get("title") or "Paper Report"
    sections_html = "\n".join(render_generic_section(s) for s in sections_for_analysis(analysis))
    html_text = TEMPLATE.format(
        title=esc(title),
        css=CSS,
        hero=render_hero(analysis, slug),
        summary=render_summary(analysis),
        sections=sections_html,
    )
    return "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"


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
  min-height: 82vh;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(310px, 0.7fr);
  gap: 30px;
  align-items: center;
  padding: 44px 0 30px;
}
.eyebrow, .label {
  color: var(--green);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}
h1 {
  margin: 12px 0 16px;
  max-width: 820px;
  font-size: clamp(40px, 7vw, 82px);
  line-height: 0.98;
  letter-spacing: 0;
}
.hero-lede { max-width: 720px; margin: 0; color: #2d3732; font-size: clamp(18px, 2vw, 23px); }
.hero-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
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
.summary-panel { padding: 22px; margin: 18px 0 28px; }
.summary-panel p { max-width: 880px; font-size: 18px; }
.adaptive-section { margin: 24px 0; padding: 22px; }
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
{hero}
{summary}
{sections}
<footer class="footer">
  Generated from structured analysis as a static visual briefing.
</footer>
</main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to analysis JSON")
    parser.add_argument("--output", required=True, help="Path for generated HTML")
    parser.add_argument("--slug", default=None, help="Slug for display and stable report identity")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        analysis = json.load(f)

    if not analysis.get("paper", {}).get("title"):
        print("ERROR: analysis.paper.title is required", file=sys.stderr)
        sys.exit(1)
    if not analysis.get("headline"):
        print("ERROR: analysis.headline is required", file=sys.stderr)
        sys.exit(1)

    slug = args.slug or analysis.get("slug") or slugify(analysis["paper"]["title"])
    html_text = build_html(analysis, slug)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {output} ({len(html_text):,} bytes) - slug: {slug}")


if __name__ == "__main__":
    main()
