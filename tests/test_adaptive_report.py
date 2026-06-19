import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "paper-reading-assistant" / "scripts" / "render_report.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_report", RENDERER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_adaptive_analysis():
    return {
        "paper": {
            "title": "Adaptive Clinical AI",
            "authors": ["A. Researcher"],
            "venue": "arXiv",
            "year": 2026,
            "url": "https://example.com/paper",
        },
        "slug": "adaptive-clinical-ai",
        "headline": "A clinical AI paper needs workflow-specific explanation.",
        "plain_summary": "This paper studies an adaptive clinical workflow.",
        "report_plan": {
            "paper_archetype": "clinical",
            "reader_goal": "decide usefulness",
            "narrative_arc": [
                "problem_context",
                "experiment_design",
                "real_world_implications",
                "learning_path",
                "quiz",
            ],
            "sections": [
                {
                    "type": "problem_context",
                    "title": "Why this problem matters",
                    "takeaway": "Clinical AI only matters if it fits care delivery.",
                    "content": "The paper studies where clinical reasoning meets workflow.",
                    "visuals": [
                        {
                            "type": "cards",
                            "title": "Three pressures",
                            "items": [
                                {"label": "Safety", "value": "High", "caption": "Bad advice can harm."},
                                {"label": "Workflow", "value": "Hard", "caption": "Clinicians need reviewable output."},
                            ],
                        }
                    ],
                },
                {
                    "type": "experiment_design",
                    "title": "How the study works",
                    "takeaway": "The setup is controlled, not deployed.",
                    "content": "A structured test compares model output with human review.",
                    "visuals": [
                        {
                            "type": "flow",
                            "title": "Study flow",
                            "steps": [
                                {"label": "Case", "caption": "Input scenario"},
                                {"label": "Model", "caption": "AI response"},
                                {"label": "Review", "caption": "Human scoring"},
                            ],
                        },
                        {
                            "type": "heatmap",
                            "title": "Evidence map",
                            "columns": ["Model", "Human", "Risk"],
                            "rows": [
                                {"label": "Accuracy", "cells": ["Strong", "Baseline", "Medium"]},
                                {"label": "Deployment", "cells": ["Untested", "Known", "High"]},
                            ],
                        },
                    ],
                },
                {
                    "type": "real_world_implications",
                    "title": "What to do with it",
                    "takeaway": "Pilot the workflow before trusting the model.",
                    "content": "The implementation risk is mostly operational.",
                    "visuals": [
                        {
                            "type": "funnel",
                            "title": "Translation funnel",
                            "steps": [
                                {"label": "Benchmark", "caption": "Shown", "status": "supported"},
                                {"label": "Pilot", "caption": "Needs proof", "status": "caution"},
                                {"label": "Autonomy", "caption": "Not supported", "status": "gap"},
                            ],
                        },
                        {
                            "type": "matrix",
                            "title": "Opportunity map",
                            "columns": ["Lower risk", "Higher risk"],
                            "rows": ["Higher value", "Lower value"],
                            "cells": [
                                {"label": "Supervised intake", "caption": "Best wedge", "tone": "good"},
                                {"label": "Diagnosis engine", "caption": "Needs evidence", "tone": "caution"},
                                {"label": "FAQ", "caption": "Low differentiation", "tone": "neutral"},
                                {"label": "Autonomous doctor", "caption": "Wrong start", "tone": "bad"},
                            ],
                        },
                    ],
                },
                {
                    "type": "learning_path",
                    "title": "Read next",
                    "takeaway": "Move from foundations to deployment.",
                    "papers": [
                        {
                            "title": "Medical AI Foundations",
                            "url": "https://example.com/foundations",
                            "why": "Explains the base evaluation lineage.",
                            "read_for": "Medical QA and safety framing.",
                        }
                    ],
                },
                {
                    "type": "quiz",
                    "title": "Check your understanding",
                    "takeaway": "Use the paper, do not just remember it.",
                    "questions": [
                        {
                            "category": "Paper understanding",
                            "question": "What does the paper prove?",
                            "choices": ["Autonomy", "A controlled workflow result", "No need for review", "Nothing"],
                            "answer": "A controlled workflow result",
                            "explanation": "The result is bounded by the study setup.",
                        }
                    ],
                },
            ],
        },
    }


class AdaptiveReportTests(unittest.TestCase):
    def test_adaptive_report_plan_renders_sections_and_visuals(self):
        renderer = load_renderer()
        html = renderer.build_html(sample_adaptive_analysis(), "adaptive-clinical-ai")

        self.assertIn('class="adaptive-section section-problem_context"', html)
        self.assertIn('class="adaptive-section section-experiment_design"', html)
        self.assertIn('class="visual visual-flow"', html)
        self.assertIn('class="visual visual-heatmap"', html)
        self.assertIn('class="visual visual-funnel"', html)
        self.assertIn('class="visual visual-matrix"', html)
        self.assertIn('class="learning-card"', html)
        self.assertIn('class="quiz-card"', html)
        self.assertIn("What does the paper prove?", html)

    def test_reports_never_render_notes_or_contacts_even_for_legacy_fields(self):
        renderer = load_renderer()
        analysis = sample_adaptive_analysis()
        analysis["people"] = [
            {
                "name": "Private Connection",
                "role": "Should not render",
                "why": "Old contact feature",
                "linkedin": "https://linkedin.com/in/example",
            }
        ]

        html = renderer.build_html(analysis, "adaptive-clinical-ai")

        forbidden = [
            "notes-card",
            "contenteditable",
            "/api/notes",
            "people-grid",
            "person-card",
            "LinkedIn",
            "People worth reaching out",
            "Private Connection",
        ]
        for text in forbidden:
            self.assertNotIn(text, html)

    def test_legacy_analysis_gets_adaptive_fallback_without_people_or_notes(self):
        renderer = load_renderer()
        analysis = {
            "paper": {"title": "Legacy Method Paper", "url": "https://example.com/legacy"},
            "headline": "A method paper can still render without report_plan.",
            "plain_summary": "The legacy format still has summary text.",
            "eli5": {"analogy": "a careful recipe", "text": "It explains the method simply."},
            "results": [{"claim": "It works", "evidence": "A benchmark", "caveat": "One domain"}],
            "implications": {"research": ["Try stronger baselines"], "practice": ["Validate cheaply"]},
            "people": [{"name": "Should Not Render"}],
        }

        html = renderer.build_html(analysis, "legacy-method-paper")

        self.assertIn('class="adaptive-section section-plain_summary"', html)
        self.assertIn('class="adaptive-section section-results_interpretation"', html)
        self.assertIn("A method paper can still render without report_plan.", html)
        self.assertNotIn("Should Not Render", html)
        self.assertNotIn("notes-card", html)

    def test_synthetic_benchmark_shape_can_use_its_own_section_order(self):
        renderer = load_renderer()
        analysis = {
            "paper": {
                "title": "Small Benchmark for Retrieval Agents",
                "authors": ["B. Builder"],
                "venue": "Synthetic",
                "year": 2026,
                "url": "https://example.com/benchmark",
            },
            "headline": "A benchmark paper should foreground task setup and comparisons.",
            "plain_summary": "This synthetic benchmark evaluates retrieval agents across task families.",
            "report_plan": {
                "paper_archetype": "benchmark",
                "reader_goal": "judge whether the benchmark is useful",
                "narrative_arc": [
                    "experiment_design",
                    "results_interpretation",
                    "limitations_and_caveats",
                    "learning_path",
                    "quiz",
                ],
                "sections": [
                    {
                        "type": "experiment_design",
                        "title": "Benchmark setup first",
                        "takeaway": "For a benchmark, the task definition is the product.",
                        "content": "The report starts with tasks and protocol instead of architecture.",
                        "visuals": [
                            {
                                "type": "table",
                                "title": "Task families",
                                "columns": ["Family", "Metric"],
                                "rows": [["Lookup", "Exact match"], ["Synthesis", "Rubric score"]],
                            }
                        ],
                    },
                    {
                        "type": "results_interpretation",
                        "title": "Compare systems",
                        "takeaway": "The useful visual is a comparison chart.",
                        "content": "A benchmark paper needs score interpretation and caveats.",
                        "visuals": [
                            {
                                "type": "bar_chart",
                                "title": "Scores",
                                "bars": [
                                    {"label": "Baseline", "value": 42, "max": 100},
                                    {"label": "Agent", "value": 68, "max": 100},
                                ],
                            }
                        ],
                    },
                    {
                        "type": "limitations_and_caveats",
                        "title": "Benchmark caveats",
                        "takeaway": "Coverage matters as much as score.",
                        "content": "The benchmark may overrepresent easy retrieval tasks.",
                    },
                    {
                        "type": "learning_path",
                        "title": "Read next",
                        "papers": [
                            {
                                "title": "Benchmark Design",
                                "url": "https://example.com/read-next",
                                "why": "Explains evaluation protocol design.",
                                "read_for": "Benchmark validity.",
                            }
                        ],
                    },
                    {
                        "type": "quiz",
                        "title": "Check your understanding",
                        "questions": [
                            {
                                "category": "Field understanding",
                                "question": "What is the key object in a benchmark paper?",
                                "choices": ["Task protocol", "Logo", "Landing page", "Author count"],
                                "answer": "Task protocol",
                                "explanation": "Benchmark value depends on what is measured and how.",
                            }
                        ],
                    },
                ],
            },
        }

        html = renderer.build_html(analysis, "small-benchmark")

        first_adaptive = html.index('class="adaptive-section section-experiment_design"')
        result_section = html.index('class="adaptive-section section-results_interpretation"')
        self.assertLess(first_adaptive, result_section)
        self.assertIn('class="visual visual-table"', html)
        self.assertIn('class="visual visual-bar_chart"', html)
        self.assertIn("Benchmark setup first", html)


if __name__ == "__main__":
    unittest.main()
