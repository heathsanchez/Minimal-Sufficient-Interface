import itertools
import unittest

from test_constructor_genesis import closure, compose, generate_terms, term_map, true_map


def identity(n):
    return tuple(range(n))


def shortest_context_separator(generators, obs, u, v, n):
    """Breadth-first search for a reachable context separating states u and v.

    Returns (word, map) where word is a tuple of primitive indices. The verifier
    need not precompute an all-futures signature or reveal raw state identity.
    """
    if obs[u] != obs[v]:
        return (), identity(n)

    seen = {identity(n)}
    frontier = [((), identity(n))]
    while frontier:
        word, h = frontier.pop(0)
        for i, g in enumerate(generators):
            gh = compose(g, h)
            if gh in seen:
                continue
            seen.add(gh)
            w = word + (i,)
            if obs[gh[u]] != obs[gh[v]]:
                return w, gh
            frontier.append((w, gh))
    return None


def contextual_equivalent_by_search(generators, obs, u, v, n):
    return shortest_context_separator(generators, obs, u, v, n) is None


def learn_constructor_adaptively(algebra, generators, obs, n):
    """CEGIS where each constructor error is exposed by an adaptively found context."""
    candidates = list(generate_terms(3))
    counterexamples = []

    while True:
        witness = None
        for term in candidates:
            for f in algebra:
                for g in algebra:
                    target = true_map(f, g)
                    candidate = term_map(term, f, g, n)
                    for x in range(n):
                        sep = shortest_context_separator(
                            generators, obs, candidate[x], target[x], n
                        )
                        if sep is not None:
                            word, ctx = sep
                            witness = (f, g, x, word, ctx, target[x])
                            break
                    if witness:
                        break
                if witness:
                    break
            if witness:
                break

        if witness is None:
            return candidates, counterexamples

        f, g, x, word, ctx, target_state = witness
        expected = obs[ctx[target_state]]
        counterexamples.append((f, g, x, word, expected))
        candidates = [
            term for term in candidates
            if obs[ctx[term_map(term, f, g, n)[x]]] == expected
        ]
        if not candidates:
            raise AssertionError("sound contextual verifier eliminated whole grammar")


class AdaptiveContextualVerifier(unittest.TestCase):
    def test_adaptive_search_matches_full_behavioural_equivalence(self):
        n = 3
        maps = tuple(itertools.product(range(n), repeat=n))
        observations = [o for o in itertools.product((0, 1), repeat=n) if len(set(o)) > 1]
        checked = 0
        max_separator_depth = 0

        for obs in observations:
            for a in maps:
                for b in maps:
                    algebra = closure((a, b), n)
                    for u in range(n):
                        for v in range(n):
                            # Full behavioural relation, used only as the judge.
                            full = all(obs[h[u]] == obs[h[v]] for h in algebra)
                            sep = shortest_context_separator((a, b), obs, u, v, n)
                            self.assertEqual(full, sep is None)
                            if sep is not None:
                                max_separator_depth = max(max_separator_depth, len(sep[0]))
                            checked += 1

        print(
            "adaptive context-search census: "
            f"state_pairs_checked={checked}; max_shortest_separator_depth={max_separator_depth}"
        )
        self.assertEqual(checked, 6 * 27 * 27 * 3 * 3)

    def test_adaptive_context_cegis_has_no_harmful_survivors(self):
        n = 3
        maps = tuple(itertools.product(range(n), repeat=n))
        observations = [o for o in itertools.product((0, 1), repeat=n) if len(set(o)) > 1]
        total = 0
        harmful = 0
        max_cexs = 0
        deepest_counterexample_context = 0

        for obs in observations:
            for a in maps:
                for b in maps:
                    total += 1
                    algebra = closure((a, b), n)
                    survivors, cexs = learn_constructor_adaptively(
                        algebra, (a, b), obs, n
                    )
                    max_cexs = max(max_cexs, len(cexs))
                    if cexs:
                        deepest_counterexample_context = max(
                            deepest_counterexample_context,
                            max(len(cex[3]) for cex in cexs),
                        )

                    for term in survivors:
                        for f in algebra:
                            for g in algebra:
                                target = true_map(f, g)
                                candidate = term_map(term, f, g, n)
                                for x in range(n):
                                    if not contextual_equivalent_by_search(
                                        (a, b), obs, candidate[x], target[x], n
                                    ):
                                        harmful += 1
                                        break
                                if harmful:
                                    break
                            if harmful:
                                break
                        if harmful:
                            break

        print(
            "adaptive contextual constructor CEGIS: "
            f"total_worlds={total}; harmful_survivors={harmful}; "
            f"max_counterexamples={max_cexs}; "
            f"deepest_counterexample_context={deepest_counterexample_context}"
        )
        self.assertEqual(total, 6 * 27 * 27)
        self.assertEqual(harmful, 0)
        self.assertGreater(deepest_counterexample_context, 0)


if __name__ == "__main__":
    unittest.main()
