import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PULLER = ROOT / "paper-reading-assistant" / "scripts" / "pull_paper.py"
PROFILES_DIR = ROOT / "profiles"


def load_puller():
    spec = importlib.util.spec_from_file_location("pull_paper", PULLER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def candidate(
    title,
    *,
    abstract="retrieval augmented generation for medical diagnosis",
    year=2026,
    publication_date="2026-05-01",
    citations=10,
    topics=None,
    url="https://arxiv.org/abs/2605.00001",
    openalex_id=None,
    arxiv_id=None,
    is_oa=True,
):
    return {
        "id": openalex_id or f"https://openalex.org/W{abs(hash(title))}",
        "doi": None,
        "title": title,
        "publication_year": year,
        "publication_date": publication_date,
        "cited_by_count": citations,
        "abstract": abstract,
        "authors": ["Ada Researcher", "Ben Scientist"],
        "primary_location": {
            "landing_page_url": url,
            "pdf_url": url.replace("/abs/", "/pdf/") if "arxiv.org/abs/" in url else None,
            "source": {"display_name": "arXiv" if "arxiv.org" in url else "Journal"},
        },
        "open_access": {"is_oa": is_oa, "oa_url": url if is_oa else None},
        "locations": [],
        "topics": [{"display_name": t} for t in (topics or ["Medical Artificial Intelligence"])],
        "arxiv_id": arxiv_id,
    }


class PullPaperTests(unittest.TestCase):
    def test_local_env_files_are_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".env", gitignore)
        self.assertIn(".env.*", gitignore)

    def test_checked_in_config_file_has_structured_selection_and_email_settings(self):
        puller = load_puller()
        config = puller.load_app_config()

        self.assertIn("selection", config)
        self.assertIn("defaults", config["selection"])
        self.assertIn("score_weights", config["selection"])
        self.assertEqual(config["selection"]["defaults"]["recency_days"], 730)
        self.assertEqual(config["selection"]["defaults"]["max_results_to_score"], 50)
        self.assertEqual(config["selection"]["score_weights"]["recency_trend"], 18)
        self.assertIn("sources", config)
        self.assertEqual(config["sources"]["curated_source_labels"]["dair-ai-weekly"], "DAIR AI Papers of the Week")
        self.assertEqual(config["email"]["provider"], "gmail")
        self.assertEqual(config["email"]["providers"]["gmail"]["host"], "smtp.gmail.com")
        self.assertEqual(config["email"]["providers"]["gmail"]["username_placeholder"], "your-gmail-address@gmail.com")
        self.assertEqual(config["email"]["providers"]["gmail"]["password_placeholder"], "your-google-app-password")
        self.assertEqual(config["email"]["providers"]["gmail"]["email_from_placeholder"], "your-gmail-address@gmail.com")
        self.assertEqual(config["email"]["providers"]["gmail"]["email_to_placeholder"], "your-delivery-email@example.com")
        self.assertEqual(config["email"]["smtp"]["host_env"], "REPORT_SMTP_HOST")

    def test_profile_defaults_and_score_weights_come_from_structured_config(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps({
                "selection": {
                    "defaults": {
                        "recency_days": 90,
                        "max_results_to_score": 7,
                        "curated_max_weeks": 3,
                    },
                    "score_weights": {
                        "recency_trend": 41,
                    },
                }
            }), encoding="utf-8")

            config = puller.load_app_config(config_path)
            profile = puller.normalize_profile({"name": "custom", "keywords": ["diagnosis"]}, config=config)
            scored = puller.score_candidate(
                candidate("Fresh Diagnosis Paper", abstract="diagnosis", publication_date="2026-06-19"),
                profile,
                date(2026, 6, 19),
            )

        self.assertEqual(profile["recency_days"], 90)
        self.assertEqual(profile["max_results_to_score"], 7)
        self.assertEqual(profile["curated_max_weeks"], 3)
        self.assertEqual(scored.breakdown["recency_trend"], 41.0)

    def test_run_pull_accepts_config_path_for_domain_defaults(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.json"
            config_path.write_text(json.dumps({
                "selection": {
                    "defaults": {
                        "recency_days": 120,
                        "max_results_to_score": 9,
                        "curated_max_weeks": 4,
                    }
                }
            }), encoding="utf-8")
            profile_path = tmp_path / "profile.json"
            profile_path.write_text(json.dumps({
                "name": "medical-ai",
                "keywords": ["medical diagnosis"],
            }), encoding="utf-8")
            seen_profile = {}

            def fetcher(profile):
                seen_profile.update(profile)
                return [candidate("Medical Diagnosis With Retrieval")]

            result = puller.run_pull(
                profile_path,
                papers_dir=tmp_path / "papers",
                fetcher=fetcher,
                today=date(2026, 6, 19),
                dry_run=True,
                config_path=config_path,
            )

        self.assertIn("Selected paper", result.message)
        self.assertEqual(seen_profile["recency_days"], 120)
        self.assertEqual(seen_profile["max_results_to_score"], 9)
        self.assertEqual(seen_profile["curated_max_weeks"], 4)

    def test_pull_cli_accepts_config_flag(self):
        puller = load_puller()
        profile_path = Path("profiles/medical-ai.json")
        config_path = Path("paper-reading-assistant/config.json")

        with mock.patch.object(sys, "argv", [
            "pull_paper.py",
            "--profile", str(profile_path),
            "--dry-run",
            "--config", str(config_path),
        ]), mock.patch.object(
            puller,
            "run_pull",
            return_value=puller.PullResult({"title": "Paper"}, "Selected paper"),
        ) as run_pull:
            result = puller.main()

        self.assertEqual(result, 0)
        self.assertEqual(run_pull.call_args.kwargs["config_path"], config_path)

    def test_checked_in_profiles_match_expected_schema(self):
        puller = load_puller()
        profiles = sorted(PROFILES_DIR.glob("*.json"))

        self.assertGreaterEqual(len(profiles), 2)
        for profile_path in profiles:
            profile = puller.load_profile(profile_path)
            self.assertEqual(profile["name"], profile_path.stem)
            self.assertGreater(len(profile["keywords"]), 0)
            self.assertIn("max_results_to_score", profile)
            self.assertIn("curated_sources", profile)
            self.assertIn("curated_max_weeks", profile)

        llm_agents = puller.load_profile(PROFILES_DIR / "llm-agents.json")
        self.assertIn("dair-ai-weekly", llm_agents["curated_sources"])

    def test_dair_parser_extracts_weekly_ranked_papers_and_arxiv_ids(self):
        puller = load_puller()
        markdown = """
## Top AI Papers of the Week (June 7 - June 14) - 2026
Paper Links
1) **Self-Harness** - Agent harnesses improve themselves. | [Paper](https://arxiv.org/abs/2606.12345), [Tweet](https://x.com/example/status/1) |
2) MiniMax Sparse Attention - Efficient long-context attention. [Paper](https://arxiv.org/abs/2606.54321)
## Top AI Papers of the Week (May 31 - June 7) - 2026
1) **Older Paper** - Outside the requested recent issue. | [Paper](https://arxiv.org/abs/2605.11111) |
"""

        entries = puller.parse_dair_year_markdown(markdown, max_weeks=1)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["issue_title"], "Top AI Papers of the Week (June 7 - June 14) - 2026")
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[0]["title"], "Self-Harness")
        self.assertEqual(entries[0]["paper_url"], "https://arxiv.org/abs/2606.12345")
        self.assertEqual(entries[0]["arxiv_id"], "2606.12345")
        self.assertEqual(entries[1]["rank"], 2)
        self.assertEqual(entries[1]["title"], "MiniMax Sparse Attention")

    def test_dair_matching_prefers_arxiv_id_over_title_when_available(self):
        puller = load_puller()
        entries = [{
            "source": "dair-ai-weekly",
            "issue_title": "Top AI Papers of the Week",
            "rank": 1,
            "title": "Self-Harness",
            "paper_url": "https://arxiv.org/abs/2606.12345",
            "arxiv_id": "2606.12345",
        }]
        title_collision = candidate("Self-Harness", abstract="agent harness", arxiv_id="2606.99999")
        arxiv_match = candidate("A Different OpenAlex Title", abstract="agent harness", arxiv_id="2606.12345")

        enriched = puller.enrich_candidates_with_curated_matches([title_collision, arxiv_match], entries)

        self.assertNotIn("curated_matches", enriched[0])
        self.assertEqual(enriched[1]["curated_matches"][0]["paper_url"], "https://arxiv.org/abs/2606.12345")

    def test_dair_matching_uses_normalized_title_when_no_arxiv_id_exists(self):
        puller = load_puller()
        entries = [{
            "source": "dair-ai-weekly",
            "issue_title": "Top AI Papers of the Week",
            "rank": None,
            "title": "Skill RAG",
            "paper_url": "https://example.com/skill-rag-paper",
            "arxiv_id": None,
        }]
        paper = candidate("Skill-RAG", abstract="retrieval agent skill")

        enriched = puller.enrich_candidates_with_curated_matches([paper], entries)

        self.assertEqual(enriched[0]["curated_matches"][0]["title"], "Skill RAG")

    def test_curated_popularity_scores_dair_matches_without_dominating_relevance(self):
        puller = load_puller()
        profile = puller.normalize_profile({
            "name": "llm-agents",
            "keywords": ["agent harness", "tool use", "planning"],
            "must_include": ["agent"],
        })
        strong_relevance = candidate(
            "Agent Harness for Tool Use",
            abstract="agent harness tool use planning with language models",
            citations=20,
            arxiv_id="2606.00001",
        )
        weak_curated = candidate(
            "Agent Metadata Catalog",
            abstract="agent metadata catalog",
            citations=20,
            arxiv_id="2606.00002",
        )
        weak_curated["curated_matches"] = [{
            "source": "dair-ai-weekly",
            "issue_title": "Top AI Papers of the Week",
            "rank": 1,
            "paper_url": "https://arxiv.org/abs/2606.00002",
        }]

        scored = puller.score_candidate(weak_curated, profile, date(2026, 6, 19))
        winner = puller.select_best_paper([weak_curated, strong_relevance], profile, set(), today=date(2026, 6, 19))

        self.assertEqual(scored.breakdown["curated_popularity"], 10.0)
        self.assertEqual(winner.candidate["title"], strong_relevance["title"])

    def test_relevance_dominates_weakly_related_high_citation_paper(self):
        puller = load_puller()
        profile = puller.normalize_profile({
            "name": "medical-ai",
            "keywords": ["medical diagnosis", "retrieval augmented generation"],
            "openalex_topics": ["Medical Artificial Intelligence"],
            "recency_days": 365,
            "max_results_to_score": 20,
        })
        relevant = candidate(
            "Retrieval Augmented Generation for Medical Diagnosis",
            citations=25,
            topics=["Medical Artificial Intelligence"],
        )
        famous_irrelevant = candidate(
            "A Highly Cited Paper About Protein Folding",
            abstract="protein folding structure prediction",
            citations=5000,
            topics=["Computational Biology"],
        )

        winner = puller.select_best_paper([famous_irrelevant, relevant], profile, pulled_ids=set(), today=date(2026, 6, 19))

        self.assertEqual(winner.candidate["title"], relevant["title"])
        self.assertGreater(winner.breakdown["relevance"], winner.breakdown["citation_signal"])

    def test_recency_gets_slight_edge_over_citations_for_equally_relevant_papers(self):
        puller = load_puller()
        profile = puller.normalize_profile({
            "name": "medical-ai",
            "keywords": ["medical diagnosis"],
            "recency_days": 730,
            "max_results_to_score": 20,
        })
        fresh = candidate(
            "Fresh Medical Diagnosis Agent",
            abstract="medical diagnosis agent",
            publication_date="2026-06-01",
            citations=5,
        )
        older_more_cited = candidate(
            "Older Medical Diagnosis Agent",
            abstract="medical diagnosis agent",
            publication_date="2025-06-01",
            citations=65,
        )

        winner = puller.select_best_paper([older_more_cited, fresh], profile, pulled_ids=set(), today=date(2026, 6, 19))

        self.assertEqual(winner.candidate["title"], fresh["title"])
        self.assertGreater(winner.breakdown["recency_trend"], winner.breakdown["citation_signal"])

    def test_hard_filters_and_already_pulled_skip_candidates(self):
        puller = load_puller()
        profile = puller.normalize_profile({
            "name": "medical-ai",
            "keywords": ["diagnosis"],
            "must_exclude": ["survey"],
            "recency_days": 3650,
            "max_results_to_score": 20,
        })
        excluded = candidate("A Survey of Diagnosis Models", abstract="diagnosis survey", openalex_id="https://openalex.org/W1")
        already_pulled = candidate("Diagnosis Model", abstract="diagnosis", openalex_id="https://openalex.org/W2")
        fresh = candidate("New Diagnosis Model", abstract="diagnosis", openalex_id="https://openalex.org/W3")

        winner = puller.select_best_paper(
            [excluded, already_pulled, fresh],
            profile,
            pulled_ids={"https://openalex.org/W2"},
            today=date(2026, 6, 19),
        )

        self.assertEqual(winner.candidate["id"], "https://openalex.org/W3")
        self.assertNotIn("survey", winner.candidate["title"].lower())

    def test_already_pulled_checks_all_candidate_identifiers(self):
        puller = load_puller()
        profile = puller.normalize_profile({
            "name": "medical-ai",
            "keywords": ["diagnosis"],
        })
        manual_arxiv = candidate(
            "Manual arXiv Paper",
            abstract="diagnosis",
            citations=1000,
            publication_date="2026-06-01",
            openalex_id="https://openalex.org/W999",
            arxiv_id="2401.05654",
        )
        fresh = candidate(
            "Fresh Diagnosis Paper",
            abstract="diagnosis",
            citations=1,
            publication_date="2024-01-01",
            openalex_id="https://openalex.org/W1000",
            arxiv_id="2606.00001",
        )

        winner = puller.select_best_paper(
            [manual_arxiv, fresh],
            profile,
            pulled_ids={"2401.05654"},
            today=date(2026, 6, 19),
        )

        self.assertEqual(winner.candidate["arxiv_id"], "2606.00001")

    def test_normal_run_creates_one_folder_source_analysis_and_ledger(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile_path = tmp_path / "profile.json"
            profile_path.write_text(json.dumps({
                "name": "medical-ai",
                "keywords": ["medical diagnosis"],
                "recency_days": 3650,
                "max_results_to_score": 20,
            }), encoding="utf-8")

            result = puller.run_pull(
                profile_path,
                papers_dir=tmp_path / "papers",
                fetcher=lambda _profile: [
                    candidate("Medical Diagnosis With Retrieval", abstract="medical diagnosis retrieval", openalex_id="https://openalex.org/W42")
                ],
                today=date(2026, 6, 19),
                dry_run=False,
            )

            folder = result.folder
            self.assertTrue(folder.exists())
            self.assertTrue((folder / "source.md").exists())
            self.assertTrue((folder / "analysis.json").exists())
            self.assertFalse((folder / "report.html").exists())
            self.assertEqual(len([p for p in (tmp_path / "papers").iterdir() if p.is_dir()]), 1)

            source_text = (folder / "source.md").read_text(encoding="utf-8")
            self.assertIn("Score breakdown", source_text)
            self.assertIn("OpenAlex ID: https://openalex.org/W42", source_text)

            analysis = json.loads((folder / "analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(analysis["paper"]["title"], "Medical Diagnosis With Retrieval")
            self.assertIn("report_plan", analysis)

            ledger = json.loads((tmp_path / "papers" / ".pulled.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["pulled"][0]["openalex_id"], "https://openalex.org/W42")

    def test_dry_run_creates_no_files(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile_path = tmp_path / "profile.json"
            profile_path.write_text(json.dumps({
                "name": "medical-ai",
                "keywords": ["medical diagnosis"],
            }), encoding="utf-8")

            result = puller.run_pull(
                profile_path,
                papers_dir=tmp_path / "papers",
                fetcher=lambda _profile: [candidate("Medical Diagnosis With Retrieval")],
                today=date(2026, 6, 19),
                dry_run=True,
            )

            self.assertIsNone(result.folder)
            self.assertFalse((tmp_path / "papers").exists())
            self.assertIn("Selected paper", result.message)

    def test_profile_without_curated_source_does_not_call_curated_fetcher(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile_path = tmp_path / "profile.json"
            profile_path.write_text(json.dumps({
                "name": "medical-ai",
                "keywords": ["medical diagnosis"],
            }), encoding="utf-8")

            def fail_if_called(_profile):
                raise AssertionError("curated fetcher should not be called")

            result = puller.run_pull(
                profile_path,
                papers_dir=tmp_path / "papers",
                fetcher=lambda _profile: [candidate("Medical Diagnosis With Retrieval")],
                curated_fetcher=fail_if_called,
                today=date(2026, 6, 19),
                dry_run=True,
            )

            self.assertIn("Selected paper", result.message)

    def test_dry_run_and_source_markdown_include_curated_evidence(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile_path = tmp_path / "profile.json"
            profile_path.write_text(json.dumps({
                "name": "llm-agents",
                "keywords": ["agent harness"],
                "must_include": ["agent"],
                "curated_sources": ["dair-ai-weekly"],
            }), encoding="utf-8")
            entries = [{
                "source": "dair-ai-weekly",
                "issue_title": "Top AI Papers of the Week (June 7 - June 14) - 2026",
                "rank": 2,
                "title": "Self-Harness",
                "paper_url": "https://arxiv.org/abs/2606.12345",
                "arxiv_id": "2606.12345",
            }]

            dry_result = puller.run_pull(
                profile_path,
                papers_dir=tmp_path / "dry-papers",
                fetcher=lambda _profile: [
                    candidate("Self-Harness", abstract="agent harness tool use", arxiv_id="2606.12345")
                ],
                curated_fetcher=lambda _profile: entries,
                today=date(2026, 6, 19),
                dry_run=True,
            )
            self.assertIn("Curated source: DAIR AI Papers of the Week", dry_result.message)
            self.assertIn("Rank: 2", dry_result.message)
            self.assertFalse((tmp_path / "dry-papers").exists())

            result = puller.run_pull(
                profile_path,
                papers_dir=tmp_path / "papers",
                fetcher=lambda _profile: [
                    candidate("Self-Harness", abstract="agent harness tool use", arxiv_id="2606.12345")
                ],
                curated_fetcher=lambda _profile: entries,
                today=date(2026, 6, 19),
                dry_run=False,
            )

            source_text = (result.folder / "source.md").read_text(encoding="utf-8")
            self.assertIn("Curated source: DAIR AI Papers of the Week", source_text)
            self.assertIn("DAIR rank: 2", source_text)
            self.assertIn("https://arxiv.org/abs/2606.12345", source_text)

            ledger = json.loads((tmp_path / "papers" / ".pulled.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["pulled"][0]["curated_sources"], ["dair-ai-weekly"])

    def test_recurring_run_selects_next_candidate_when_top_was_pulled(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            papers_dir = Path(tmp) / "papers"
            papers_dir.mkdir()
            (papers_dir / ".pulled.json").write_text(json.dumps({
                "pulled": [
                    {
                        "canonical_id": "https://openalex.org/W1",
                        "openalex_id": "https://openalex.org/W1",
                        "selected_date": "2026-06-01",
                        "profile": "medical-ai",
                        "score": 98,
                        "slug": "already-read",
                    }
                ]
            }), encoding="utf-8")
            profile_path = Path(tmp) / "profile.json"
            profile_path.write_text(json.dumps({"name": "medical-ai", "keywords": ["diagnosis"]}), encoding="utf-8")

            result = puller.run_pull(
                profile_path,
                papers_dir=papers_dir,
                fetcher=lambda _profile: [
                    candidate("Already Read Diagnosis Paper", abstract="diagnosis", openalex_id="https://openalex.org/W1", citations=100),
                    candidate("Fresh Diagnosis Paper", abstract="diagnosis", openalex_id="https://openalex.org/W2", citations=50),
                ],
                today=date(2026, 6, 19),
                dry_run=False,
            )

            self.assertEqual(result.paper["openalex_id"], "https://openalex.org/W2")
            ledger = json.loads((papers_dir / ".pulled.json").read_text(encoding="utf-8"))
            self.assertEqual(len(ledger["pulled"]), 2)

    def test_run_returns_message_when_no_new_eligible_paper_exists(self):
        puller = load_puller()
        with tempfile.TemporaryDirectory() as tmp:
            papers_dir = Path(tmp) / "papers"
            papers_dir.mkdir()
            (papers_dir / ".pulled.json").write_text(json.dumps({
                "pulled": [{"canonical_id": "https://openalex.org/W1"}]
            }), encoding="utf-8")
            profile_path = Path(tmp) / "profile.json"
            profile_path.write_text(json.dumps({"name": "medical-ai", "keywords": ["diagnosis"]}), encoding="utf-8")

            result = puller.run_pull(
                profile_path,
                papers_dir=papers_dir,
                fetcher=lambda _profile: [
                    candidate("Already Read Diagnosis Paper", abstract="diagnosis", openalex_id="https://openalex.org/W1")
                ],
                today=date(2026, 6, 19),
                dry_run=False,
            )

            self.assertIsNone(result.paper)
            self.assertIsNone(result.folder)
            self.assertIn("No eligible papers", result.message)


if __name__ == "__main__":
    unittest.main()
