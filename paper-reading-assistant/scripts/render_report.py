#!/usr/bin/env python3
"""
render_report.py — Render a paper analysis JSON into a self-contained HTML report.

Usage:
    python render_report.py --input analysis.json --output report.html [--slug my-paper]

The report is designed so a reader with NO background in the paper's field can
follow it: an ELI5 analogy, a jargon decoder, plain-language figures, and
optional interactive demos/simulations sit alongside the deep skeptical analysis.

Notes persist to disk: when the report is opened through `serve.py`, the notes
editor saves to `papers/<slug>/notes.md`. Opened directly from the filesystem it
falls back to browser localStorage, and a "Download notes.md" button always works.

JSON schema (all fields optional unless marked required):

{
  "paper": {                              # required
    "title": "...",                       # required
    "authors": ["Name 1", "Name 2"],
    "affiliations": ["MIT", "Google"],    # parallel to authors, optional
    "venue": "NeurIPS 2024",
    "year": 2024,
    "url": "https://arxiv.org/abs/...",
    "code_url": "https://github.com/...",
    "data_url": null
  },
  "slug": "attention-is-all-you-need",    # used for notes persistence; CLI --slug wins
  "headline": "One-sentence sharpest takeaway.",      # required
  "eli5": {                               # explain-like-I'm-new — the simplifier
    "analogy": "It's like ... .",
    "text": "Two or three plain sentences. No jargon."
  },
  "plain_summary": "Markdown allowed (basic).",       # required
  "glossary": [                           # jargon decoder — rendered as an accordion
    {"term": "RLHF", "plain": "Teaching a model with human thumbs-up/down."}
  ],
  "figures": [                            # plain-language visuals
    {"src": "fig1.png", "alt": "...", "caption": "What this picture is telling you, in plain words."}
  ],
  "demos": [                              # interactive simulations (inline HTML/JS, sandboxed)
    {"title": "Try it", "caption": "Drag the slider to see X.", "html": "<input ...><script>...</script>"}
  ],
  "novelty": {
    "type": "methodological",            # one of: conceptual, methodological, empirical, engineering
    "before": "Before this paper, ...",
    "after":  "This paper shows ..."
  },
  "methods": "Markdown bullets or prose.",
  "results": [
    {"claim": "...", "evidence": "...", "caveat": "..."}
  ],
  "limitations": {
    "stated":   ["..."],
    "unstated": ["..."]
  },
  "implementation": {
    "feasibility": "afternoon | week | quarter | research project",
    "requirements": ["..."],
    "cheapest_validation": "Description of the smallest viable test."
  },
  "implications": {
    "research":   ["..."],
    "practice":   ["..."],
    "personal":   ["..."]                # optional
  },
  "knowledge_graph": {
    "nodes": [
      {"id": "transformer", "label": "Transformer", "type": "technique"}
    ],
    "edges": [
      {"from": "this_paper", "to": "transformer", "label": "builds_on"}
    ]
  },
  "people": [
    {
      "name": "Jane Doe",
      "role": "First author, PhD student at MIT",
      "why":  "Knows the experiments that didn't make the paper.",
      "connection_path": "2nd-degree: via Sam Lee (your connection at MIT)",
      "linkedin": "https://linkedin.com/in/janedoe",
      "search_hint": null
    }
  ]
}

Node types recognized for color: technique, dataset, prior_work, claim, domain, concept.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path


# ---------- minimal markdown ----------------------------------------------

def md_to_html(text: str) -> str:
    """Tiny markdown subset: bold, italic, inline code, bullet lists, paragraphs."""
    if not text:
        return ""
    text = html.escape(text)
    # inline
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    lines = text.split("\n")
    out = []
    in_list = False
    para: list[str] = []

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


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


# ---------- section renderers ---------------------------------------------

def render_header(paper: dict) -> str:
    title = esc(paper.get("title", "Untitled"))
    authors = paper.get("authors") or []
    affs = paper.get("affiliations") or []
    if authors:
        if affs and len(affs) == len(authors):
            byline = ", ".join(f"{esc(a)} <span class='aff'>({esc(f)})</span>"
                               for a, f in zip(authors, affs))
        else:
            byline = ", ".join(esc(a) for a in authors)
    else:
        byline = ""

    meta_bits = []
    if paper.get("venue"):
        meta_bits.append(esc(paper["venue"]))
    if paper.get("year"):
        meta_bits.append(esc(paper["year"]))
    meta = " · ".join(meta_bits)

    links = []
    if paper.get("url"):
        links.append(f'<a href="{esc(paper["url"])}" target="_blank">Paper ↗</a>')
    if paper.get("code_url"):
        links.append(f'<a href="{esc(paper["code_url"])}" target="_blank">Code ↗</a>')
    if paper.get("data_url"):
        links.append(f'<a href="{esc(paper["data_url"])}" target="_blank">Data ↗</a>')

    return f"""
    <header class="paper-header">
      <h1>{title}</h1>
      {f'<p class="byline">{byline}</p>' if byline else ''}
      {f'<p class="meta">{meta}</p>' if meta else ''}
      {f'<p class="links">{" · ".join(links)}</p>' if links else ''}
    </header>
    """


def render_headline(headline: str) -> str:
    if not headline:
        return ""
    return f"""
    <section class="card headline">
      <div class="label">TL;DR</div>
      <p>{esc(headline)}</p>
    </section>
    """


def render_section(title: str, body_html: str, label: str | None = None,
                   extra_class: str = "") -> str:
    if not body_html.strip():
        return ""
    label_html = f'<div class="label">{esc(label)}</div>' if label else ""
    cls = ("card " + extra_class).strip()
    return f"""
    <section class="{cls}">
      {label_html}
      <h2>{esc(title)}</h2>
      {body_html}
    </section>
    """


def render_eli5(eli5: dict) -> str:
    """The simplifier: an analogy + a no-jargon explanation, up top, hard to miss."""
    if not eli5:
        return ""
    analogy = eli5.get("analogy", "")
    text = eli5.get("text", "")
    if not analogy and not text:
        return ""
    body = ""
    if analogy:
        body += f'<p class="analogy"><span class="analogy-mark">Think of it like</span> {esc(analogy)}</p>'
    if text:
        body += md_to_html(text)
    return render_section("Explain it simply", body, label="No background needed",
                          extra_class="eli5")


def render_glossary(glossary) -> str:
    """Jargon decoder — click a term to reveal a plain definition."""
    if not glossary:
        return ""
    items = []
    for g in glossary:
        term = esc(g.get("term", ""))
        plain = esc(g.get("plain", ""))
        if not term:
            continue
        items.append(f"""
          <details class="glossary-item">
            <summary>{term}</summary>
            <p>{plain}</p>
          </details>
        """)
    if not items:
        return ""
    return render_section("Jargon decoder", "".join(items),
                          label="Tap any term", extra_class="glossary")


def render_figures(figures) -> str:
    if not figures:
        return ""
    blocks = []
    for f in figures:
        src = f.get("src")
        alt = esc(f.get("alt", ""))
        caption = esc(f.get("caption", ""))
        img = f'<img src="{esc(src)}" alt="{alt}" loading="lazy">' if src else ""
        blocks.append(f"""
          <figure class="paper-figure">
            {img}
            {f'<figcaption>{caption}</figcaption>' if caption else ''}
          </figure>
        """)
    return render_section("The picture, explained", "".join(blocks),
                          label="Visual", extra_class="figures")


def render_demos(demos) -> str:
    """Interactive simulations. Each demo's HTML runs inside a sandboxed iframe so
    it cannot touch the rest of the page or the notes store."""
    if not demos:
        return ""
    blocks = []
    for i, d in enumerate(demos):
        title = esc(d.get("title", f"Demo {i + 1}"))
        caption = esc(d.get("caption", ""))
        inner = d.get("html", "")
        # Wrap in a tiny self-contained document; sandbox allows scripts only.
        srcdoc = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<style>body{font-family:system-ui,sans-serif;margin:12px;color:#1a1a1a;}"
            "input,button,select{font:inherit;margin:4px 0;}</style></head>"
            f"<body>{inner}</body></html>"
        )
        srcdoc_attr = html.escape(srcdoc, quote=True)
        blocks.append(f"""
          <div class="demo">
            <h3>{title}</h3>
            {f'<p class="demo-caption">{caption}</p>' if caption else ''}
            <iframe class="demo-frame" sandbox="allow-scripts"
                    srcdoc="{srcdoc_attr}" loading="lazy"></iframe>
          </div>
        """)
    return render_section("Play with it", "".join(blocks),
                          label="Interactive", extra_class="demos")


def render_novelty(nov: dict) -> str:
    if not nov:
        return ""
    t = nov.get("type", "").lower()
    type_label = {
        "conceptual": "Conceptually novel",
        "methodological": "Methodologically novel",
        "empirical": "Empirically novel",
        "engineering": "Engineering novel",
    }.get(t, "Novelty")
    body = f"""
      <div class="novelty-tag novelty-{esc(t)}">{type_label}</div>
      <div class="before-after">
        <div><span class="ba-label">Before</span><p>{esc(nov.get("before",""))}</p></div>
        <div><span class="ba-label">After</span><p>{esc(nov.get("after",""))}</p></div>
      </div>
    """
    return render_section("What's actually new", body)


def render_results(results) -> str:
    if not results:
        return ""
    rows = []
    for r in results:
        rows.append(f"""
          <div class="result-row">
            <p class="claim">{esc(r.get("claim",""))}</p>
            {f'<p class="evidence"><span class="r-label">Evidence</span> {esc(r.get("evidence",""))}</p>' if r.get("evidence") else ''}
            {f'<p class="caveat"><span class="r-label">Caveat</span> {esc(r.get("caveat",""))}</p>' if r.get("caveat") else ''}
          </div>
        """)
    return render_section("Results — and what they support", "".join(rows))


def render_limitations(lim: dict) -> str:
    if not lim:
        return ""
    parts = []
    if lim.get("stated"):
        items = "".join(f"<li>{esc(x)}</li>" for x in lim["stated"])
        parts.append(f'<div class="lim-block"><h3>Stated by authors</h3><ul>{items}</ul></div>')
    if lim.get("unstated"):
        items = "".join(f"<li>{esc(x)}</li>" for x in lim["unstated"])
        parts.append(f'<div class="lim-block lim-unstated"><h3>Unstated</h3><ul>{items}</ul></div>')
    return render_section("Limitations", "".join(parts))


def render_implementation(impl: dict) -> str:
    if not impl:
        return ""
    feas = impl.get("feasibility", "")
    feas_html = f'<div class="feasibility feas-{esc(feas).replace(" ", "-")}">Effort: {esc(feas)}</div>' if feas else ""
    reqs = ""
    if impl.get("requirements"):
        items = "".join(f"<li>{esc(x)}</li>" for x in impl["requirements"])
        reqs = f"<h3>What you'd need</h3><ul>{items}</ul>"
    cv = ""
    if impl.get("cheapest_validation"):
        cv = f"<h3>Cheapest validation</h3><p>{esc(impl['cheapest_validation'])}</p>"
    return render_section("Could you actually use this?", feas_html + reqs + cv)


def render_implications(imp: dict) -> str:
    if not imp:
        return ""
    blocks = []
    titles = {
        "research": "For research",
        "practice": "For practice",
        "personal": "For you",
    }
    for key in ["research", "practice", "personal"]:
        if imp.get(key):
            items = "".join(f"<li>{esc(x)}</li>" for x in imp[key])
            blocks.append(f'<div class="imp-block"><h3>{titles[key]}</h3><ul>{items}</ul></div>')
    return render_section("So what?", f'<div class="imp-grid">{"".join(blocks)}</div>')


def render_people(people) -> str:
    if not people:
        return ""
    cards = []
    for p in people:
        link_html = ""
        if p.get("linkedin"):
            link_html = f'<a class="li-link" href="{esc(p["linkedin"])}" target="_blank">LinkedIn ↗</a>'
        elif p.get("search_hint"):
            link_html = f'<span class="li-hint">{esc(p["search_hint"])}</span>'
        path = p.get("connection_path")
        path_html = f'<p class="conn-path">{esc(path)}</p>' if path else ""
        cards.append(f"""
          <div class="person-card">
            <h3>{esc(p.get("name",""))}</h3>
            <p class="role">{esc(p.get("role",""))}</p>
            {path_html}
            <p class="why">{esc(p.get("why",""))}</p>
            {link_html}
          </div>
        """)
    return render_section("People worth reaching out to",
                          f'<div class="people-grid">{"".join(cards)}</div>',
                          label="Starts from your network")


def render_graph(graph: dict) -> str:
    if not graph or not graph.get("nodes"):
        return ""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    # Inject the data as JSON — vis-network will pick it up.
    data_script = (
        f'<script id="graph-data" type="application/json">'
        f'{json.dumps({"nodes": nodes, "edges": edges})}'
        f'</script>'
    )
    return render_section(
        "Knowledge graph",
        f"""
        <p class="graph-help">Drag to pan, scroll to zoom, click a node to highlight its connections.</p>
        <div id="kg" class="kg-container"></div>
        {data_script}
        """
    )


def render_notes(slug: str) -> str:
    return f"""
    <section class="card notes-card" data-slug="{esc(slug)}">
      <div class="label">Your notes</div>
      <h2>Notes</h2>
      <p class="notes-help">
        These persist. Served via <code>serve.py</code> they save to
        <code>papers/{esc(slug)}/notes.md</code>;
        opened as a file they save to your browser.
        <span id="notes-status" class="notes-status"></span>
      </p>
      <div id="notes" class="notes-editor"
           data-placeholder="Type your notes here… (Markdown)"></div>
      <div class="notes-actions">
        <button id="notes-save" type="button">Save</button>
        <button id="notes-download" type="button">Download notes.md</button>
      </div>
    </section>
    """


# ---------- main template -------------------------------------------------

CSS = """
:root {
  --bg: #fafaf7;
  --card: #ffffff;
  --ink: #1a1a1a;
  --muted: #6b6b6b;
  --line: #e8e6e0;
  --accent: #2d4a8a;
  --accent-soft: #eef2fa;
  --warn: #b85c00;
  --warn-soft: #fdf3e7;
  --good: #2e6f4a;
  --good-soft: #ecf5ef;
  --eli5: #6a3fb5;
  --eli5-soft: #f1ecfa;
  --radius: 10px;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.55;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}
.container { max-width: 880px; margin: 0 auto; padding: 48px 24px 96px; }

.paper-header { margin-bottom: 32px; }
.paper-header h1 {
  font-size: 32px; line-height: 1.2; margin: 0 0 12px;
  letter-spacing: -0.01em; font-weight: 600;
}
.byline { color: var(--ink); margin: 4px 0; font-size: 15px; }
.byline .aff { color: var(--muted); font-size: 13px; }
.meta { color: var(--muted); font-size: 14px; margin: 4px 0; }
.links { margin-top: 12px; font-size: 14px; }
.links a { color: var(--accent); text-decoration: none; margin-right: 4px; }
.links a:hover { text-decoration: underline; }

.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 24px 28px;
  margin-bottom: 20px;
}
.card h2 {
  font-size: 18px; font-weight: 600; margin: 0 0 12px;
  letter-spacing: -0.005em;
}
.card h3 {
  font-size: 14px; font-weight: 600; margin: 16px 0 6px;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
}
.card p { margin: 8px 0; }
.card ul { margin: 8px 0; padding-left: 20px; }
.card li { margin: 4px 0; }
.card code {
  background: #f3f1ec; padding: 1px 5px; border-radius: 4px;
  font-size: 0.9em; font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
.label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); margin-bottom: 8px; font-weight: 600;
}

.headline {
  background: var(--accent-soft);
  border-color: #d4dded;
}
.headline p {
  font-size: 19px; line-height: 1.45; margin: 0;
  font-weight: 500; color: var(--ink);
}

.eli5 { background: var(--eli5-soft); border-color: #ddd2f0; }
.eli5 .label { color: var(--eli5); }
.eli5 h2 { color: var(--eli5); }
.analogy { font-size: 17px; line-height: 1.5; }
.analogy-mark {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
  font-weight: 700; color: var(--eli5); display: block; margin-bottom: 2px;
}

.glossary-item {
  border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 12px; margin: 6px 0; background: var(--bg);
}
.glossary-item summary {
  cursor: pointer; font-weight: 600; font-size: 14px;
}
.glossary-item p { margin: 8px 0 2px; font-size: 14px; color: #333; }

.paper-figure {
  margin: 12px 0; padding: 12px; border: 1px solid var(--line);
  border-radius: 8px; background: var(--bg);
}
.paper-figure img { max-width: 100%; height: auto; border-radius: 6px; display: block; }
.paper-figure figcaption { font-size: 14px; color: #333; margin-top: 8px; }

.demo { margin: 14px 0; }
.demo h3 { color: var(--ink); text-transform: none; letter-spacing: 0; font-size: 15px; }
.demo-caption { font-size: 14px; color: var(--muted); margin: 4px 0 8px; }
.demo-frame {
  width: 100%; min-height: 220px; border: 1px solid var(--line);
  border-radius: 8px; background: #fff;
}

.novelty-tag {
  display: inline-block; padding: 4px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 500; margin-bottom: 12px;
  background: var(--accent-soft); color: var(--accent);
}
.before-after { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 8px; }
.before-after > div {
  padding: 14px 16px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg);
}
.ba-label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--muted); font-weight: 600;
}
.before-after p { margin: 6px 0 0; font-size: 14px; }

.result-row { padding: 12px 0; border-bottom: 1px solid var(--line); }
.result-row:last-child { border-bottom: none; }
.result-row .claim { font-weight: 500; margin: 0 0 6px; }
.result-row .evidence, .result-row .caveat { font-size: 14px; margin: 4px 0; color: #333; }
.result-row .caveat { color: var(--warn); }
.r-label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
  font-weight: 600; margin-right: 4px;
}
.result-row .evidence .r-label { color: var(--good); }
.result-row .caveat .r-label   { color: var(--warn); }

.lim-block { margin-bottom: 12px; }
.lim-unstated {
  background: var(--warn-soft); border: 1px solid #f0d9bc;
  padding: 12px 16px; border-radius: 8px;
}

.feasibility {
  display: inline-block; padding: 4px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 500; margin-bottom: 8px;
  background: var(--good-soft); color: var(--good);
}
.feas-quarter, .feas-research-project { background: var(--warn-soft); color: var(--warn); }

.imp-grid { display: grid; gap: 14px; }
.imp-block {
  padding: 14px 16px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg);
}
.imp-block h3 { margin-top: 0; }

.people-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px;
}
.person-card {
  padding: 16px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg);
}
.person-card h3 {
  margin: 0 0 4px; font-size: 15px; text-transform: none;
  letter-spacing: 0; color: var(--ink);
}
.person-card .role { font-size: 13px; color: var(--muted); margin: 0 0 6px; }
.conn-path {
  font-size: 12px; font-weight: 600; color: var(--good);
  background: var(--good-soft); border-radius: 6px;
  padding: 4px 8px; margin: 0 0 8px; display: inline-block;
}
.person-card .why { font-size: 14px; margin: 0 0 10px; }
.li-link {
  color: var(--accent); text-decoration: none; font-size: 13px; font-weight: 500;
}
.li-link:hover { text-decoration: underline; }
.li-hint { color: var(--muted); font-size: 13px; font-style: italic; }

.graph-help { color: var(--muted); font-size: 13px; margin-top: 0; }
.kg-container {
  height: 480px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg); margin-top: 12px;
}

.notes-editor {
  min-height: 140px; padding: 12px 14px;
  border: 1px solid var(--line); border-radius: 8px;
  background: var(--bg); font-size: 15px; line-height: 1.6;
  outline: none; white-space: pre-wrap;
}
.notes-editor:focus { border-color: var(--accent); }
.notes-editor:empty::before {
  content: attr(data-placeholder); color: var(--muted);
}
.notes-help { font-size: 13px; color: var(--muted); margin-top: 0; }
.notes-status { font-weight: 600; margin-left: 6px; }
.notes-actions { margin-top: 10px; display: flex; gap: 8px; }
.notes-actions button {
  font: inherit; font-size: 13px; padding: 6px 14px; cursor: pointer;
  border: 1px solid var(--line); border-radius: 8px; background: #fff;
}
.notes-actions button:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 640px) {
  .container { padding: 32px 16px 64px; }
  .paper-header h1 { font-size: 26px; }
  .before-after { grid-template-columns: 1fr; }
}
"""

GRAPH_JS = """
(function() {
  var el = document.getElementById('graph-data');
  var container = document.getElementById('kg');
  if (!el || !container || typeof vis === 'undefined') return;
  var data = JSON.parse(el.textContent);

  var typeColor = {
    technique:  { bg: '#eef2fa', bd: '#2d4a8a' },
    dataset:    { bg: '#ecf5ef', bd: '#2e6f4a' },
    prior_work: { bg: '#f3eee6', bd: '#7a5a2a' },
    claim:      { bg: '#fdf3e7', bd: '#b85c00' },
    domain:     { bg: '#f0ecf5', bd: '#5e3d8a' },
    concept:    { bg: '#f0f0f0', bd: '#555555' }
  };

  var nodes = data.nodes.map(function(n) {
    var c = typeColor[n.type] || typeColor.concept;
    return {
      id: n.id,
      label: n.label,
      color: { background: c.bg, border: c.bd, highlight: { background: c.bd, border: c.bd } },
      font: { color: '#1a1a1a', size: 14, face: 'system-ui' },
      shape: 'box',
      margin: 10,
      borderWidth: 1.5
    };
  });

  var edges = data.edges.map(function(e) {
    return {
      from: e.from, to: e.to,
      label: e.label,
      arrows: 'to',
      color: { color: '#bcb9b0', highlight: '#2d4a8a' },
      font: { size: 11, color: '#6b6b6b', strokeWidth: 0, align: 'middle' },
      smooth: { type: 'continuous' }
    };
  });

  new vis.Network(container, { nodes: nodes, edges: edges }, {
    physics: { stabilization: { iterations: 200 }, barnesHut: { springLength: 150 } },
    interaction: { hover: true, tooltipDelay: 200 }
  });
})();
"""

# Notes persistence. Saves to papers/<slug>/notes.md through serve.py when
# available (POST /api/notes), otherwise localStorage. Always offers a download.
NOTES_JS = """
(function() {
  var notes = document.getElementById('notes');
  var card = document.querySelector('.notes-card');
  if (!notes || !card) return;
  var slug = card.getAttribute('data-slug') || (document.title || 'paper');
  var statusEl = document.getElementById('notes-status');
  var saveBtn = document.getElementById('notes-save');
  var dlBtn = document.getElementById('notes-download');
  var lsKey = 'paper-notes:' + slug;
  var served = location.protocol === 'http:' || location.protocol === 'https:';

  function setStatus(msg) { if (statusEl) statusEl.textContent = msg; }

  function load() {
    if (served) {
      fetch('/api/notes?slug=' + encodeURIComponent(slug))
        .then(function(r) { return r.ok ? r.text() : ''; })
        .then(function(text) { if (text) notes.textContent = text; })
        .catch(function() {
          var s = localStorage.getItem(lsKey); if (s) notes.textContent = s;
        });
    } else {
      var s = localStorage.getItem(lsKey); if (s) notes.textContent = s;
    }
  }

  function save() {
    var text = notes.textContent || '';
    localStorage.setItem(lsKey, text);
    if (served) {
      setStatus('saving…');
      fetch('/api/notes?slug=' + encodeURIComponent(slug), {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: text
      }).then(function(r) {
        setStatus(r.ok ? 'saved to notes.md ✓' : 'save failed (kept in browser)');
      }).catch(function() { setStatus('offline — kept in browser'); });
    } else {
      setStatus('saved in browser ✓');
    }
  }

  function download() {
    var blob = new Blob([notes.textContent || ''], { type: 'text/markdown' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'notes.md';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  notes.setAttribute('contenteditable', 'true');
  var t;
  notes.addEventListener('input', function() {
    setStatus('unsaved…');
    clearTimeout(t);
    t = setTimeout(save, 800);
  });
  if (saveBtn) saveBtn.addEventListener('click', save);
  if (dlBtn) dlBtn.addEventListener('click', download);
  load();
})();
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
<script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/dist/vis-network.min.js"></script>
</head>
<body>
<div class="container">
{header}
{headline}
{eli5}
{plain_summary}
{glossary}
{figures}
{demos}
{novelty}
{methods}
{results}
{limitations}
{implementation}
{implications}
{graph}
{people}
{notes}
</div>
<script>{graph_js}</script>
<script>{notes_js}</script>
</body>
</html>
"""


def build_html(analysis: dict, slug: str) -> str:
    paper = analysis.get("paper", {})
    title = esc(paper.get("title", "Paper Report"))

    plain = md_to_html(analysis.get("plain_summary", ""))
    methods = md_to_html(analysis.get("methods", ""))

    return TEMPLATE.format(
        title=title,
        css=CSS,
        header=render_header(paper),
        headline=render_headline(analysis.get("headline", "")),
        eli5=render_eli5(analysis.get("eli5", {})),
        plain_summary=render_section("Plain-language summary", plain),
        glossary=render_glossary(analysis.get("glossary")),
        figures=render_figures(analysis.get("figures")),
        demos=render_demos(analysis.get("demos")),
        novelty=render_novelty(analysis.get("novelty", {})),
        methods=render_section("Methods — what they actually did", methods),
        results=render_results(analysis.get("results")),
        limitations=render_limitations(analysis.get("limitations", {})),
        implementation=render_implementation(analysis.get("implementation", {})),
        implications=render_implications(analysis.get("implications", {})),
        graph=render_graph(analysis.get("knowledge_graph", {})),
        people=render_people(analysis.get("people")),
        notes=render_notes(slug),
        graph_js=GRAPH_JS,
        notes_js=NOTES_JS,
    )


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or "paper"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to analysis JSON")
    ap.add_argument("--output", required=True, help="Path for generated HTML")
    ap.add_argument("--slug", default=None,
                    help="Slug for notes persistence (defaults to analysis.slug or title)")
    args = ap.parse_args()

    with open(args.input) as f:
        analysis = json.load(f)

    if not analysis.get("paper", {}).get("title"):
        print("ERROR: analysis.paper.title is required", file=sys.stderr)
        sys.exit(1)
    if not analysis.get("headline"):
        print("ERROR: analysis.headline is required", file=sys.stderr)
        sys.exit(1)

    slug = args.slug or analysis.get("slug") or slugify(analysis["paper"]["title"])

    html_text = build_html(analysis, slug)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    print(f"Wrote {out} ({len(html_text):,} bytes) — notes slug: {slug}")


if __name__ == "__main__":
    main()
