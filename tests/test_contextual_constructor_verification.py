import itertools
import unittest

from test_constructor_genesis import closure, generate_terms, term_map, true_map


def behavioural_signatures(algebra, obs, n):
    """All-reachable-futures observation signature of each state."""
    return tuple(tuple(obs[h[x]] for h in algebra) for x in range(n))


def first_observational_counterexample(term, algebra, obs, n, contextual):
    sig = behavioural_signatures(algebra, obs, n) if contextual else None
    for f in algebra:
        for g in algebra:
            target = true_map(f, g)
            candidate = term_map(term, f, g, n)
            for x in range(n):
                if contextual:
                    got = sig[candidate[x]]
                    want = sig[target[x]]
                else:
                    got = obs[candidate[x]]
                    want = obs[target[x]]
                if got != want:
                    return f, g, x, want
    return None


def learn_from_observation(algebra, obs, n, contextual):
    candidates = list(generate_terms(3))
    counterexamples = []
    while True:
        bad = None
        for term in candidates:
            w = first_observational_counterexample(term, algebra, obs, n, contextual)
            if w is not None:
                bad = w
                break
        if bad is None:
            return candidates, counterexamples
        f, g, x, expected = bad
        counterexamples.append(bad)
        sig = behavioural_signatures(algebra, obs, n) if contextual else None
        kept = []
        for term in candidates:
            y = term_map(term, f, g, n)[x]
            got = sig[y] if contextual else obs[y]
            if got == expected:
                kept.append(term)
        candidates = kept
        if not candidates:
            raise AssertionError("sound observational verifier eliminated whole grammar")


class ContextualConstructorVerification(unittest.TestCase):
    def test_one_step_observation_can_leave_future_harmful_constructor_ambiguity(self):
        """A local protected observation can miss a constructor error exposed later."""
        n = 3
        maps = tuple(itertools.product(range(n), repeat=n))
        observations = [o for o in itertools.product((0, 1), repeat=n) if len(set(o)) > 1]
        witness = None

        for obs in observations:
            for a in maps:
                for b in maps:
                    algebra = closure((a, b), n)
                    local_survivors, _ = learn_from_observation(algebra, obs, n, contextual=False)
                    harmful = [
                        t for t in local_survivors
                        if first_observational_counterexample(t, algebra, obs, n, contextual=True) is not None
                    ]
                    if harmful:
                        witness = (obs, a, b, harmful[0])
                        break
                if witness:
                    break
            if witness:
                break

        self.assertIsNotNone(witness)
        obs, a, b, bad_term = witness
        algebra = closure((a, b), n)
        self.assertIsNone(
            first_observational_counterexample(bad_term, algebra, obs, n, contextual=False)
        )
        self.assertIsNotNone(
            first_observational_counterexample(bad_term, algebra, obs, n, contextual=True)
        )
        print(
            "local-observation falsifier: "
            f"obs={obs}; a={a}; b={b}; bad_term={bad_term}"
        )

    def test_all_futures_observational_feedback_recovers_safe_constructor_class(self):
        """Replace the raw-state oracle with the MSI all-futures observation boundary.

        Exhaust all nonconstant binary observations and all ordered pairs of
        deterministic maps on three states. Any ambiguity remaining after CEGIS
        must be behaviourally invisible under every reachable continuation.
        """
        n = 3
        maps = tuple(itertools.product(range(n), repeat=n))
        observations = [o for o in itertools.product((0, 1), repeat=n) if len(set(o)) > 1]
        total = 0
        harmful = 0
        raw_distinct_safe = 0
        max_cexs = 0

        for obs in observations:
            for a in maps:
                for b in maps:
                    total += 1
                    algebra = closure((a, b), n)
                    survivors, cexs = learn_from_observation(algebra, obs, n, contextual=True)
                    max_cexs = max(max_cexs, len(cexs))
                    for term in survivors:
                        if first_observational_counterexample(
                            term, algebra, obs, n, contextual=True
                        ) is not None:
                            harmful += 1
                        else:
                            # Count safe ambiguity that would have been rejected by
                            # an unnecessarily strong raw-state equality oracle.
                            if any(
                                term_map(term, f, g, n) != true_map(f, g)
                                for f in algebra for g in algebra
                            ):
                                raw_distinct_safe += 1

        print(
            "contextual constructor verifier census: "
            f"total_worlds={total}; harmful_survivors={harmful}; "
            f"raw_distinct_but_behaviourally_safe={raw_distinct_safe}; "
            f"max_counterexamples={max_cexs}"
        )
        self.assertEqual(total, 6 * 27 * 27)
        self.assertEqual(harmful, 0)
        self.assertGreater(raw_distinct_safe, 0)


if __name__ == "__main__":
    unittest.main()
