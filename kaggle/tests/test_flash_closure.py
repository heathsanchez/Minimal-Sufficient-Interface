from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metalogic_arc3.flash_ledger import (
    ACTIVE, CANCELLED, PENDING, REVOKED,
    EvidenceRef, FlashLedger, GlobalCapability, Probe, Residual,
)
from metalogic_arc3.flash_closure import run_to_fixed_point
from metalogic_arc3.flash_scheduler import choose_wave


def cap(
    ledger: FlashLedger,
    cid: str,
    kind: str,
    game: str,
    scope: dict,
    consequence: tuple,
    *,
    cost: int = 0,
    witness_key: str | None = None,
    dependencies: set[str] | None = None,
):
    ref = EvidenceRef(game, kind, "test-run", witness_key or cid)
    ledger.add_evidence(ref)
    item = GlobalCapability(
        capability_id=cid,
        kind=kind,
        source_games={game},
        scope=scope,
        consequence_signature=consequence,
        exact_witnesses=[ref],
        protected_effect=None,
        acquisition_cost=cost,
        authority="unit-test",
        dependencies=set(dependencies or ()),
    )
    ledger.add_capability(item)
    return item


def residual_probe(
    ledger: FlashLedger,
    pid: str,
    game: str,
    *,
    cost: int,
    cancellation: set[str],
    purpose: str = "unit",
):
    rid = "res:" + pid
    ledger.add_residual(Residual(rid, game, "test", cost, {"x"}))
    ledger.add_probe(Probe(
        probe_id=pid,
        game=game,
        exact_context=None,
        intervention=("test",),
        residuals_addressed={rid},
        proposal_score=1.0,
        expected_cost=cost,
        original_reason="unit",
        cancellation_conditions=cancellation,
        metadata={"purpose": purpose},
    ))


class FlashContracts(unittest.TestCase):
    def test_deterministic_serialization_and_no_double_payment(self):
        a = FlashLedger()
        b = FlashLedger()
        ref = EvidenceRef("g", "k", "run", "key", "sha")
        self.assertEqual(a.add_evidence(ref), a.add_evidence(ref))
        b.add_evidence(ref)
        self.assertEqual(a.content_hash(), b.content_hash())
        self.assertEqual(len(a.raw_evidence), 1)

    def test_flash_fixed_point_compiles_route_and_cancels_probe(self):
        ledger = FlashLedger()
        cap(
            ledger, "long", "protected_progress", "g",
            {"route_key": "g:L1"}, ("L1",), cost=67,
        )
        cap(
            ledger, "short", "protected_progress", "g",
            {"route_key": "g:L1"}, ("L1",), cost=57,
        )
        residual_probe(
            ledger, "p", "g", cost=5,
            cancellation={"route_dominated:g:L1"},
        )
        event = run_to_fixed_point(ledger, event_id="e")
        self.assertGreaterEqual(event.closure_iterations, 2)
        self.assertTrue(event.routes_compiled)
        self.assertEqual(ledger.probes["p"].status, CANCELLED)
        self.assertTrue(any(
            item.kind == "compiled_route" and item.state == ACTIVE
            for item in ledger.capabilities.values()
        ))

    def test_revocation_separator_splits_promoted_candidate(self):
        ledger = FlashLedger()
        cap(
            ledger, "candidate", "state_equivalence_certificate", "g",
            {"pair": ["a", "b"]}, ("EQUIV",),
        )
        cap(
            ledger, "sep", "separator", "g",
            {"revokes_capability_id": "candidate"}, ("SEPARATES",),
        )
        event = run_to_fixed_point(ledger, event_id="sep-event")
        self.assertEqual(ledger.capabilities["candidate"].state, REVOKED)
        self.assertIn("candidate", event.quotients_split)

    def test_negative_propagation_is_same_game_only(self):
        ledger = FlashLedger()
        cap(
            ledger, "fatal", "fatal_basin", "g1",
            {"game": "g1", "family": "f"}, ("FATAL",),
        )
        residual_probe(
            ledger, "local", "g1", cost=6,
            cancellation={"fatal_family:g1:f"},
        )
        residual_probe(
            ledger, "other", "g2", cost=6,
            cancellation={"fatal_family:g1:f"},
        )
        run_to_fixed_point(ledger, event_id="fatal-event")
        self.assertEqual(ledger.probes["local"].status, CANCELLED)
        self.assertEqual(ledger.probes["other"].status, PENDING)

    def test_global_obstruction_cancels_only_proposal_law_tests(self):
        ledger = FlashLedger()
        cap(
            ledger, "obs", "obstruction", "g1",
            {"global_law": "law"}, ("COUNTEREXAMPLE",),
        )
        residual_probe(
            ledger, "law-test", "g2", cost=3,
            cancellation={"global_obstruction:law"},
            purpose="test_global_proposal_law",
        )
        residual_probe(
            ledger, "behavior", "g2", cost=3,
            cancellation={"global_obstruction:law"},
            purpose="domain_residual",
        )
        run_to_fixed_point(ledger, event_id="obs-event")
        self.assertEqual(ledger.probes["law-test"].status, CANCELLED)
        self.assertEqual(ledger.probes["behavior"].status, PENDING)

    def test_transfer_source_alone_has_no_destination_authority(self):
        ledger = FlashLedger()
        cap(
            ledger, "candidate", "transferable_capability_candidate", "g1",
            {"transfer_key": "k"}, ("MAYBE",),
        )
        residual_probe(
            ledger, "dest", "g2", cost=4,
            cancellation={"transfer_verified:g2:k"},
        )
        run_to_fixed_point(ledger, event_id="source-only")
        self.assertEqual(ledger.probes["dest"].status, PENDING)

        ref = EvidenceRef("g2", "destination_validation", "run2", "k")
        ledger.add_evidence(ref)
        ledger.add_capability(GlobalCapability(
            capability_id="verified",
            kind="destination_verified_transfer",
            source_games={"g1", "g2"},
            scope={"destination_game": "g2", "transfer_key": "k"},
            consequence_signature=("VERIFIED",),
            exact_witnesses=[ref],
            protected_effect=None,
            acquisition_cost=1,
            authority="destination-exact",
            dependencies={"candidate"},
        ))
        run_to_fixed_point(ledger, event_id="dest-verified")
        self.assertEqual(ledger.probes["dest"].status, CANCELLED)

    def test_sham_irrelevant_obstruction_does_not_cancel(self):
        ledger = FlashLedger()
        cap(
            ledger, "sham", "obstruction", "g1",
            {"global_law": "irrelevant"}, ("COUNTEREXAMPLE",),
        )
        residual_probe(
            ledger, "p", "g2", cost=2,
            cancellation={"global_obstruction:real"},
            purpose="test_global_proposal_law",
        )
        run_to_fixed_point(ledger, event_id="sham")
        self.assertEqual(ledger.probes["p"].status, PENDING)

    def test_order_robust_for_independent_obstructions(self):
        def run(order):
            ledger = FlashLedger()
            residual_probe(
                ledger, "pa", "g2", cost=1,
                cancellation={"global_obstruction:a"},
                purpose="test_global_proposal_law",
            )
            residual_probe(
                ledger, "pb", "g2", cost=1,
                cancellation={"global_obstruction:b"},
                purpose="test_global_proposal_law",
            )
            for law in order:
                cap(
                    ledger, law, "obstruction", "g1",
                    {"global_law": law}, ("COUNTEREXAMPLE", law),
                )
                run_to_fixed_point(ledger, event_id="e:" + law)
            return {
                pid: (p.status, p.acquisition_actions_avoided)
                for pid, p in ledger.probes.items()
            }
        self.assertEqual(run(("a", "b")), run(("b", "a")))

    def test_scheduler_is_deterministic_and_low_overlap(self):
        ledger = FlashLedger()
        for i in range(3):
            rid = f"r{i}"
            ledger.add_residual(
                Residual(rid, f"g{i}", "x", i + 1, {f"k{i}"})
            )
            ledger.add_probe(Probe(
                probe_id=f"p{i}",
                game=f"g{i}",
                exact_context=None,
                intervention=("x",),
                residuals_addressed={rid},
                proposal_score=0.0,
                expected_cost=1,
            ))
        first = choose_wave(ledger, capacity=2)
        self.assertEqual(first, choose_wave(ledger, capacity=2))
        self.assertEqual(len(first), 2)


if __name__ == "__main__":
    unittest.main()
