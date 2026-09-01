import unittest

from consequential_core import (
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

        # A merge is not a repair: it would erase a previously licensed split.
        indiscrete = EquivalenceRelation.from_partition(X, ({0, 1, 2, 3},))
        with self.assertRaises(ValueError):
            certify_repair(
                DevelopmentState(X, active_representation=new),
                PairResidual(0, 1, old, 0, 1),
                RefineRepresentation(indiscrete),
                lambda *_: True,
                attachment="invalid merge",
            )

    def test_meta_becoming_is_literal_language_extension_over_kernel_version_space(self):
        hidden = meta.source_training_tasks()[0]
        X = meta.SOURCE_STATES
        required = EquivalenceRelation.from_observation(X, lambda i: hidden[i])

        base_cols = tuple(meta.base_language(meta.SOURCE_ATOMS).values())
        realized = tuple(
            dict.fromkeys(
                EquivalenceRelation.from_observation(X, lambda i, col=col: col[i])
                for col in base_cols
            )
        )
        self.assertNotIn(required, realized)

        closure = ClosureCertificate(
            interactions=tuple(meta.base_language(meta.SOURCE_ATOMS)),
            complete=True,
            regime="base atoms plus negations",
        )
        residual = ClosureResidual(required, realized, closure)
        state = DevelopmentState(
            X,
            version_space=realized,
            language=tuple(meta.base_language(meta.SOURCE_ATOMS)),
        )

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

        # Duplicate extension is structurally inert and is rejected by the core.
        with self.assertRaises(ValueError):
            certify_repair(
                after,
                residual,
                ExtendLanguage(delta),
                lambda *_: True,
                attachment="duplicate",
            )

    def test_recursive_compounding_is_policy_change_not_language_extension(self):
        X = tuple(range(len(recursive.TARGET_LABELS)))
        empty_rep = EquivalenceRelation.from_observation(X, lambda _i: 0)
        pair = recursive.residual(recursive.TARGET_LABELS, recursive.TARGET_QUERIES, ())
        self.assertIsNotNone(pair)
        left, right = pair
        residual = PairResidual(
            left,
            right,
            empty_rep,
            recursive.TARGET_LABELS[left],
            recursive.TARGET_LABELS[right],
        )

        source_chosen, source_history = recursive.cold_episode(
            recursive.SOURCE_LABELS,
            recursive.SOURCE_QUERIES,
            recursive.SOURCE_ORDER,
            budget=8,
        )
        warm_policy = recursive.compile_policy(
            recursive.SOURCE_QUERIES, recursive.SOURCE_ORDER, source_history
        )

        state = DevelopmentState(
            X,
            active_representation=empty_rep,
            language=tuple(recursive.TARGET_QUERIES),
            policy=None,
        )
        repair = UpdatePolicy(warm_policy)

        def resolves(_state, candidate, _residual):
            chosen, _ = recursive.policy_episode(
                recursive.TARGET_LABELS,
                recursive.TARGET_QUERIES,
                recursive.TARGET_ORDER,
                budget=1,
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
            attachment="source residual history changes next target acquisition",
        )
        after, token = compile_repair(state, certified)
        self.assertEqual(after.language, state.language)
        self.assertEqual(after.policy, warm_policy)
        self.assertEqual(ablate(after, token), state)

        # This establishes the seam explicitly: the successful repair changes D,
        # not E or C. A later theorem may compile D into C, but this test does not
        # assume such a map exists.
        self.assertEqual(after.active_representation, state.active_representation)


if __name__ == "__main__":
    unittest.main()
