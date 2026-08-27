import unittest

from test_constructor_genesis import generate_terms, eval_term, term_map


def pointwise_min(f, g):
    """A hidden binary constructor not expressible by the unary word grammar in general."""
    return tuple(min(f[x], g[x]) for x in range(len(f)))


def cegis_against_hidden_constructor(f, g, target_map, n=3, max_depth=3):
    """Run the same counterexample-elimination logic against an arbitrary hidden law."""
    candidates = list(generate_terms(max_depth))
    counterexamples = []
    for x in range(n):
        expected = target_map[x]
        bad = [t for t in candidates if eval_term(t, f, g, x) != expected]
        if bad:
            counterexamples.append((x, expected))
            candidates = [t for t in candidates if eval_term(t, f, g, x) == expected]
        if not candidates:
            break
    return candidates, counterexamples


class AdversarialBreakAttempts(unittest.TestCase):
    def test_constructor_genesis_breaks_when_true_law_is_outside_grammar(self):
        # Fixed smallest witness found by exhaustive search over three-state maps.
        # The hidden constructor is pointwise min rather than sequential composition.
        f = (0, 0, 2)
        g = (1, 0, 1)
        target = pointwise_min(f, g)
        self.assertEqual(target, (0, 0, 1))

        terms = generate_terms(3)
        # None of the 15 grammar programs x | F(t) | G(t) realizes this law here.
        self.assertTrue(all(term_map(t, f, g, 3) != target for t in terms))

        survivors, counterexamples = cegis_against_hidden_constructor(f, g, target)
        self.assertEqual(survivors, [])
        self.assertGreater(len(counterexamples), 0)

    def test_more_depth_does_not_fix_this_expressivity_failure(self):
        # This is not merely the chosen depth-3 cutoff.  For this f,g pair, every
        # nonempty word immediately maps state 0 to either 0 or 1 and then falls
        # into the same small orbit; the desired total map (0,0,1) is unreachable
        # by any unary action word.  Check a much deeper finite prefix as a guard.
        f = (0, 0, 2)
        g = (1, 0, 1)
        target = pointwise_min(f, g)
        terms = generate_terms(12)
        self.assertTrue(all(term_map(t, f, g, 3) != target for t in terms))


if __name__ == "__main__":
    unittest.main()
