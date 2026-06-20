import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
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


def write_temp_analysis(tmp_path: Path, analysis: dict | None = None) -> Path:
    analysis_path = tmp_path / "analysis.json"
    analysis_path.write_text(
        json.dumps(analysis or sample_adaptive_analysis()),
        encoding="utf-8",
    )
    return analysis_path


class AdaptiveReportTests(unittest.TestCase):
    def test_insight_dashboard_so_what_and_source_link_render_prominently(self):
        renderer = load_renderer()
        analysis = sample_adaptive_analysis()
        analysis["insight_dashboard"] = {
            "cards": [
                {
                    "label": "Evidence base",
                    "value": "300+ papers",
                    "caption": "Qualitative survey of the field.",
                },
                {
                    "label": "Builder readiness",
                    "value": "Tool agents: high",
                    "caption": "Physical agents remain early.",
                },
            ],
            "primary_visuals": [
                {
                    "type": "bar_chart",
                    "title": "Maturity by area",
                    "bars": [
                        {"label": "Tool use", "value": 8, "max": 10},
                        {"label": "Robotics", "value": 3, "max": 10},
                    ],
                },
                {
                    "type": "line_chart",
                    "title": "Field momentum",
                    "points": [
                        {"label": "2021", "value": 1},
                        {"label": "2022", "value": 4},
                        {"label": "2023", "value": 9},
                    ],
                }
            ],
        }
        analysis["evidence_profile"] = {
            "claims": [
                {
                    "claim": "Tool-using agents are product-adjacent.",
                    "support": 8,
                    "risk": 5,
                    "caption": "Supported by many systems, but reliability remains uneven.",
                }
            ]
        }
        analysis["so_what"] = {
            "research": {
                "headline": "Build better agent benchmarks.",
                "implications": ["Current demos are hard to compare."],
                "open_questions": ["How should sociability and safety be measured?"],
                "next_actions": ["Design shared evaluation suites."],
            },
            "product": {
                "headline": "Ship supervised tool agents first.",
                "opportunities": ["Research assistants and coding copilots."],
                "guardrails": ["Human review before consequential actions."],
                "next_actions": ["Pilot in internal workflows."],
            },
            "business": {
                "headline": "Sell reliability, not autonomy.",
                "market_openings": ["Domain-specific agent services."],
                "adoption_blockers": ["Liability for wrong actions."],
                "risks": ["Cost and trust failures."],
                "next_actions": ["Define accountability boundaries."],
            },
        }
        analysis["opportunity_matrix"] = {
            "x_axis": "Feasibility",
            "y_axis": "Strategic value",
            "columns": ["Lower feasibility", "Higher feasibility"],
            "rows": ["Higher value", "Lower value"],
            "cells": [
                {"label": "Agent teams", "caption": "Promising but brittle.", "tone": "caution"},
                {"label": "Research assistant", "caption": "Build now.", "tone": "good"},
                {"label": "Humanoid autonomy", "caption": "Too early.", "tone": "bad"},
                {"label": "FAQ bot", "caption": "Easy but commoditized.", "tone": "neutral"},
            ],
        }

        html = renderer.build_html(analysis, "adaptive-clinical-ai")

        self.assertIn('class="source-button"', html)
        self.assertIn('href="https://example.com/paper"', html)
        self.assertIn("insight-dashboard", html)
        self.assertIn("Evidence base", html)
        self.assertIn('class="visual visual-bar_chart"', html)
        self.assertIn('class="visual visual-line_chart"', html)
        self.assertIn("Field momentum", html)
        self.assertIn('class="evidence-profile"', html)
        self.assertIn("Tool-using agents are product-adjacent.", html)
        self.assertIn("so-what-section", html)
        self.assertIn("Build better agent benchmarks.", html)
        self.assertIn("Ship supervised tool agents first.", html)
        self.assertIn("Sell reliability, not autonomy.", html)
        self.assertIn('class="visual visual-matrix"', html)
        self.assertIn("Research assistant", html)
        self.assertIn("data-lens-tab", html)

    def test_archetype_modules_adapt_without_forcing_survey_layout(self):
        renderer = load_renderer()
        survey = sample_adaptive_analysis()
        survey["report_plan"]["paper_archetype"] = "survey"
        method = sample_adaptive_analysis()
        method["report_plan"]["paper_archetype"] = "method"

        survey_html = renderer.build_html(survey, "survey-paper")
        method_html = renderer.build_html(method, "method-paper")

        self.assertIn("Field map", survey_html)
        self.assertIn("Opportunity matrix", survey_html)
        self.assertIn("Architecture flow", method_html)
        self.assertIn("Implementation feasibility", method_html)
        self.assertNotIn("Architecture flow", survey_html)
        self.assertNotIn("Field map", method_html)

    def test_context_sections_render_before_dashboard_and_so_what(self):
        renderer = load_renderer()
        analysis = sample_adaptive_analysis()
        analysis["insight_dashboard"] = {
            "cards": [{"label": "Evidence base", "value": "Controlled study", "caption": "Context-dependent"}],
            "primary_visuals": [],
        }
        analysis["so_what"] = {
            "research": {"headline": "Research implication", "next_actions": ["Test the workflow"]},
            "product": {"headline": "Product implication", "next_actions": ["Pilot with review"]},
            "business": {"headline": "Business implication", "next_actions": ["Price accountability"]},
        }

        html = renderer.build_html(analysis, "adaptive-clinical-ai")

        summary_idx = html.index('class="summary-panel adaptive-section section-plain_summary"')
        context_idx = html.index('class="adaptive-section section-problem_context"')
        dashboard_idx = html.index('<section class="insight-dashboard adaptive-section"')
        so_what_idx = html.index('<section class="so-what-section adaptive-section"')
        experiment_idx = html.index('class="adaptive-section section-experiment_design"')

        self.assertLess(summary_idx, context_idx)
        self.assertLess(context_idx, dashboard_idx)
        self.assertLess(dashboard_idx, so_what_idx)
        self.assertLess(so_what_idx, experiment_idx)

    def test_top_section_menu_matches_rendered_order_and_progress_hooks(self):
        renderer = load_renderer()
        analysis = sample_adaptive_analysis()
        analysis["insight_dashboard"] = {
            "cards": [{"label": "Evidence base", "value": "Controlled study", "caption": "Context-dependent"}],
            "primary_visuals": [],
        }
        analysis["so_what"] = {
            "research": {"headline": "Research implication", "next_actions": ["Test the workflow"]},
            "product": {"headline": "Product implication", "next_actions": ["Pilot with review"]},
            "business": {"headline": "Business implication", "next_actions": ["Price accountability"]},
        }

        html = renderer.build_html(analysis, "adaptive-clinical-ai")

        self.assertIn('class="section-menu"', html)
        self.assertIn('aria-label="Report sections"', html)
        self.assertIn('id="reading-progress-bar"', html)
        self.assertIn("data-section-link", html)
        self.assertIn("IntersectionObserver", html)
        self.assertIn("requestAnimationFrame", html)
        self.assertIn("updateActiveSection", html)
        self.assertIn("getBoundingClientRect", html)
        self.assertNotIn("section-menu-label", html)
        self.assertNotIn("reading-progress-label", html)
        self.assertNotIn("0% read", html)
        self.assertNotIn("% read", html)
        self.assertNotIn("section-chip", html)

        expected_links = [
            ("section-plain_summary", "Plain-language summary"),
            ("section-problem_context", "Why this problem matters"),
            ("section-insight_dashboard", "Insight dashboard"),
            ("section-so_what", "So what"),
            ("section-experiment_design", "How the study works"),
            ("section-real_world_implications", "What to do with it"),
            ("section-learning_path", "Read next"),
            ("section-quiz", "Check your understanding"),
        ]
        previous_link_idx = -1
        previous_section_idx = -1
        for anchor_id, label in expected_links:
            link = f'href="#{anchor_id}"'
            target = f'id="{anchor_id}"'
            self.assertIn(link, html)
            self.assertIn(target, html)
            link_idx = html.index(link)
            section_idx = html.index(target)
            self.assertGreater(link_idx, previous_link_idx)
            self.assertGreater(section_idx, previous_section_idx)
            self.assertIn(f">{label}</a>", html)
            previous_link_idx = link_idx
            previous_section_idx = section_idx

        context_link_idx = html.index('href="#section-problem_context"')
        dashboard_link_idx = html.index('href="#section-insight_dashboard"')
        so_what_link_idx = html.index('href="#section-so_what"')
        experiment_link_idx = html.index('href="#section-experiment_design"')
        self.assertLess(context_link_idx, dashboard_link_idx)
        self.assertLess(dashboard_link_idx, so_what_link_idx)
        self.assertLess(so_what_link_idx, experiment_link_idx)

    def test_render_cli_without_email_writes_report_and_does_not_use_smtp(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            missing_env_path = tmp_path / "missing.env"
            stdout = io.StringIO()

            with mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--env-file", str(missing_env_path),
            ]), mock.patch("smtplib.SMTP") as smtp, mock.patch("sys.stdout", stdout):
                result = renderer.main()

            self.assertEqual(result, 0)
            self.assertTrue(output_path.exists())
            smtp.assert_not_called()
            self.assertIn("Email delivery skipped", stdout.getvalue())
            self.assertIn("REPORT_EMAIL_TO", stdout.getvalue())

    def test_render_cli_with_email_sends_generated_report_attachment(self):
        renderer = load_renderer()
        env = {
            "REPORT_SMTP_HOST": "smtp.example.com",
            "REPORT_SMTP_PORT": "587",
            "REPORT_SMTP_USERNAME": "sender@example.com",
            "REPORT_SMTP_PASSWORD": "secret",
            "REPORT_EMAIL_FROM": "sender@example.com",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"

            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--email-to", "reader@example.com",
            ]), mock.patch("smtplib.SMTP") as smtp:
                smtp_client = smtp.return_value.__enter__.return_value
                smtp_client.send_message.side_effect = lambda _msg: self.assertTrue(output_path.exists())

                result = renderer.main()

            self.assertEqual(result, 0)
            smtp.assert_called_once_with("smtp.example.com", 587, timeout=30)
            smtp_client.starttls.assert_called_once()
            smtp_client.login.assert_called_once_with("sender@example.com", "secret")
            smtp_client.send_message.assert_called_once()
            message = smtp_client.send_message.call_args.args[0]
            self.assertEqual(message["To"], "reader@example.com")
            self.assertEqual(message["From"], "sender@example.com")
            self.assertEqual(message["Subject"], "Paper report: Adaptive Clinical AI")
            body = message.get_body(preferencelist=("plain",)).get_content()
            self.assertIn("Attached is the generated research paper report.", body)
            self.assertIn("Title: Adaptive Clinical AI", body)
            self.assertIn("Report file: report.html", body)
            attachments = list(message.iter_attachments())
            self.assertEqual(len(attachments), 1)
            self.assertEqual(attachments[0].get_filename(), "report.html")
            self.assertEqual(attachments[0].get_content_type(), "text/html")
            self.assertIn("<!DOCTYPE html>", attachments[0].get_content())

    def test_render_cli_with_email_uses_structured_config_env_names(self):
        renderer = load_renderer()
        env = {
            "MAIL_HOST": "smtp.custom.example",
            "MAIL_PORT": "2525",
            "MAIL_USERNAME": "custom-sender@example.com",
            "MAIL_PASSWORD": "custom-secret",
            "MAIL_FROM": "custom-sender@example.com",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            config_path = tmp_path / "config.json"
            config_path.write_text(json.dumps({
                "email": {
                    "smtp": {
                        "host_env": "MAIL_HOST",
                        "port_env": "MAIL_PORT",
                        "default_port": 2525,
                        "username_env": "MAIL_USERNAME",
                        "password_env": "MAIL_PASSWORD",
                        "from_env": "MAIL_FROM",
                        "starttls_ports": [2525],
                    }
                }
            }), encoding="utf-8")

            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--email-to", "reader@example.com",
                "--config", str(config_path),
            ]), mock.patch("smtplib.SMTP") as smtp:
                smtp_client = smtp.return_value.__enter__.return_value

                result = renderer.main()

        self.assertEqual(result, 0)
        smtp.assert_called_once_with("smtp.custom.example", 2525, timeout=30)
        smtp_client.starttls.assert_called_once()
        smtp_client.login.assert_called_once_with("custom-sender@example.com", "custom-secret")
        message = smtp_client.send_message.call_args.args[0]
        self.assertEqual(message["From"], "custom-sender@example.com")
        self.assertEqual(message["To"], "reader@example.com")

    def test_render_cli_with_email_uses_gmail_provider_defaults_from_config(self):
        renderer = load_renderer()
        env = {
            "REPORT_SMTP_USERNAME": "sender@gmail.com",
            "REPORT_SMTP_PASSWORD": "google-app-password",
            "REPORT_EMAIL_FROM": "sender@gmail.com",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"

            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--email-to", "reader@example.com",
            ]), mock.patch("smtplib.SMTP") as smtp:
                smtp_client = smtp.return_value.__enter__.return_value

                result = renderer.main()

        self.assertEqual(result, 0)
        smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        smtp_client.starttls.assert_called_once()
        smtp_client.login.assert_called_once_with("sender@gmail.com", "google-app-password")

    def test_render_cli_with_email_loads_missing_values_from_dotenv(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            dotenv_path = tmp_path / ".env"
            dotenv_path.write_text("\n".join([
                "REPORT_SMTP_USERNAME=dotenv-sender@gmail.com",
                "REPORT_SMTP_PASSWORD='dotenv app password'",
                "REPORT_EMAIL_FROM=dotenv-sender@gmail.com",
                "REPORT_SMTP_PORT=587",
            ]), encoding="utf-8")
            stdout = io.StringIO()

            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--email-to", "reader@example.com",
                "--env-file", str(dotenv_path),
            ]), mock.patch("smtplib.SMTP") as smtp, mock.patch("sys.stdout", stdout):
                smtp_client = smtp.return_value.__enter__.return_value

                result = renderer.main()

        self.assertEqual(result, 0)
        smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        smtp_client.login.assert_called_once_with("dotenv-sender@gmail.com", "dotenv app password")
        self.assertIn("Loaded local env file", stdout.getvalue())
        self.assertIn("Email delivery configured", stdout.getvalue())

    def test_render_cli_uses_dotenv_default_recipient_when_email_to_omitted(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            dotenv_path = tmp_path / ".env"
            dotenv_path.write_text("\n".join([
                "REPORT_SMTP_USERNAME=sender@gmail.com",
                "REPORT_SMTP_PASSWORD=google-app-password",
                "REPORT_EMAIL_FROM=sender@gmail.com",
                "REPORT_EMAIL_TO=sender@gmail.com",
            ]), encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--env-file", str(dotenv_path),
            ]), mock.patch("smtplib.SMTP") as smtp:
                result = renderer.main()

        self.assertEqual(result, 0)
        message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        self.assertEqual(message["To"], "sender@gmail.com")

    def test_render_cli_skips_blank_dotenv_default_recipient(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            dotenv_path = tmp_path / ".env"
            dotenv_path.write_text("\n".join([
                "REPORT_SMTP_USERNAME=sender@gmail.com",
                "REPORT_SMTP_PASSWORD=google-app-password",
                "REPORT_EMAIL_FROM=sender@gmail.com",
                "REPORT_EMAIL_TO=   ",
            ]), encoding="utf-8")
            stdout = io.StringIO()

            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--env-file", str(dotenv_path),
            ]), mock.patch("smtplib.SMTP") as smtp, mock.patch("sys.stdout", stdout):
                result = renderer.main()

            self.assertEqual(result, 0)
            self.assertTrue(output_path.exists())
            smtp.assert_not_called()
            self.assertIn("Email delivery skipped", stdout.getvalue())
            self.assertIn("REPORT_EMAIL_TO is blank", stdout.getvalue())

    def test_render_cli_email_to_overrides_dotenv_default_recipient(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            dotenv_path = tmp_path / ".env"
            dotenv_path.write_text("\n".join([
                "REPORT_SMTP_USERNAME=sender@gmail.com",
                "REPORT_SMTP_PASSWORD=google-app-password",
                "REPORT_EMAIL_FROM=sender@gmail.com",
                "REPORT_EMAIL_TO=default-reader@example.com",
            ]), encoding="utf-8")

            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--email-to", "override-reader@example.com",
                "--env-file", str(dotenv_path),
            ]), mock.patch("smtplib.SMTP") as smtp:
                result = renderer.main()

        self.assertEqual(result, 0)
        message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        self.assertEqual(message["To"], "override-reader@example.com")

    def test_dotenv_loader_does_not_override_existing_environment_values(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as tmp:
            dotenv_path = Path(tmp) / ".env"
            dotenv_path.write_text("\n".join([
                "REPORT_SMTP_USERNAME=dotenv-sender@gmail.com",
                "REPORT_SMTP_PASSWORD=dotenv-password",
                "REPORT_EMAIL_FROM=dotenv-sender@gmail.com",
            ]), encoding="utf-8")
            environ = {
                "REPORT_SMTP_USERNAME": "existing-sender@gmail.com",
                "REPORT_SMTP_PASSWORD": "existing-password",
            }

            renderer.load_dotenv(dotenv_path, environ=environ)

        self.assertEqual(environ["REPORT_SMTP_USERNAME"], "existing-sender@gmail.com")
        self.assertEqual(environ["REPORT_SMTP_PASSWORD"], "existing-password")
        self.assertEqual(environ["REPORT_EMAIL_FROM"], "dotenv-sender@gmail.com")

    def test_render_cli_with_email_missing_config_keeps_report_and_returns_error(self):
        renderer = load_renderer()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            missing_env_path = tmp_path / "missing.env"
            stderr = io.StringIO()

            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--email-to", "reader@example.com",
                "--env-file", str(missing_env_path),
            ]), mock.patch("smtplib.SMTP") as smtp, mock.patch("sys.stderr", stderr):
                result = renderer.main()

            self.assertEqual(result, 1)
            self.assertTrue(output_path.exists())
            smtp.assert_not_called()
            self.assertIn("Missing email configuration", stderr.getvalue())
            self.assertIn("REPORT_SMTP_USERNAME", stderr.getvalue())

    def test_render_cli_with_email_smtp_failure_keeps_report_and_returns_error(self):
        renderer = load_renderer()
        env = {
            "REPORT_SMTP_HOST": "smtp.example.com",
            "REPORT_SMTP_PORT": "587",
            "REPORT_SMTP_USERNAME": "sender@example.com",
            "REPORT_SMTP_PASSWORD": "secret",
            "REPORT_EMAIL_FROM": "sender@example.com",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            analysis_path = write_temp_analysis(tmp_path)
            output_path = tmp_path / "report.html"
            stderr = io.StringIO()

            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "argv", [
                "render_report.py",
                "--input", str(analysis_path),
                "--output", str(output_path),
                "--slug", "adaptive-clinical-ai",
                "--email-to", "reader@example.com",
            ]), mock.patch("smtplib.SMTP") as smtp, mock.patch("sys.stderr", stderr):
                smtp_client = smtp.return_value.__enter__.return_value
                smtp_client.send_message.side_effect = RuntimeError("smtp down")

                result = renderer.main()

            self.assertEqual(result, 1)
            self.assertTrue(output_path.exists())
            self.assertIn("Email send failed", stderr.getvalue())
            self.assertIn("smtp down", stderr.getvalue())

    def test_visual_aliases_render_instead_of_disappearing(self):
        renderer = load_renderer()
        analysis = sample_adaptive_analysis()
        analysis["report_plan"]["sections"] = [
            {
                "type": "problem_context",
                "title": "Visual aliases",
                "content": "The renderer should normalize common analysis shapes.",
                "visuals": [
                    {
                        "type": "timeline",
                        "title": "Technology evolution",
                        "data": [
                            {"era": "1950s-80s", "label": "Symbolic Agents", "note": "Rules and expert systems."},
                            {"era": "2022-", "label": "LLM Agents", "note": "General reasoning plus tools."},
                        ],
                    },
                    {
                        "type": "flow",
                        "title": "Agent loop",
                        "steps": [
                            {"label": "Perceive", "note": "Read the environment."},
                            {"label": "Act", "note": "Use a tool."},
                        ],
                    },
                    {
                        "type": "comparison",
                        "title": "Tool use vs embodied action",
                        "rows": [
                            {"aspect": "Maturity", "tool_use": "Production-adjacent", "embodied": "Research demo"},
                            {"aspect": "Failure", "tool_use": "Wrong API call", "embodied": "Unsafe motion"},
                        ],
                    },
                    {
                        "type": "matrix",
                        "title": "Coverage matrix",
                        "x_label": "Severity",
                        "y_label": "Coverage",
                        "cells": [
                            {"x": "High", "y": "Well covered", "items": ["Hallucination", "Misuse"]},
                            {"x": "High", "y": "Undercovered", "items": ["Cost", "Production failures"]},
                        ],
                    },
                    {
                        "type": "funnel",
                        "title": "Readiness ladder",
                        "stages": [
                            {"label": "Demo", "description": "Controlled examples"},
                            {"label": "Product", "description": "Accountable deployment"},
                        ],
                    },
                ],
            }
        ]

        html = renderer.build_html(analysis, "visual-aliases")

        self.assertIn('class="visual visual-timeline"', html)
        self.assertIn("1950s-80s", html)
        self.assertIn("Rules and expert systems.", html)
        self.assertIn("Read the environment.", html)
        self.assertIn('class="visual visual-comparison"', html)
        self.assertIn("Production-adjacent", html)
        self.assertIn('class="visual visual-matrix"', html)
        self.assertIn("Hallucination", html)
        self.assertIn('class="visual visual-funnel"', html)
        self.assertIn("Controlled examples", html)

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
        self.assertIn('class="section-menu"', html)
        self.assertIn('href="#section-plain_summary"', html)
        self.assertIn('id="section-plain_summary"', html)
        self.assertIn('id="reading-progress-bar"', html)
        self.assertNotIn("reading-progress-label", html)
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
