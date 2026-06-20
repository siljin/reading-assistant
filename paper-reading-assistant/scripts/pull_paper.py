#!/usr/bin/env python3
"""
pull_paper.py - Select one high-value research paper for a topic profile.

The puller is intentionally lean:
  - OpenAlex is the primary discovery source.
  - One run selects at most one paper.
  - Normal mode creates one paper folder with source.md and starter analysis.json.
  - Full report analysis remains agent-assisted.
"""

import argparse
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
PAPERS_DIR = REPO_ROOT / "papers"
LEDGER_NAME = ".pulled.json"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
DAIR_README_URL = "https://raw.githubusercontent.com/dair-ai/AI-Papers-of-the-Week/main/README.md"
DAIR_RAW_BASE = "https://raw.githubusercontent.com/dair-ai/AI-Papers-of-the-Week/main"
CURATED_SOURCE_LABELS = {
    "dair-ai-weekly": "DAIR AI Papers of the Week",
}
RELEVANCE_POINTS = 35.0
CITATION_POINTS = 17.0
RECENCY_POINTS = 18.0
CURATED_POPULARITY_POINTS = 10.0
SOURCE_CREDIBILITY_POINTS = 8.0
ACCESSIBILITY_POINTS = 7.0
NOVELTY_DIVERSITY_POINTS = 5.0


class ScoredPaper:
    def __init__(self, candidate: dict, score: float, breakdown: dict):
        self.candidate = candidate
        self.score = score
        self.breakdown = breakdown


class PullResult:
    def __init__(self, paper: dict | None, message: str, folder: Path | None = None):
        self.paper = paper
        self.message = message
        self.folder = folder


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:60] or "paper"


def normalize_profile(profile: dict) -> dict:
    return {
        "name": profile.get("name") or "default",
        "keywords": list(profile.get("keywords") or []),
        "openalex_topics": list(profile.get("openalex_topics") or []),
        "arxiv_categories": list(profile.get("arxiv_categories") or []),
        "must_include": list(profile.get("must_include") or []),
        "must_exclude": list(profile.get("must_exclude") or []),
        "recency_days": int(profile.get("recency_days") or 730),
        "min_year": profile.get("min_year"),
        "max_results_to_score": int(profile.get("max_results_to_score") or 50),
        "curated_sources": list(profile.get("curated_sources") or []),
        "curated_max_weeks": int(profile.get("curated_max_weeks") or 8),
    }


def load_profile(path: Path) -> dict:
    return normalize_profile(json.loads(path.read_text(encoding="utf-8")))


def abstract_from_inverted_index(index: dict | None) -> str:
    if not index:
        return ""
    positions = []
    for word, indexes in index.items():
        for i in indexes:
            positions.append((i, word))
    return " ".join(word for _, word in sorted(positions))


def normalize_openalex_work(work: dict) -> dict:
    authorships = work.get("authorships") or []
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in authorships
        if (a.get("author") or {}).get("display_name")
    ]
    ids = work.get("ids") or {}
    primary = work.get("primary_location") or {}
    best_oa = work.get("best_oa_location") or {}
    open_access = work.get("open_access") or {}
    primary_source = primary.get("source") or {}
    topics = work.get("topics") or work.get("concepts") or []

    arxiv_id = None
    for value in ids.values():
        if isinstance(value, str) and "arxiv.org/abs/" in value:
            arxiv_id = value.rsplit("/", 1)[-1]

    return {
        "id": work.get("id") or ids.get("openalex"),
        "doi": work.get("doi") or ids.get("doi"),
        "title": work.get("title") or work.get("display_name"),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "cited_by_count": work.get("cited_by_count") or 0,
        "abstract": work.get("abstract") or abstract_from_inverted_index(work.get("abstract_inverted_index")),
        "authors": authors,
        "primary_location": {
            "landing_page_url": primary.get("landing_page_url") or best_oa.get("landing_page_url"),
            "pdf_url": primary.get("pdf_url") or best_oa.get("pdf_url"),
            "source": {"display_name": primary_source.get("display_name")},
        },
        "open_access": {
            "is_oa": bool(open_access.get("is_oa")),
            "oa_url": open_access.get("oa_url"),
        },
        "locations": work.get("locations") or [],
        "topics": [{"display_name": t.get("display_name")} for t in topics if t.get("display_name")],
        "arxiv_id": arxiv_id,
    }


def fetch_openalex_candidates(profile: dict) -> list[dict]:
    params = {
        "per-page": str(profile["max_results_to_score"]),
        "sort": "cited_by_count:desc",
        "select": ",".join([
            "id",
            "doi",
            "ids",
            "title",
            "display_name",
            "publication_year",
            "publication_date",
            "cited_by_count",
            "abstract_inverted_index",
            "authorships",
            "primary_location",
            "best_oa_location",
            "open_access",
            "locations",
            "topics",
            "concepts",
        ]),
    }
    if profile["keywords"]:
        params["search"] = " ".join(profile["keywords"])
    filters = []
    if profile.get("min_year"):
        filters.append(f"from_publication_date:{int(profile['min_year'])}-01-01")
    if filters:
        params["filter"] = ",".join(filters)

    url = f"{OPENALEX_WORKS_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "reading-assistant/0.1 (mailto:example@example.com)"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return [normalize_openalex_work(work) for work in data.get("results", [])]


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": "reading-assistant/0.1"})
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def extract_arxiv_id(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#)\s/]+)", value, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).removesuffix(".pdf")


def normalize_match_title(value: str | None) -> str:
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", value or "")
    text = re.sub(r"[*_`|]", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def clean_dair_title(value: str) -> str:
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", value)
    text = re.sub(r"[*_`|]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_dair_year_markdown(markdown: str, max_weeks: int = 8) -> list[dict]:
    text = re.sub(r"\s+##\s+Top AI Papers", "\n## Top AI Papers", markdown.replace("\r\n", "\n"))
    heading_pattern = re.compile(r"##\s+(Top AI Papers of the Week\s+\([^)]+\)\s*-\s*\d{4})")
    headings = list(heading_pattern.finditer(text))
    entries = []

    for issue_index, heading in enumerate(headings[:max(0, max_weeks)]):
        section_start = heading.end()
        section_end = headings[issue_index + 1].start() if issue_index + 1 < len(headings) else len(text)
        section = text[section_start:section_end]
        rank_matches = list(re.finditer(
            r"(?:^|\|\s*)\s*(\d{1,2})\)\s+(?:\*\*)?(.+?)(?:\*\*)?\s+-",
            section,
            flags=re.MULTILINE,
        ))
        for index, rank_match in enumerate(rank_matches):
            segment_end = rank_matches[index + 1].start() if index + 1 < len(rank_matches) else len(section)
            segment = section[rank_match.start():segment_end]
            paper_match = re.search(r"\[Paper\]\((https?://[^)]+)\)", segment)
            if not paper_match:
                continue
            paper_url = paper_match.group(1).strip()
            entries.append({
                "source": "dair-ai-weekly",
                "issue_title": heading.group(1).strip(),
                "rank": int(rank_match.group(1)),
                "title": clean_dair_title(rank_match.group(2)),
                "paper_url": paper_url,
                "arxiv_id": extract_arxiv_id(paper_url),
            })
    return entries


def dair_year_urls_from_index(markdown: str) -> list[str]:
    years = []
    for match in re.finditer(r"years/(\d{4})\.md", markdown):
        year = match.group(1)
        if year not in years:
            years.append(year)
    if not years:
        years = [str(date.today().year)]
    return [f"{DAIR_RAW_BASE}/years/{year}.md" for year in years]


def fetch_dair_curated_entries(profile: dict) -> list[dict]:
    if "dair-ai-weekly" not in profile.get("curated_sources", []):
        return []
    max_weeks = max(1, int(profile.get("curated_max_weeks") or 8))
    index_markdown = fetch_text(DAIR_README_URL)
    entries = []
    weeks_remaining = max_weeks
    for year_url in dair_year_urls_from_index(index_markdown):
        if weeks_remaining <= 0:
            break
        year_entries = parse_dair_year_markdown(fetch_text(year_url), max_weeks=weeks_remaining)
        entries.extend(year_entries)
        issue_titles = {entry["issue_title"] for entry in year_entries}
        weeks_remaining -= len(issue_titles)
    return entries


def fetch_curated_entries(profile: dict) -> list[dict]:
    entries = []
    if "dair-ai-weekly" in profile.get("curated_sources", []):
        entries.extend(fetch_dair_curated_entries(profile))
    return entries


def enrich_candidates_with_curated_matches(candidates: list[dict], curated_entries: list[dict]) -> list[dict]:
    by_arxiv = {
        entry["arxiv_id"]: entry
        for entry in curated_entries
        if entry.get("arxiv_id")
    }
    by_title = {
        normalize_match_title(entry.get("title")): entry
        for entry in curated_entries
        if not entry.get("arxiv_id") and normalize_match_title(entry.get("title"))
    }
    enriched = []
    for candidate in candidates:
        item = dict(candidate)
        match = None
        arxiv_id = candidate.get("arxiv_id") or extract_arxiv_id(source_url(candidate)) or extract_arxiv_id(pdf_url(candidate))
        if arxiv_id and arxiv_id in by_arxiv:
            match = by_arxiv[arxiv_id]
        elif not arxiv_id:
            match = by_title.get(normalize_match_title(candidate.get("title")))
        else:
            no_arxiv_title_match = by_title.get(normalize_match_title(candidate.get("title")))
            if no_arxiv_title_match:
                match = no_arxiv_title_match
        if match:
            item["curated_matches"] = [dict(match)]
        enriched.append(item)
    return enriched


def canonical_id(candidate: dict) -> str:
    for key in ("id", "doi", "arxiv_id"):
        value = candidate.get(key)
        if value:
            return str(value)
    return slugify(candidate.get("title") or "")


def candidate_ids(candidate: dict) -> set[str]:
    ids = {canonical_id(candidate)}
    for key in ("id", "doi", "arxiv_id"):
        value = candidate.get(key)
        if value:
            ids.add(str(value))
    return ids


def source_url(candidate: dict) -> str:
    primary = candidate.get("primary_location") or {}
    open_access = candidate.get("open_access") or {}
    for value in (
        primary.get("landing_page_url"),
        open_access.get("oa_url"),
        primary.get("pdf_url"),
        candidate.get("doi"),
        candidate.get("id"),
    ):
        if value:
            return str(value)
    arxiv_id = candidate.get("arxiv_id")
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    return ""


def pdf_url(candidate: dict) -> str:
    primary = candidate.get("primary_location") or {}
    url = primary.get("pdf_url")
    if url:
        return str(url)
    src = source_url(candidate)
    if "arxiv.org/abs/" in src:
        return src.replace("/abs/", "/pdf/")
    return ""


def combined_text(candidate: dict) -> str:
    topic_text = " ".join(t.get("display_name", "") for t in candidate.get("topics") or [])
    return " ".join([
        str(candidate.get("title") or ""),
        str(candidate.get("abstract") or ""),
        topic_text,
    ]).lower()


def parse_date(value: str | None, year=None) -> date | None:
    if value:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    if year:
        try:
            return date(int(year), 1, 1)
        except (TypeError, ValueError):
            return None
    return None


def has_required_fields(candidate: dict) -> bool:
    return bool(
        candidate.get("title")
        and candidate.get("authors")
        and candidate.get("publication_year")
        and candidate.get("abstract")
        and source_url(candidate)
    )


def passes_hard_filters(candidate: dict, profile: dict, pulled_ids: set[str]) -> bool:
    if candidate_ids(candidate) & pulled_ids:
        return False
    if not has_required_fields(candidate):
        return False
    text = combined_text(candidate)
    if any(term.lower() in text for term in profile["must_exclude"]):
        return False
    if profile["must_include"] and not all(term.lower() in text for term in profile["must_include"]):
        return False
    if profile.get("min_year") and int(candidate.get("publication_year") or 0) < int(profile["min_year"]):
        return False
    return True


def keyword_units(keyword: str) -> list[str]:
    words = [w for w in re.split(r"[^a-z0-9]+", keyword.lower()) if w]
    return [keyword.lower()] + words


def score_relevance(candidate: dict, profile: dict) -> float:
    text = combined_text(candidate)
    title = str(candidate.get("title") or "").lower()
    score = 0.0
    for keyword in profile["keywords"]:
        keyword_l = keyword.lower()
        units = keyword_units(keyword)
        if keyword_l in title:
            score += 10
        elif keyword_l in text:
            score += 7
        else:
            matched = sum(1 for unit in units[1:] if unit in text)
            if units[1:]:
                score += min(6, matched / len(units[1:]) * 6)

    topic_names = [str(t.get("display_name") or "").lower() for t in candidate.get("topics") or []]
    for topic in profile["openalex_topics"]:
        if any(topic.lower() in name for name in topic_names):
            score += 8

    arxiv_text = " ".join([str(candidate.get("arxiv_id") or ""), source_url(candidate)]).lower()
    for category in profile["arxiv_categories"]:
        if category.lower() in arxiv_text:
            score += 6

    return min(RELEVANCE_POINTS, score)


def score_citations(candidate: dict, today: date) -> float:
    pub_date = parse_date(candidate.get("publication_date"), candidate.get("publication_year")) or today
    age_years = max((today - pub_date).days / 365.25, 0.25)
    annualized = float(candidate.get("cited_by_count") or 0) / age_years
    return min(CITATION_POINTS, math.log1p(annualized) / math.log1p(250) * CITATION_POINTS)


def score_recency(candidate: dict, profile: dict, today: date) -> float:
    pub_date = parse_date(candidate.get("publication_date"), candidate.get("publication_year"))
    if not pub_date:
        return 0.0
    age_days = max((today - pub_date).days, 0)
    window = max(int(profile["recency_days"]), 1)
    if age_days > window:
        return max(0.0, RECENCY_POINTS * (window / age_days) * 0.25)
    return RECENCY_POINTS * (1 - (age_days / window) * 0.5)


def score_source(candidate: dict) -> float:
    url = source_url(candidate).lower()
    source_name = (((candidate.get("primary_location") or {}).get("source") or {}).get("display_name") or "").lower()
    if "arxiv.org" in url or "arxiv" in source_name:
        return SOURCE_CREDIBILITY_POINTS
    if source_name:
        return 6.0
    return 3.0


def score_accessibility(candidate: dict) -> float:
    score = 0.0
    if source_url(candidate):
        score += 2
    if (candidate.get("open_access") or {}).get("is_oa"):
        score += 2
    if pdf_url(candidate):
        score += 2
    if candidate.get("abstract"):
        score += 1
    return min(ACCESSIBILITY_POINTS, score)


def score_curated_popularity(candidate: dict) -> float:
    matches = candidate.get("curated_matches") or []
    if not matches:
        return 0.0
    scores = []
    for match in matches:
        rank = match.get("rank")
        if rank is None:
            scores.append(6.0)
        elif int(rank) <= 5:
            scores.append(CURATED_POPULARITY_POINTS)
        elif int(rank) <= 10:
            scores.append(8.0)
        else:
            scores.append(6.0)
    return max(scores)


def score_novelty(candidate: dict, papers_dir: Path | None = None) -> float:
    if not papers_dir or not papers_dir.exists():
        return NOVELTY_DIVERSITY_POINTS
    title_words = set(re.findall(r"[a-z0-9]+", str(candidate.get("title") or "").lower()))
    if not title_words:
        return 0.0
    for analysis in papers_dir.glob("*/analysis.json"):
        try:
            existing = json.loads(analysis.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        existing_title = ((existing.get("paper") or {}).get("title") or "").lower()
        existing_words = set(re.findall(r"[a-z0-9]+", existing_title))
        if existing_words and len(title_words & existing_words) / len(title_words | existing_words) > 0.55:
            return 0.0
    return NOVELTY_DIVERSITY_POINTS


def score_candidate(candidate: dict, profile: dict, today: date, papers_dir: Path | None = None) -> ScoredPaper:
    breakdown = {
        "relevance": round(score_relevance(candidate, profile), 2),
        "citation_signal": round(score_citations(candidate, today), 2),
        "recency_trend": round(score_recency(candidate, profile, today), 2),
        "curated_popularity": round(score_curated_popularity(candidate), 2),
        "source_credibility": round(score_source(candidate), 2),
        "accessibility": round(score_accessibility(candidate), 2),
        "novelty_diversity": round(score_novelty(candidate, papers_dir), 2),
    }
    total = round(sum(breakdown.values()), 2)
    return ScoredPaper(candidate, total, breakdown)


def select_best_paper(
    candidates: list[dict],
    profile: dict,
    pulled_ids: set[str],
    today: date | None = None,
    papers_dir: Path | None = None,
) -> ScoredPaper:
    today = today or date.today()
    scored = [
        score_candidate(candidate, profile, today, papers_dir)
        for candidate in candidates
        if passes_hard_filters(candidate, profile, pulled_ids)
    ]
    if not scored:
        raise ValueError("No eligible papers found for this profile.")

    def sort_key(item: ScoredPaper):
        pub_date = parse_date(item.candidate.get("publication_date"), item.candidate.get("publication_year")) or date.min
        return (
            item.score,
            item.breakdown["relevance"],
            pub_date.toordinal(),
            item.breakdown["citation_signal"],
            item.breakdown["accessibility"],
        )

    return sorted(scored, key=sort_key, reverse=True)[0]


def load_ledger(papers_dir: Path) -> dict:
    path = papers_dir / LEDGER_NAME
    if not path.exists():
        return {"pulled": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"pulled": []}
    if "pulled" not in data or not isinstance(data["pulled"], list):
        return {"pulled": []}
    return data


def pulled_id_set(ledger: dict) -> set[str]:
    ids = set()
    for entry in ledger.get("pulled") or []:
        for key in ("canonical_id", "openalex_id", "doi", "arxiv_id"):
            if entry.get(key):
                ids.add(str(entry[key]))
    return ids


def write_ledger(papers_dir: Path, ledger: dict) -> None:
    papers_dir.mkdir(parents=True, exist_ok=True)
    (papers_dir / LEDGER_NAME).write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def starter_analysis(candidate: dict, slug: str) -> dict:
    return {
        "paper": {
            "title": candidate.get("title") or "",
            "authors": candidate.get("authors") or [],
            "affiliations": [],
            "venue": (((candidate.get("primary_location") or {}).get("source") or {}).get("display_name") or ""),
            "year": candidate.get("publication_year"),
            "url": source_url(candidate),
            "code_url": "",
            "data_url": None,
        },
        "slug": slug,
        "headline": "",
        "eli5": {"analogy": "", "text": ""},
        "plain_summary": candidate.get("abstract") or "",
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
                    "papers": [{"title": "", "url": "", "why": "", "read_for": ""}],
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


def source_markdown(candidate: dict, profile: dict, scored: ScoredPaper, selected_date: date) -> str:
    title = candidate.get("title") or "Untitled paper"
    authors = ", ".join(candidate.get("authors") or [])
    lines = [
        f"# Source: {title}",
        "",
        "Automatically selected by `pull_paper.py`.",
        "",
        "## Paper",
        f"- Title: {title}",
        f"- Authors: {authors}",
        f"- Year: {candidate.get('publication_year') or ''}",
        f"- Publication date: {candidate.get('publication_date') or ''}",
        f"- Selected date: {selected_date.isoformat()}",
        f"- Profile: {profile['name']}",
        f"- Source URL: {source_url(candidate)}",
    ]
    if pdf_url(candidate):
        lines.append(f"- PDF URL: {pdf_url(candidate)}")
    if candidate.get("id"):
        lines.append(f"- OpenAlex ID: {candidate.get('id')}")
    if candidate.get("doi"):
        lines.append(f"- DOI: {candidate.get('doi')}")
    if candidate.get("arxiv_id"):
        lines.append(f"- arXiv ID: {candidate.get('arxiv_id')}")
    curated_matches = candidate.get("curated_matches") or []
    if curated_matches:
        match = curated_matches[0]
        label = CURATED_SOURCE_LABELS.get(match.get("source"), match.get("source") or "Curated source")
        lines += [
            f"- Curated source: {label}",
            f"- DAIR issue: {match.get('issue_title') or ''}",
            f"- DAIR rank: {match.get('rank') if match.get('rank') is not None else 'unranked'}",
            f"- DAIR paper URL: {match.get('paper_url') or ''}",
        ]

    lines += [
        "",
        "## Why this paper was selected",
        f"- Total score: {scored.score:.2f} / 100",
        "- Reason: highest eligible score for this profile after hard filters and already-pulled checks.",
        "",
        "## Score breakdown",
    ]
    for key, value in scored.breakdown.items():
        lines.append(f"- {key.replace('_', ' ').title()}: {value:.2f}")

    lines += [
        "",
        "## Abstract",
        "",
        candidate.get("abstract") or "",
        "",
        "## Next step",
        "",
        "Ask the agent to read this source, complete `analysis.json`, then run:",
        "",
        "```bash",
        "python paper-reading-assistant/scripts/render_report.py \\",
        "  --input papers/<slug>/analysis.json \\",
        "  --output papers/<slug>/report.html \\",
        "  --slug <slug>",
        "```",
    ]
    return "\n".join(lines) + "\n"


def unique_folder(papers_dir: Path, base_slug: str) -> tuple[str, Path]:
    slug = base_slug
    folder = papers_dir / slug
    index = 2
    while folder.exists():
        slug = f"{base_slug}-{index}"
        folder = papers_dir / slug
        index += 1
    return slug, folder


def record_ledger_entry(ledger: dict, scored: ScoredPaper, profile: dict, slug: str, selected_date: date) -> dict:
    candidate = scored.candidate
    entry = {
        "canonical_id": canonical_id(candidate),
        "openalex_id": candidate.get("id"),
        "doi": candidate.get("doi"),
        "arxiv_id": candidate.get("arxiv_id"),
        "selected_date": selected_date.isoformat(),
        "profile": profile["name"],
        "score": scored.score,
        "slug": slug,
    }
    curated_sources = sorted({
        match.get("source")
        for match in candidate.get("curated_matches") or []
        if match.get("source")
    })
    if curated_sources:
        entry["curated_sources"] = curated_sources
    ledger.setdefault("pulled", []).append(entry)
    return entry


def public_paper(candidate: dict) -> dict:
    paper = dict(candidate)
    paper["openalex_id"] = candidate.get("id")
    return paper


def dry_run_message(scored: ScoredPaper, profile: dict) -> str:
    candidate = scored.candidate
    parts = [
        "Selected paper:",
        f"  Title: {candidate.get('title')}",
        f"  Score: {scored.score:.2f} / 100",
        f"  Profile: {profile['name']}",
        f"  Source: {source_url(candidate)}",
        "  Score breakdown:",
    ]
    for key, value in scored.breakdown.items():
        parts.append(f"    - {key}: {value:.2f}")
    curated_matches = candidate.get("curated_matches") or []
    if curated_matches:
        match = curated_matches[0]
        label = CURATED_SOURCE_LABELS.get(match.get("source"), match.get("source") or "Curated source")
        parts += [
            "  Curated evidence:",
            f"    - Curated source: {label}",
            f"    - Issue: {match.get('issue_title')}",
            f"    - Rank: {match.get('rank') if match.get('rank') is not None else 'unranked'}",
            f"    - Paper URL: {match.get('paper_url')}",
        ]
    return "\n".join(parts)


def run_pull(
    profile_path: Path,
    papers_dir: Path = PAPERS_DIR,
    fetcher=fetch_openalex_candidates,
    curated_fetcher=fetch_curated_entries,
    today: date | None = None,
    dry_run: bool = False,
) -> PullResult:
    today = today or date.today()
    profile = load_profile(profile_path)
    ledger = load_ledger(papers_dir)
    candidates = fetcher(profile)
    curated_warning = ""
    if profile.get("curated_sources"):
        try:
            candidates = enrich_candidates_with_curated_matches(candidates, curated_fetcher(profile))
        except Exception as exc:
            curated_warning = f"Curated enrichment skipped: {exc}"
    try:
        scored = select_best_paper(
            candidates,
            profile,
            pulled_id_set(ledger),
            today=today,
            papers_dir=papers_dir if papers_dir.exists() else None,
        )
    except ValueError as exc:
        message = str(exc)
        if curated_warning:
            message = f"{message}\n{curated_warning}"
        return PullResult(None, message, None)

    if dry_run:
        message = dry_run_message(scored, profile)
        if curated_warning:
            message = f"{message}\n{curated_warning}"
        return PullResult(public_paper(scored.candidate), message, None)

    papers_dir.mkdir(parents=True, exist_ok=True)
    slug, folder = unique_folder(papers_dir, slugify(scored.candidate.get("title") or "paper"))
    folder.mkdir(parents=True)
    (folder / "source.md").write_text(source_markdown(scored.candidate, profile, scored, today), encoding="utf-8")
    (folder / "analysis.json").write_text(
        json.dumps(starter_analysis(scored.candidate, slug), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    record_ledger_entry(ledger, scored, profile, slug, today)
    write_ledger(papers_dir, ledger)

    message = "\n".join([
        f"Selected paper: {scored.candidate.get('title')}",
        f"Score: {scored.score:.2f} / 100",
        f"Folder: {folder}",
        "",
        "Next agent-assisted step:",
        f"  Complete papers/{slug}/analysis.json from papers/{slug}/source.md",
        "  Then render:",
        f"  python paper-reading-assistant/scripts/render_report.py --input papers/{slug}/analysis.json --output papers/{slug}/report.html --slug {slug}",
    ])
    if curated_warning:
        message = f"{message}\n{curated_warning}"
    return PullResult(public_paper(scored.candidate), message, folder)


def main() -> int:
    parser = argparse.ArgumentParser(description="Select one research paper for a topic profile.")
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        result = run_pull(args.profile, dry_run=args.dry_run)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(result.message)
    if result.paper is None:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
