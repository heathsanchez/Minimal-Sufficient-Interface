from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "arc3-kaggle-integration.yml").read_text()


class GeneralizationWorkflowContracts(unittest.TestCase):
    def test_runs_untouched_bt11_with_same_generated_agent(self):
        self.assertIn("bt11-fd9df0622a1a", WORKFLOW)
        self.assertIn("ARC3_UNTOUCHED_BT11_EXECUTED=PASS", WORKFLOW)

    def test_untouched_bt11_is_not_a_success_gate_or_archive(self):
        # This stage is measurement: it must execute and report, not require a
        # hand-coded level count. Promotion happens only after evidence exists.
        self.assertNotIn("ARC3_BT11_ARCHIVE", WORKFLOW)
        self.assertNotIn("test \"$bt11_levels\" -ge", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
