import itertools
import unittest


def seq(f, g):
    """True sequential constructor: apply g, then f."""
    return tuple(f[g[x]] for x in range(len(g)))


def rev(f, g):
    return tuple(g[f[x]] for x in range(len(g)))


def left(f, g):
    return f


def right(f, g):
    return g


def pointwise_min(f, g):
    return tuple(min(f[x], g[x]) for x in range(len(g)))


def pointwise_max(f, g):
    return tuple(max(f[x], g[x]) for x in range(len(g)))


CONSTRUCTORS = (
    ("seq", seq),
    ("rev", rev),
    ("left", left),
    ("right", right),
    ("min", pointwise_min),
    ("max", pointwise_max),
)


def identity(n):
    return tuple(range(n))


def closure(generators, constructor, n):
    """Least finite set containing id/generators and closed under constructor."""
    seen = {identity(n), *generators}
    changed = True
    while changed:
        changed = False
        current = tuple(seen)
        for f in current:
            for g in current:
                h = constructor(f, g)
                if h not in seen:
                    seen.add(h)
                    changed = True
    return frozenset(seen)


def relation(maps, obs, n):
    def sig(x):
        return tuple(obs[m[x]] for m in sorted(maps))

    return tuple(tuple(sig(x) == sig(y) for y in range(n)) for x in range(n))


def eliminate_by_counterexamples(true_maps, survivors, n):
    """Eliminate constructor hypotheses only when a verifier counterexample exists.

    A counterexample is (f,g,x,y) where f and g are reachable under the hidden
    true dynamics, x is a state, and y is the actually observed result of doing
    g then f.  The learner is never given a composition table or closure law.
    """
    survivors = list(survivors)
    counterexamples = []
    ordered_maps = sorted(true_maps)

    while True:
        witness = None
        for f in ordered_maps:
            for g in ordered_maps:
                truth = seq(f, g)
                for x in range(n):
                    y = truth[x]
                    if any(constructor(f, g)[x] != y for _, constructor in survivors):
                        witness = (f, g, x, y)
                        break
                if witness is not None:
                    break
            if witness is not None:
                break

        if witness is None:
            return survivors, counterexamples

        f, g, x, y = witness
        survivors = [
            (name, constructor)
            for name, constructor in survivors
            if constructor(f, g)[x] == y
        ]
        counterexamples.append(witness)
        if not survivors:
            raise AssertionError("verifier eliminated the true constructor")


class ConstructorLawDiscovery(unittest.TestCase):
    def test_exhaustive_three_state_constructor_version_space(self):
        n = 3
        total_worlds = 0
        uniquely_identified = 0
        ambiguous_but_operationally_equivalent = 0
        harmful_ambiguity = 0
        max_counterexamples = 0
        total_counterexamples = 0
        survivor_histogram = {}
        examples = []

        for obs in itertools.product(range(2), repeat=n):
            for g0 in itertools.product(range(n), repeat=n):
                for g1 in itertools.product(range(n), repeat=n):
                    total_worlds += 1
                    generators = (g0, g1)
                    true_maps = closure(generators, seq, n)
                    target_rel = relation(true_maps, obs, n)

                    survivors, counterexamples = eliminate_by_counterexamples(
                        true_maps, CONSTRUCTORS, n
                    )
                    names = tuple(name for name, _ in survivors)
                    survivor_histogram[names] = survivor_histogram.get(names, 0) + 1
                    max_counterexamples = max(max_counterexamples, len(counterexamples))
                    total_counterexamples += len(counterexamples)

                    if names == ("seq",):
                        uniquely_identified += 1
                    else:
                        operationally_ok = True
                        for _, constructor in survivors:
                            learned_maps = closure(generators, constructor, n)
                            if learned_maps != true_maps:
                                operationally_ok = False
                                break
                            if relation(learned_maps, obs, n) != target_rel:
                                operationally_ok = False
                                break
                        if operationally_ok:
                            ambiguous_but_operationally_equivalent += 1
                        else:
                            harmful_ambiguity += 1
                            if len(examples) < 5:
                                examples.append((obs, g0, g1, names, counterexamples))

        print(
            "constructor law discovery census: "
            f"total_worlds={total_worlds}; "
            f"uniquely_identified={uniquely_identified}; "
            f"ambiguous_but_operationally_equivalent={ambiguous_but_operationally_equivalent}; "
            f"harmful_ambiguity={harmful_ambiguity}; "
            f"total_counterexamples={total_counterexamples}; "
            f"max_counterexamples={max_counterexamples}; "
            f"survivor_histogram={survivor_histogram}; "
            f"harmful_examples={examples}"
        )

        self.assertEqual(total_worlds, 8 * 27 * 27)
        self.assertEqual(harmful_ambiguity, 0)
        self.assertEqual(
            uniquely_identified + ambiguous_but_operationally_equivalent,
            total_worlds,
        )
        self.assertGreater(total_counterexamples, 0)

    def test_counterexamples_select_sequential_composition_in_a_noncommuting_world(self):
        n = 3
        obs = (0, 0, 1)
        g0 = (0, 2, 1)
        g1 = (1, 0, 2)
        true_maps = closure((g0, g1), seq, n)
        survivors, counterexamples = eliminate_by_counterexamples(true_maps, CONSTRUCTORS, n)
        self.assertTrue(counterexamples)
        # Whatever syntax survives must be extensionally identical to sequential
        # composition on the whole reachable subalgebra.
        for _, constructor in survivors:
            for f in true_maps:
                for g in true_maps:
                    self.assertEqual(constructor(f, g), seq(f, g))


if __name__ == "__main__":
    unittest.main()
