import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEW_PAPER = ROOT / "paper-reading-assistant" / "scripts" / "new_paper.py"
SCRIPTS = ROOT / "paper-reading-assistant" / "scripts"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RemovedNotesContactsTests(unittest.TestCase):
    def test_new_paper_scaffold_has_report_plan_and_no_people_notes_or_template_duplication(self):
        module = load_module(NEW_PAPER, "new_paper")

        self.assertIn("report_plan", module.ANALYSIS_TEMPLATE)
        self.assertNotIn("people", module.ANALYSIS_TEMPLATE)

        with tempfile.TemporaryDirectory() as tmp:
            module.PAPERS_DIR = Path(tmp)
            slug = "test-paper"
            folder = module.scaffold_paper("Test Paper", slug)

            self.assertEqual(folder, Path(tmp) / slug)
            analysis_path = folder / "analysis.json"
            self.assertTrue(analysis_path.exists())
            self.assertFalse((folder / "analysis.template.json").exists())
            self.assertTrue((folder / "source.md").exists())
            self.assertFalse((folder / "notes.md").exists())
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            self.assertIn("report_plan", analysis)

    def test_removed_optional_server_and_packaging_artifacts_are_absent(self):
        self.assertFalse((SCRIPTS / "serve.py").exists())
        self.assertFalse((SCRIPTS / "build_skill.sh").exists())
        self.assertFalse((ROOT / "paper-reading-assistant.skill").exists())


if __name__ == "__main__":
    unittest.main()
