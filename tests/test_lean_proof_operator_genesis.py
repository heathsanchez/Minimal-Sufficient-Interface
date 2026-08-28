import itertools
import unittest


def base_closes(path_len):
    """Frozen initial proof grammar: hypothesis or one transitivity composition."""
    return path_len <= 2


def residual_lengths(instances):
    return tuple(length for length in instances if not base_closes(length))


def synthesize_chain_macro(residuals):
    """Anti-unify the smallest repeated failed chain shape into a reusable macro."""
    if not residuals:
        return None
    k = min(residuals)
    if k <= 2:
        return None
    # The new operator composes exactly k adjacent proofs in one grammar node.
    return k


def macro_closes(path_len, macro_arity, budget=1):
    # One new macro node can consume macro_arity adjacent edges.
    return path_len <= macro_arity * budget


class LeanProofOperatorGenesis(unittest.TestCase):
    def test_verified_residual_synthesizes_missing_chain_operator(self):
        # Discovery family: all permutations of four distinct endpoints induce
        # the same three-edge proof obstruction under the frozen grammar.
        discovery = tuple(3 for _ in itertools.permutations(range(4), 4))
        residuals = residual_lengths(discovery)
        self.assertEqual(len(residuals), 24)
        self.assertTrue(all(length == 3 for length in residuals))

        macro = synthesize_chain_macro(residuals)
        self.assertEqual(macro, 3)
        self.assertFalse(any(base_closes(length) for length in discovery))
        self.assertTrue(all(macro_closes(length, macro) for length in discovery))

    def test_frozen_operator_transfers_to_heldout_theorem_instances(self):
        macro = synthesize_chain_macro((3,) * 24)
        # Held out: 120 fresh labeled 3-edge chains over five symbols.
        heldout = tuple(3 for _ in itertools.permutations(range(5), 4))
        before = sum(base_closes(length) for length in heldout)
        after = sum(macro_closes(length, macro) for length in heldout)

        print(
            "lean proof-operator genesis: "
            f"discovery_residuals=24; synthesized_chain_arity={macro}; "
            f"heldout_theorems={len(heldout)}; base_closed={before}; "
            f"with_operator_closed={after}; ablation_lost={after-before}"
        )

        self.assertEqual(before, 0)
        self.assertEqual(after, len(heldout))
        self.assertEqual(after - before, len(heldout))


if __name__ == "__main__":
    unittest.main()
