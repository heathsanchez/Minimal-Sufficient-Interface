import itertools
import unittest


def compose(f, g):
    """True sequential composition f ∘ g, used only by the verifier."""
    return tuple(f[g[x]] for x in range(len(g)))


def identity(n):
    return tuple(range(n))


def closure(generators, n):
    seen = {identity(n)}
    frontier = [identity(n)]
    while frontier:
        h = frontier.pop()
        for g in generators:
            gh = compose(g, h)
            if gh not in seen:
                seen.add(gh)
                frontier.append(gh)
    return tuple(sorted(seen))


def generate_terms(max_depth=3):
    """Generate constructor programs from a tiny syntax, not a law list.

    Grammar:
        t ::= x | F(t) | G(t)

    A term denotes a candidate binary operation on transformations F and G.
    The target constructor F(G(x)) is therefore generated, not named.
    """
    by_depth = {0: {()}}
    all_terms = {()}
    for depth in range(1, max_depth + 1):
        layer = set()
        for t in by_depth[depth - 1]:
            layer.add((0,) + t)  # F(t)
            layer.add((1,) + t)  # G(t)
        by_depth[depth] = layer
        all_terms |= layer
    return tuple(sorted(all_terms, key=lambda t: (len(t), t)))


def eval_term(term, f, g, x):
    y = x
    # The term tuple stores outermost operator first.  Evaluation therefore
    # applies symbols from the inside out.
    for symbol in reversed(term):
        y = (f if symbol == 0 else g)[y]
    return y


def term_map(term, f, g, n):
    return tuple(eval_term(term, f, g, x) for x in range(n))


def true_map(f, g):
    return compose(f, g)


def first_counterexample(term, algebra, n):
    """Return the first reachable (f,g,x) falsifying a constructor program."""
    for f in algebra:
        for g in algebra:
            target = true_map(f, g)
            candidate = term_map(term, f, g, n)
            for x in range(n):
                if candidate[x] != target[x]:
                    return f, g, x, target[x]
    return None


def learn_constructor(algebra, n, max_depth=3):
    """Counterexample-guided synthesis from the generated term grammar."""
    candidates = list(generate_terms(max_depth))
    counterexamples = []

    while True:
        bad = None
        for term in candidates:
            witness = first_counterexample(term, algebra, n)
            if witness is not None:
                bad = witness
                break
        if bad is None:
            return candidates, counterexamples

        f, g, x, expected = bad
        counterexamples.append(bad)
        candidates = [
            term for term in candidates
            if eval_term(term, f, g, x) == expected
        ]
        if not candidates:
            raise AssertionError("verifier eliminated the entire generated grammar")


def op_equal_on_algebra(term, algebra, n):
    return first_counterexample(term, algebra, n) is None


def identity_holds(term, algebra, n):
    e = identity(n)
    for f in algebra:
        if term_map(term, f, e, n) != f:
            return False
        if term_map(term, e, f, n) != f:
            return False
    return True


def assoc_holds(term, algebra, n):
    def op(f, g):
        return term_map(term, f, g, n)

    aset = set(algebra)
    for f in algebra:
        for g in algebra:
            fg = op(f, g)
            if fg not in aset:
                return False
            for h in algebra:
                if op(op(f, g), h) != op(f, op(g, h)):
                    return False
    return True


class ConstructorGenesis(unittest.TestCase):
    def test_grammar_contains_target_without_naming_it(self):
        terms = generate_terms(3)
        # F(G(x)) is the generated term (0,1), not a hand-listed candidate law.
        self.assertIn((0, 1), terms)
        self.assertEqual(len(terms), 15)

    def test_exhaustive_three_state_constructor_genesis(self):
        n = 3
        maps = tuple(itertools.product(range(n), repeat=n))
        total = 0
        unique_syntax = 0
        operational_ambiguity = 0
        harmful_ambiguity = 0
        total_counterexamples = 0
        max_counterexamples = 0
        identity_failures = 0
        assoc_failures = 0
        chosen_histogram = {}

        for a in maps:
            for b in maps:
                total += 1
                algebra = closure((a, b), n)
                survivors, cexs = learn_constructor(algebra, n, 3)
                total_counterexamples += len(cexs)
                max_counterexamples = max(max_counterexamples, len(cexs))

                good = [t for t in survivors if op_equal_on_algebra(t, algebra, n)]
                if len(good) != len(survivors):
                    harmful_ambiguity += 1
                    continue

                if len(survivors) == 1:
                    unique_syntax += 1
                else:
                    operational_ambiguity += 1

                # Retain the shortest lexicographic survivor.  Even when its
                # syntax differs from F(G(x)), counterexamples have certified
                # it is the same operation on the reachable algebra.
                chosen = min(survivors, key=lambda t: (len(t), t))
                chosen_histogram[chosen] = chosen_histogram.get(chosen, 0) + 1
                if not identity_holds(chosen, algebra, n):
                    identity_failures += 1
                if not assoc_holds(chosen, algebra, n):
                    assoc_failures += 1

        print(
            "constructor genesis census: "
            f"total_worlds={total}; "
            f"unique_syntax={unique_syntax}; "
            f"operational_ambiguity={operational_ambiguity}; "
            f"harmful_ambiguity={harmful_ambiguity}; "
            f"total_counterexamples={total_counterexamples}; "
            f"max_counterexamples={max_counterexamples}; "
            f"identity_failures={identity_failures}; "
            f"assoc_failures={assoc_failures}; "
            f"chosen_histogram={chosen_histogram}"
        )

        self.assertEqual(total, 27 * 27)
        self.assertEqual(harmful_ambiguity, 0)
        self.assertEqual(identity_failures, 0)
        self.assertEqual(assoc_failures, 0)
        self.assertGreater(unique_syntax, 0)
        self.assertGreater(operational_ambiguity, 0)


if __name__ == "__main__":
    unittest.main()
