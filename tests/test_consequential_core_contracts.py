import unittest

from consequential_core import (
    AcquisitionResidual,
    ClosureCertificate,
    ClosureResidual,
    DevelopmentState,
    EquivalenceRelation,
    ExtendLanguage,
    PairResidual,
    RefineRepresentation,
    UpdatePolicy,
    ablate,
    certify_repair,
    compile_repair,
    residual_resolved_by_representation,
)
from tests import test_golden_law_meta_becoming as meta
from tests import test_recursive_developmental_compounding as recursive


class ConsequentialCoreContracts(unittest.TestCase):
    def test_difference_shape_is_literal_representation_refinement(self):
        X = tuple(range(4))
        old = EquivalenceRelation.from_partition(X, ({0, 1}, {2, 3}))
        residual = PairResidual(0, 1, old, 0, 1)
        new = EquivalenceRelation.from_partition(X, ({0}, {1}, {2}, {3}))
        state = DevelopmentState(X, active_representation=old)
        repair = RefineRepresentation(new)

        certified = certify_repair(
            state,
            residual,
            repair,
            lambda _s, r, rho: residual_resolved_by_representation(rho, r.new_representation),
            attachment="separator splits motivating pair",
        )
        after, token = compile_repair(state, certified)
        self.assertEqual(after.active_representation, new)
        self.assertEqual(ablate(after, token), state)

        indiscrete = EquivalenceRelation.from_partition(X, ({0, 1, 2, 3},))
        with self.assertRaises(ValueError):
            certify_repair(
                DevelopmentState(X, active_representation=new),
                PairResidual(0, 1, old, 0, 1),
                RefineRepresentation(indiscrete),
                lambda *_: True,
                attachment="invalid merge",
            )

    def test_meta_becoming_is_literal_language_extension_over_kernel_closure(self):
        hidden = meta.source_training_tasks()[0]
        X = meta.SOURCE_STATES
        required = EquivalenceRelation.from_observation(X, lambda i: hidden[i])

        base_language = meta.base_language(meta.SOURCE_ATOMS)
        base_cols = tuple(base_language.values())
        realized = tuple(
            dict.fromkeys(
                EquivalenceRelation.from_observation(X, lambda i, col=col: col[i])
                for col in base_cols
            )
        )
        self.assertNotIn(required, realized)

        language_snapshot = tuple(base_language)
        closure = ClosureCertificate(
            interactions=language_snapshot,
            complete=True,
            regime="base atoms plus negations",
            language_snapshot=language_snapshot,
        )
        residual = ClosureResidual(required, realized, closure)
        state = DevelopmentState(X, language=language_snapshot)

        delta = "s_twist"
        repair = ExtendLanguage(delta)
        certified = certify_repair(
            state,
            residual,
            repair,
            lambda _s, _r, _rho: bool(
                meta.exact_repairs_with_operator(
                    meta.SOURCE_ATOMS, meta.SOURCE_OPS[delta], hidden
                )
            ),
            attachment="operator realizes previously absent target kernel",
        )
        after, token = compile_repair(state, certified)
        self.assertIn(delta, after.language)
        self.assertEqual(ablate(after, token), state)

        with self.assertRaises(ValueError):
            certify_repair(
                after,
                residual,
                ExtendLanguage("s_untwist"),
                lambda *_: True,
                attachment="stale residual",
            )

    def test_recursive_compounding_is_explicit_second_order_acquisition(self):
        X = tuple(range(len(recursive.TARGET_LABELS)))
        language = tuple(recursive.TARGET_QUERIES)

        source_chosen, source_history = recursive.cold_episode(
            recursive.SOURCE_LABELS,
            recursive.SOURCE_QUERIES,
            recursive.SOURCE_ORDER,
            budget=8,
        )
        warm_policy = recursive.compile_policy(
            recursive.SOURCE_QUERIES, recursive.SOURCE_ORDER, source_history
        )

        cold_chosen, _ = recursive.policy_episode(
            recursive.TARGET_LABELS,
            recursive.TARGET_QUERIES,
            recursive.TARGET_ORDER,
            budget=1,
            policy={},
        )
        self.assertFalse(
            recursive.sufficient(
                recursive.TARGET_LABELS, recursive.TARGET_QUERIES, cold_chosen
            )
        )

        state = DevelopmentState(
            X,
            language=language,
            policy=None,
        )
        residual = AcquisitionResidual(
            task="reach exact target interface in one query",
            language_snapshot=language,
            policy_snapshot=None,
            budget=1,
            cold_success=False,
        )
        repair = UpdatePolicy(warm_policy)

        def resolves(_state, candidate, rho):
            chosen, _ = recursive.policy_episode(
                recursive.TARGET_LABELS,
                recursive.TARGET_QUERIES,
                recursive.TARGET_ORDER,
                budget=rho.budget,
                policy=candidate.new_policy,
            )
            return recursive.sufficient(
                recursive.TARGET_LABELS, recursive.TARGET_QUERIES, chosen
            )

        certified = certify_repair(
            state,
            residual,
            repair,
            resolves,
            attachment="source residual history changes bounded future acquisition",
        )
        after, token = compile_repair(state, certified)
        self.assertEqual(after.language, state.language)
        self.assertEqual(after.policy, warm_policy)
        self.assertEqual(ablate(after, token), state)

        # The second-order repair changes D only; it does not pretend to have
        # immediately refined E or extended C.
        self.assertEqual(after.active_representation, state.active_representation)
        self.assertEqual(after.language, state.language)


if __name__ == "__main__":
    unittest.main()
