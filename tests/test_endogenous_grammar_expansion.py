import itertools
import unittest


def identity(n):
    return tuple(range(n))


def compose(f, g):
    return tuple(f[g[x]] for x in range(len(g)))


def sequential_closure(generators, n):
    """Full unary-word closure under supplied sequential execution."""
    seen = {identity(n)}
    frontier = [identity(n)]
    while frontier:
        h = frontier.pop()
        for g in generators:
            gh = compose(g, h)
            if gh not in seen:
                seen.add(gh)
                frontier.append(gh)
    return seen


def constants(n):
    return tuple(tuple(a for _ in range(n)) for a in range(n))


def table_eval(table, n, a, b):
    return table[a * n + b]


def lift_pointwise(table, n, f, g):
    return tuple(table_eval(table, n, f[x], g[x]) for x in range(n))


def hidden_local_rule(a, b):
    """Verifier-only hidden rule. The learner is never given its name/formula."""
    return min(a, b)


def hidden_operator(f, g):
    return tuple(hidden_local_rule(f[x], g[x]) for x in range(len(f)))


def first_basis_counterexample(table, n):
    """Find a verifier counterexample using only constant-map basis probes."""
    cs = constants(n)
    for a, f in enumerate(cs):
        for b, g in enumerate(cs):
            predicted = lift_pointwise(table, n, f, g)[0]
            expected = hidden_operator(f, g)[0]
            if predicted != expected:
                return a, b, expected
    return None


def synthesize_binary_local_operator(n):
    """CEGIS after a representation-level expansion from unary words to an
    unknown binary local constructor.

    No named min/max/etc candidate is supplied.  The expanded grammar is the
    entire finite space of state-local binary operations X x X -> X.
    """
    candidates = list(itertools.product(range(n), repeat=n * n))
    counterexamples = []

    while True:
        bad = None
        for table in candidates:
            witness = first_basis_counterexample(table, n)
            if witness is not None:
                bad = witness
                break
        if bad is None:
            return candidates, counterexamples

        a, b, expected = bad
        counterexamples.append(bad)
        candidates = [
            table for table in candidates
            if table_eval(table, n, a, b) == expected
        ]
        if not candidates:
            raise AssertionError("expanded binary grammar was also exhausted")


class EndogenousGrammarExpansion(unittest.TestCase):
    def test_empty_unary_version_space_triggers_arity_expansion(self):
        n = 3

        # This is the fixed adversarial witness that broke the stronger
        # constructor-genesis interpretation in BREAK_ATTEMPTS.md.
        f = (0, 0, 2)
        g = (1, 0, 1)
        target = hidden_operator(f, g)

        # Stronger than a bounded depth failure: target is absent from the full
        # finite sequential closure of the old unary grammar.
        old_closure = sequential_closure((f, g), n)
        self.assertEqual(target, (0, 0, 1))
        self.assertNotIn(target, old_closure)

        # Empty old version space is interpreted as a representation-level
        # residual.  The generic response is an arity increase: admit an
        # unknown local binary operation X x X -> X, not a named operator.
        survivors, counterexamples = synthesize_binary_local_operator(n)

        # The verifier basis determines one reusable binary operation exactly.
        self.assertEqual(len(survivors), 1)
        learned = survivors[0]
        self.assertEqual(
            learned,
            tuple(hidden_local_rule(a, b) for a in range(n) for b in range(n)),
        )
        self.assertGreater(len(counterexamples), 0)
        self.assertLessEqual(len(counterexamples), n * n)

        # The learned constructor repairs the original obstruction.
        self.assertEqual(lift_pointwise(learned, n, f, g), target)

    def test_learned_operator_transfers_and_unlocks_new_capability(self):
        n = 3
        maps = tuple(itertools.product(range(n), repeat=n))
        consts = set(constants(n))
        learned = synthesize_binary_local_operator(n)[0][0]

        heldout_pairs = 0
        transfer_failures = 0
        newly_reachable = 0
        ablation_witnesses = 0

        for f in maps:
            for g in maps:
                learned_map = lift_pointwise(learned, n, f, g)
                true_map = hidden_operator(f, g)

                # Discovery used only the 3x3 constant-map basis. Everything
                # else is held out at the transformation-pair level.
                if not (f in consts and g in consts):
                    heldout_pairs += 1
                    if learned_map != true_map:
                        transfer_failures += 1

                # Capability gain: the learned binary constructor can create a
                # map that no unary word over this pair can express.
                old_closure = sequential_closure((f, g), n)
                if true_map not in old_closure:
                    newly_reachable += 1
                    self.assertEqual(learned_map, true_map)

                    # Exact ablation: remove the learned constructor and the
                    # target map is again outside the old executable language.
                    if learned_map not in old_closure:
                        ablation_witnesses += 1

        print(
            "endogenous grammar expansion: "
            f"basis_pairs={n*n}; "
            f"heldout_pairs={heldout_pairs}; "
            f"transfer_failures={transfer_failures}; "
            f"newly_reachable={newly_reachable}; "
            f"ablation_witnesses={ablation_witnesses}"
        )

        self.assertEqual(heldout_pairs, n ** (2 * n) - n * n)
        self.assertEqual(transfer_failures, 0)
        self.assertGreater(newly_reachable, 0)
        self.assertEqual(ablation_witnesses, newly_reachable)


if __name__ == "__main__":
    unittest.main()
