from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.certified_memory import CertifiedArcMemoryGraph
from metalogic_arc3.requalification_controller import CertifiedConsequenceController


def frame(grid, *, level=0, actions=(3,), state="NOT_FINISHED", full_reset=False):
    return {
        "frame": [grid],
        "levels_completed": level,
        "state": state,
        "available_actions": list(actions),
        "full_reset": full_reset,
    }


class CertifiedMemoryContracts(unittest.TestCase):
    def test_contract_is_canonical_restartable_and_source_scoped(self):
        mg = CertifiedArcMemoryGraph()
        source = (0, "NOT_FINISHED", (3,), 2, 2, "source")
        program = ((3, None, None), (3, None, None))
        mg.add_capability(source, program, source_level=0, target_level=1)
        checkpoints = (
            (0, program[0], "primitive:3", (1, 1, 1, 0, 0, 1)),
            (1, program[1], "primitive:3", (1, 1, 1, 0, 0, 1)),
        )
        digest = mg.add_capability_contract(
            source,
            program,
            source_level=0,
            target_level=1,
            checkpoints=checkpoints,
        )
        self.assertEqual(len(digest), 64)
        candidates = mg.certified_capability_candidates(for_level=1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["program"], program)
        self.assertEqual(candidates[0]["checkpoints"], checkpoints)

        text = mg.text()
        self.assertTrue(text.startswith("MG-ARC5\n"))
        restarted = CertifiedArcMemoryGraph.parse(text)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.digest(), mg.digest())
        self.assertEqual(restarted.certified_capability_candidates(1), candidates)

    def test_legacy_mg_arc4_loads_without_fabricated_certificate(self):
        legacy = CertifiedArcMemoryGraph()
        source = (0, "NOT_FINISHED", (3,), 2, 2, "source")
        legacy.add_capability(source, ((3, None, None),), source_level=0, target_level=1)
        payload = legacy._payload()
        payload.pop("capability_contracts", None)
        text = "MG-ARC4\n" + json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        restored = CertifiedArcMemoryGraph.parse(text)
        self.assertEqual(restored.capability_count, 1)
        self.assertEqual(restored.certified_capability_candidates(1), ())

    def test_malformed_checkpoint_action_is_rejected(self):
        mg = CertifiedArcMemoryGraph()
        source = (0, "NOT_FINISHED", (3,), 2, 2, "source")
        program = ((3, None, None),)
        mg.add_capability(source, program, source_level=0, target_level=1)
        with self.assertRaises(ValueError):
            mg.add_capability_contract(
                source,
                program,
                source_level=0,
                target_level=1,
                checkpoints=((0, (4, None, None), "primitive:4", (1, 1, 1, 0, 0, 1)),),
            )


class RequalificationControllerContracts(unittest.TestCase):
    def _source_capability(self) -> CertifiedConsequenceController:
        """Earn a two-action source capability with one portable process effect.

        The second action crosses the level boundary and deliberately changes the
        whole visible grid. That endpoint replacement is protected by
        LEVEL_INCREMENT but must not become a target process checkpoint.
        """
        c = CertifiedConsequenceController((3,), archived_capabilities=(), max_transfer_depth=8)
        first = c.observe_and_choose(frame([[0, 0], [0, 0]], level=0))
        self.assertEqual(first.action_id, 3)
        second = c.observe_and_choose(frame([[1, 0], [0, 0]], level=0))
        self.assertEqual(second.action_id, 3)
        probe = c.observe_and_choose(frame([[9, 9], [9, 9]], level=1))
        self.assertEqual(probe.source, "transfer_probe")
        self.assertEqual(c.memory.capability_count, 1)
        candidate = c.memory.certified_capability_candidates(1)[0]
        self.assertEqual(candidate["program"], ((3, None, None), (3, None, None)))
        self.assertEqual(len(candidate["checkpoints"]), 1)
        return c

    def test_level_boundary_effect_is_not_a_process_checkpoint(self):
        c = self._source_capability()
        candidate = c.memory.certified_capability_candidates(1)[0]
        self.assertEqual(candidate["protected_outcome"], "LEVEL_INCREMENT")
        self.assertEqual(candidate["checkpoints"], (
            (0, (3, None, None), "primitive:3", (1, 1, 1, 0, 0, 1)),
        ))

    def test_source_witness_is_captured_only_after_progress(self):
        c = CertifiedConsequenceController((3,), archived_capabilities=(), max_transfer_depth=8)
        c.observe_and_choose(frame([[0, 0], [0, 0]], level=0))
        c.observe_and_choose(frame([[1, 0], [0, 0]], level=0))
        self.assertEqual(c.memory.certified_capability_candidates(0), ())
        c.observe_and_choose(frame([[9, 9], [9, 9]], level=1))
        candidate = c.memory.certified_capability_candidates(1)[0]
        self.assertEqual(candidate["protected_outcome"], "LEVEL_INCREMENT")
        self.assertEqual(len(candidate["checkpoints"]), 1)
        self.assertEqual(candidate["checkpoints"][0][2], "primitive:3")
        self.assertEqual(candidate["checkpoints"][0][3], (1, 1, 1, 0, 0, 1))

    def test_mismatch_stops_target_reuse_without_refuting_source(self):
        c = self._source_capability()
        next_token = c.observe_and_choose(frame([[9, 9], [9, 9]], level=1))
        self.assertNotIn(next_token.source, ("transfer_probe", "transfer"))
        trial = c.memory.transfer_trial(1)
        self.assertEqual(trial["status"], "CONTRACT_MISMATCH")
        self.assertEqual(trial["matched"], 0)
        self.assertEqual(c.memory.capability_count, 1)
        self.assertEqual(c.memory.refuted_count, 0)

    def test_matching_probe_requalifies_then_allows_bounded_transfer(self):
        c = self._source_capability()
        second = c.observe_and_choose(frame([[8, 9], [9, 9]], level=1))
        self.assertEqual(c.memory.transfer_trial(1)["status"], "PREFIX_REQUALIFIED")
        self.assertEqual(c.memory.transfer_trial(1)["matched"], 1)
        self.assertEqual(second.source, "transfer")

        tokens = [second]
        for i in range(16):
            tokens.append(c.observe_and_choose(frame([[8 - (i % 2), 9], [9, 9]], level=1)))
        speculative = [t for t in tokens if t.source in ("transfer_probe", "transfer")]
        self.assertLessEqual(len(speculative), 7)
        self.assertLessEqual(c.memory.transfer_trial(1)["issued"], 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
