import json
from pathlib import Path
import tempfile
import unittest

from directness_baseline_experiment import CASES, run_experiment
from workflow_optimizer import DevelopmentState, ProblemContract, WorkflowController


class WorkflowOptimizerTest(unittest.TestCase):
    def test_pi1_solves_all_matched_cases_and_pi0_does_not(self):
        rows = run_experiment()["rows"]
        pi0 = [r for r in rows if r["workflow"].startswith("Pi0")]
        pi1 = [r for r in rows if r["workflow"].startswith("Pi1")]
        self.assertTrue(all(not r["solved"] for r in pi0))
        self.assertTrue(all(r["solved"] for r in pi1))

    def test_heldout_identifiers_are_disjoint(self):
        dev = {p.id for c in CASES if c.split == "develop" for p in c.proposals}
        held = {p.id for c in CASES if c.split == "heldout" for p in c.proposals}
        self.assertTrue(dev.isdisjoint(held))

    def test_state_is_machine_readable(self):
        state = DevelopmentState(ProblemContract("t", "v", 1, "s"), "Pi0")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"
            state.write(path)
            self.assertEqual(json.loads(path.read_text())["contract"]["target"], "t")

    def test_every_executed_event_has_provenance_hash(self):
        from directness_baseline_experiment import run_case

        state = run_case(CASES[0], WorkflowController("Pi1", True))
        self.assertTrue(state.memory.provenance)
        self.assertTrue(
            all(len(e["event_sha256"]) == 64 for e in state.memory.provenance)
        )


if __name__ == "__main__":
    unittest.main()
