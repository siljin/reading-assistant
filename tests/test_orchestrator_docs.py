import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "paper-reading-assistant" / "ORCHESTRATOR.md"


class OrchestratorDocsTests(unittest.TestCase):
    def test_orchestrator_documents_agent_boundary_and_required_commands(self):
        text = ORCHESTRATOR.read_text(encoding="utf-8")

        self.assertIn("chat agent performs the LLM reasoning", text)
        self.assertIn("Do not add or request an LLM API key", text)
        self.assertIn("Do not automate ChatGPT/Claude browser UI", text)
        self.assertIn("pull_paper.py --profile", text)
        self.assertIn("workflow_status.py --slug", text)
        self.assertIn("render_report.py", text)


if __name__ == "__main__":
    unittest.main()
