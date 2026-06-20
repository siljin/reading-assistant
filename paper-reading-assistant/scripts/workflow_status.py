#!/usr/bin/env python3
"""
workflow_status.py - Read-only status checks for the agent-orchestrated workflow.

This script never calls an LLM and never writes files. It only reports whether a
paper folder is staged, incomplete, ready to render, rendered, or invalid.
"""

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PAPERS_DIR = REPO_ROOT / "papers"


def nonempty(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"Missing {path.name}"
    except json.JSONDecodeError as exc:
        return None, f"Invalid {path.name}: {exc.msg} at line {exc.lineno}, column {exc.colno}"


def has_learning_path(sections: list[dict]) -> bool:
    for section in sections:
        if section.get("type") == "learning_path" and nonempty(section.get("papers")):
            return True
    return False


def has_quiz(sections: list[dict]) -> bool:
    for section in sections:
        if section.get("type") == "quiz" and nonempty(section.get("questions")):
            return True
    return False


def has_so_what_lens(so_what: dict, lens: str) -> bool:
    values = so_what.get(lens) or {}
    if not isinstance(values, dict):
        return False
    if nonempty(values.get("headline")):
        return True
    for value in values.values():
        if isinstance(value, list) and any(nonempty(item) for item in value):
            return True
    return False


def missing_required_fields(analysis: dict) -> list[str]:
    missing = []
    paper = analysis.get("paper") or {}
    if not nonempty(paper.get("title")):
        missing.append("paper.title")
    if not nonempty(paper.get("url")):
        missing.append("paper.url")
    if not nonempty(analysis.get("headline")):
        missing.append("headline")
    if not nonempty(analysis.get("plain_summary")):
        missing.append("plain_summary")

    plan = analysis.get("report_plan") or {}
    sections = plan.get("sections") or []
    if not sections:
        missing.append("report_plan.sections")
    else:
        if not has_learning_path(sections):
            missing.append("report_plan.sections.learning_path")
        if not has_quiz(sections):
            missing.append("report_plan.sections.quiz")
    if "so_what" in analysis:
        so_what = analysis.get("so_what") or {}
        for lens in ("research", "product", "business"):
            if not has_so_what_lens(so_what, lens):
                missing.append(f"so_what.{lens}")
    return missing


def inspect_folder(folder: Path) -> dict:
    result = {
        "slug": folder.name,
        "folder": str(folder),
        "status": "",
        "missing": [],
        "error": "",
    }
    if not folder.exists() or not folder.is_dir():
        result["status"] = "error"
        result["error"] = f"Paper folder not found: {folder}"
        return result

    source_path = folder / "source.md"
    analysis_path = folder / "analysis.json"
    report_path = folder / "report.html"

    if not source_path.exists() and not analysis_path.exists():
        result["status"] = "staged"
        result["missing"] = ["source.md", "analysis.json"]
        return result
    if not analysis_path.exists():
        result["status"] = "staged"
        result["missing"] = ["analysis.json"]
        return result

    analysis, error = load_json(analysis_path)
    if error:
        result["status"] = "error"
        result["error"] = error
        return result

    missing = missing_required_fields(analysis)
    result["missing"] = missing
    if missing:
        result["status"] = "analysis-incomplete"
    elif report_path.exists():
        result["status"] = "rendered"
    else:
        result["status"] = "ready-to-render"
    return result


def inspect_slug(slug: str, papers_dir: Path = PAPERS_DIR) -> dict:
    return inspect_folder(papers_dir / slug)


def latest_slug_from_ledger(papers_dir: Path) -> str | None:
    ledger_path = papers_dir / ".pulled.json"
    ledger, error = load_json(ledger_path)
    if error or not ledger:
        return None
    pulled = ledger.get("pulled") or []
    pulled = [entry for entry in pulled if entry.get("slug")]
    if not pulled:
        return None
    pulled.sort(key=lambda entry: (entry.get("selected_date") or "", entry.get("slug") or ""))
    return pulled[-1]["slug"]


def latest_slug_from_dirs(papers_dir: Path) -> str | None:
    if not papers_dir.exists():
        return None
    folders = [p for p in papers_dir.iterdir() if p.is_dir()]
    if not folders:
        return None
    folders.sort(key=lambda p: p.stat().st_mtime)
    return folders[-1].name


def inspect_latest(papers_dir: Path = PAPERS_DIR) -> dict:
    slug = latest_slug_from_ledger(papers_dir) or latest_slug_from_dirs(papers_dir)
    if not slug:
        return {
            "slug": "",
            "folder": str(papers_dir),
            "status": "error",
            "missing": [],
            "error": "No paper folders found.",
        }
    return inspect_slug(slug, papers_dir=papers_dir)


def exit_code(result: dict) -> int:
    if result["status"] == "error":
        return 2
    if result["status"] in {"staged", "analysis-incomplete"}:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Report paper workflow status.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--slug")
    group.add_argument("--latest", action="store_true")
    args = parser.parse_args()

    result = inspect_latest() if args.latest else inspect_slug(args.slug)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
