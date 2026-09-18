from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.certified_interventional_quotient import (
    CertifiedInterventionalQuotient,
    CLASSES,
)
from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.runtime import normalize_frame


class CertifiedInterventionalQuotientContracts(unittest.TestCase):
    def test_exact_members_share_only_their_certified_class(self):
        q = CertifiedInterventionalQuotient()
        self.assertEqual(q.class_count, 6)
        self.assertEqual(q.member_count, 13)
        for group in CLASSES:
            contexts = {q.context(member) for member in group}
            self.assertEqual(len(contexts), 1)
            self.assertTrue(next(iter(contexts)).startswith("iq:"))

    def test_unknown_hash_remains_exact(self):
        q = CertifiedInterventionalQuotient()
        digest = "f" * 64
        self.assertEqual(q.context(digest), digest)
        self.assertFalse(q.active(digest))

    def test_controller_ablation_restores_exact_context(self):
        left, right = CLASSES[0]
        controller = ConsequenceController((1, 2, 3, 4), archived_capabilities=())
        frame = {
            "frame": [[[0]]],
            "levels_completed": 0,
            "state": "NOT_FINISHED",
            "available_actions": [1, 2, 3, 4],
        }
        obs = normalize_frame(frame)

        # Exercise the helper directly with pinned evidence identities. The raw
        # runtime Observation type is immutable, so make minimal replacements.
        left_obs = type(obs)(
            obs.levels_completed, obs.state, obs.available_actions,
            obs.frame_digest, left, obs.height, obs.width,
        )
        right_obs = type(obs)(
            obs.levels_completed, obs.state, obs.available_actions,
            obs.frame_digest, right, obs.height, obs.width,
        )
        self.assertEqual(
            controller._consequence_context(left_obs),
            controller._consequence_context(right_obs),
        )
        controller.certified_interventional_quotient_enabled = False
        self.assertEqual(controller._consequence_context(left_obs), left)
        self.assertEqual(controller._consequence_context(right_obs), right)


if __name__ == "__main__":
    unittest.main(verbosity=2)
