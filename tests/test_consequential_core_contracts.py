import unittest

from consequential_certification import (
    certify_language_extension,
    certify_policy_update,
    certify_representation_repair,
)
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
    compile_repair,
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

        certified = certify_representation_repair(
            state,
            residual,
            repair,
            experiment_pair=(0, 1),
            observed_same=False,
            attachment="separator splits motivating pair",
        )
        after, token = compile_repair(state, certified)
        self.assertEqual(after.active_representation, new)
        self.assertEqual(ablate(after, token), state)

        # A merge is not conservative development.
        partially_refined = EquivalenceRelation.from_partition(X, ({0}, {1}, {2, 3}))
        merge = EquivalenceRelation.from_partition(X, ({0, 1}, {2, 3}))
        merge_state = DevelopmentState(X, active_representation=partially_refined)
        merge_residual = PairResidual(2, 3, partially_refined, 0, 1)
        with self.assertRaises(ValueError):
            certify_representation_repair(
                merge_state,
                merge_residual,
                RefineRepresentation(merge),
                experiment_pair=(2, 3),
                observed_same=False,
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
        domain_repairs = meta.exact_repairs_with_operator(
            meta.SOURCE_ATOMS, meta.SOURCE_OPS[delta], hidden
        )
        self.assertTrue(domain_repairs)
        realized_col = domain_repairs[0][2]
        realized_kernel = EquivalenceRelation.from_observation(
            X, lambda i: realized_col[i]
        )

        certified = certify_language_extension(
            state,
            residual,
            repair,
            realized_required_kernel=realized_kernel,
            lawful_under_active_representation=True,
            attachment="operator realizes previously absent target kernel",
        )
        after, token = compile_repair(state, certified)
        self.assertIn(delta, after.language)
        self.assertEqual(ablate(after, token), state)

        # The closure residual is tied to the exact old C snapshot.
        with self.assertRaises(ValueError):
            certify_language_extension(
                after,
                residual,
                ExtendLanguage("s_untwist"),
                realized_required_kernel=required,
                lawful_under_active_representation=True,
                attachment="stale residual",
            )

    def test_recursive_compounding_is_explicit_second_order_acquisition(self):
        X = tuple(range(len(recursive.TARGET_LABELS)))
        language = tuple(recursive.TARGET_QUERIES)

        _, source_history = recursive.cold_episode(
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

        state = DevelopmentState(X, language=language, policy=None)
        residual = AcquisitionResidual(
            task="reach exact target interface in one query",
            language_snapshot=language,
            policy_snapshot=None,
            budget=1,
            cold_success=False,
        )
        repair = UpdatePolicy(warm_policy)

        warm_chosen, _ = recursive.policy_episode(
            recursive.TARGET_LABELS,
            recursive.TARGET_QUERIES,
            recursive.TARGET_ORDER,
            budget=residual.budget,
            policy=warm_policy,
        )
        warm_success = recursive.sufficient(
            recursive.TARGET_LABELS, recursive.TARGET_QUERIES, warm_chosen
        )
        self.assertTrue(warm_success)

        certified = certify_policy_update(
            state,
            residual,
            repair,
            warm_success=warm_success,
            attachment="source residual history changes bounded future acquisition",
        )
        after, token = compile_repair(state, certified)
        self.assertEqual(after.language, state.language)
        self.assertEqual(after.policy, warm_policy)
        self.assertEqual(ablate(after, token), state)

        # The second-order repair changes D only.
        self.assertEqual(after.active_representation, state.active_representation)
        self.assertEqual(after.language, state.language)


if __name__ == "__main__":
    unittest.main()
