from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.interventional_quotient import PartialInterventionalQuotient
from metalogic_arc3.replay_ledger import (
    build_ledger,
    restore_ledger,
    validate_ledger,
)


class ReplayLedgerContracts(unittest.TestCase):
    def fixture(self):
        q = PartialInterventionalQuotient()
        for node in ("a", "b", "c"):
            q.observe_node(
                node,
                protected=("NOT_FINISHED", 0),
                legal_actions=(1, 2),
            )
        q.observe_transition("a", 1, "b", outcome=("NOT_FINISHED", 0))
        q.observe_transition("a", 2, "c", outcome=("NOT_FINISHED", 0))
        q.observe_transition("b", 1, "c", outcome=("NOT_FINISHED", 0))
        prefixes = {
            "a": (),
            "b": ((1, None, None),),
            "c": ((2, None, None),),
        }
        payload = build_ledger(
            q,
            prefixes,
            metadata={
                "game_id": "fixture-game",
                "agent_sha256": "a" * 64,
            },
        )
        return q, prefixes, payload

    def test_round_trip_preserves_nodes_edges_and_prefixes(self):
        q, prefixes, payload = self.fixture()
        restored, restored_prefixes = restore_ledger(
            payload,
            expected_game_id="fixture-game",
            expected_agent_sha256="a" * 64,
        )
        self.assertEqual(restored.nodes, q.nodes)
        self.assertEqual(
            {
                source: {
                    action: set(rows)
                    for action, rows in by_action.items()
                }
                for source, by_action in restored.edges.items()
            },
            {
                source: {
                    action: set(rows)
                    for action, rows in by_action.items()
                }
                for source, by_action in q.edges.items()
            },
        )
        self.assertEqual(restored_prefixes, prefixes)

    def test_tamper_is_rejected(self):
        _q, _prefixes, payload = self.fixture()
        bad = copy.deepcopy(payload)
        bad["nodes"]["a"]["legal_actions"] = [1]
        with self.assertRaises(ValueError):
            validate_ledger(bad)

    def test_wrong_agent_is_rejected(self):
        _q, _prefixes, payload = self.fixture()
        with self.assertRaises(ValueError):
            restore_ledger(
                payload,
                expected_game_id="fixture-game",
                expected_agent_sha256="b" * 64,
            )

    def test_wrong_game_is_rejected(self):
        _q, _prefixes, payload = self.fixture()
        with self.assertRaises(ValueError):
            restore_ledger(
                payload,
                expected_game_id="other-game",
                expected_agent_sha256="a" * 64,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
