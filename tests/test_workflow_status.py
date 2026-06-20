import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "paper-reading-assistant" / "scripts" / "workflow_status.py"


def load_status():
    spec = importlib.util.spec_from_file_location("workflow_status", STATUS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def starter_analysis():
    return {
        "paper": {"title": "A Starter Paper", "url": "https://example.com/paper"},
        "headline": "",
        "plain_summary": "",
        "report_plan": {"sections": []},
    }


def complete_analysis():
    return {
        "paper": {
            "title": "A Complete Paper",
            "authors": ["A. Researcher"],
            "venue": "arXiv",
            "year": 2026,
            "url": "https://example.com/paper",
        },
        "headline": "A complete paper has enough structured analysis to render.",
        "plain_summary": "This is a concise summary of the paper and why it matters.",
        "report_plan": {
            "paper_archetype": "method",
            "reader_goal": "learn and evaluate",
            "narrative_arc": ["problem_context", "learning_path", "quiz"],
            "sections": [
                {
                    "type": "problem_context",
                    "title": "Why this matters",
                    "takeaway": "The problem context is clear.",
                    "content": "The paper addresses a concrete gap.",
                },
                {
                    "type": "learning_path",
                    "title": "Read next",
                    "papers": [
                        {
                            "title": "Related Paper",
                            "url": "https://example.com/related",
                            "why": "It gives useful context.",
                            "read_for": "Background.",
                        }
                    ],
                },
                {
                    "type": "quiz",
                    "title": "Check your understanding",
                    "questions": [
                        {
                            "category": "Paper comprehension",
                            "question": "What is being tested?",
                            "choices": ["A", "B", "C", "D"],
                            "answer": "A",
                            "explanation": "A is correct.",
                        }
                    ],
                },
            ],
        },
    }


def write_paper(folder: Path, analysis: dict | str, *, report=False):
    folder.mkdir(parents=True)
    (folder / "source.md").write_text("# Source\n\nPaper source.", encoding="utf-8")
    if isinstance(analysis, str):
        (folder / "analysis.json").write_text(analysis, encoding="utf-8")
    else:
        (folder / "analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
    if report:
        (folder / "report.html").write_text("<!doctype html><title>Report</title>", encoding="utf-8")


class WorkflowStatusTests(unittest.TestCase):
    def test_starter_analysis_is_analysis_incomplete(self):
        status = load_status()
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "papers" / "starter"
            write_paper(paper, starter_analysis())

            result = status.inspect_slug("starter", papers_dir=Path(tmp) / "papers")

            self.assertEqual(result["status"], "analysis-incomplete")
            self.assertIn("headline", result["missing"])
            self.assertIn("report_plan.sections", result["missing"])

    def test_complete_analysis_is_ready_to_render(self):
        status = load_status()
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "papers" / "complete"
            write_paper(paper, complete_analysis())

            result = status.inspect_slug("complete", papers_dir=Path(tmp) / "papers")

            self.assertEqual(result["status"], "ready-to-render")
            self.assertEqual(result["missing"], [])

    def test_new_so_what_schema_requires_each_lens_when_present(self):
        status = load_status()
        analysis = complete_analysis()
        analysis["so_what"] = {
            "research": {"headline": "Research implication", "next_actions": ["Run better benchmarks"]},
            "product": {"headline": "", "next_actions": []},
            "business": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "papers" / "needs-so-what"
            write_paper(paper, analysis)

            result = status.inspect_slug("needs-so-what", papers_dir=Path(tmp) / "papers")

            self.assertEqual(result["status"], "analysis-incomplete")
            self.assertIn("so_what.product", result["missing"])
            self.assertIn("so_what.business", result["missing"])

    def test_rendered_folder_reports_rendered(self):
        status = load_status()
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "papers" / "rendered"
            write_paper(paper, complete_analysis(), report=True)

            result = status.inspect_slug("rendered", papers_dir=Path(tmp) / "papers")

            self.assertEqual(result["status"], "rendered")

    def test_invalid_json_returns_clear_error_result(self):
        status = load_status()
        with tempfile.TemporaryDirectory() as tmp:
            paper = Path(tmp) / "papers" / "broken"
            write_paper(paper, "{not-json")

            result = status.inspect_slug("broken", papers_dir=Path(tmp) / "papers")

            self.assertEqual(result["status"], "error")
            self.assertIn("Invalid analysis.json", result["error"])

    def test_latest_uses_most_recent_ledger_entry(self):
        status = load_status()
        with tempfile.TemporaryDirectory() as tmp:
            papers_dir = Path(tmp) / "papers"
            write_paper(papers_dir / "older", complete_analysis(), report=True)
            write_paper(papers_dir / "newer", starter_analysis())
            (papers_dir / ".pulled.json").write_text(json.dumps({
                "pulled": [
                    {"slug": "older", "selected_date": "2026-06-01"},
                    {"slug": "newer", "selected_date": "2026-06-19"},
                ]
            }), encoding="utf-8")

            result = status.inspect_latest(papers_dir=papers_dir)

            self.assertEqual(result["slug"], "newer")
            self.assertEqual(result["status"], "analysis-incomplete")


if __name__ == "__main__":
    unittest.main()
