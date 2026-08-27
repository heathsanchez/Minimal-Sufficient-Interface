import unittest

from test_constructor_genesis import closure
from test_fortification import eval_table, min_table, pointwise_min


class DiagnosticAmbiguity(unittest.TestCase):
    def test_richer_language_can_fit_a_corrupted_verifier_perfectly(self):
        """Language expansion alone cannot distinguish expressivity failure from bad evidence."""
        n = 3
        f0 = (0, 0, 2)
        g0 = (1, 0, 1)
        algebra = closure((f0, g0), n)

        # Build the clean pointwise constraints for the hidden min law.
        clean = {}
        for f in algebra:
            for g in algebra:
                target = pointwise_min(f, g)
                for x in range(n):
                    key = (f[x], g[x])
                    value = target[x]
                    if key in clean:
                        self.assertEqual(clean[key], value)
                    clean[key] = value

        true = min_table(n)
        self.assertTrue(all(eval_table(true, a, b, n) == y for (a, b), y in clean.items()))

        # Corrupt exactly one verifier value without making the evidence internally
        # contradictory. A fully expressive pointwise table can absorb the error.
        key = sorted(clean)[-1]
        noisy = dict(clean)
        noisy[key] = (noisy[key] + 1) % n
        self.assertNotEqual(noisy[key], clean[key])

        learned = list(true)
        learned[key[0] * n + key[1]] = noisy[key]
        learned = tuple(learned)

        self.assertTrue(all(eval_table(learned, a, b, n) == y for (a, b), y in noisy.items()))
        self.assertNotEqual(learned, true)
        self.assertNotEqual(eval_table(learned, *key, n), eval_table(true, *key, n))

    def test_empty_or_bad_version_space_has_three_distinct_possible_causes(self):
        """The residual signal alone does not identify its own cause.

        The same meta-level symptom can mean:
          1. the hypothesis language cannot express the world;
          2. verifier evidence is wrong;
          3. previously valid evidence became stale because protected authority/world changed.

        This test records the logical diagnostic boundary rather than pretending
        one internal signal uniquely selects grammar expansion.
        """
        causes = {"language_inadequate", "verifier_unsound", "target_drift"}
        self.assertEqual(len(causes), 3)
        # No observation of merely "no consistent current hypothesis" contains a
        # tag telling the learner which member of `causes` generated it.
        symptom = "no_consistent_hypothesis"
        explanations = {cause: symptom for cause in causes}
        self.assertEqual(set(explanations.values()), {symptom})


if __name__ == "__main__":
    unittest.main()
