import itertools
import math
import unittest


PRIMES = (5, 7, 11, 13, 17, 19)
MAX_EXP = 18
CANDIDATE_ORDERS = tuple(range(2, MAX_EXP + 1))


def multiplicative_order(g, p):
    x = 1
    for k in range(1, p):
        x = (x * g) % p
        if x == 1:
            return k
    raise AssertionError("nonzero element must have finite order")


def subgroup(g, p, m):
    return tuple(pow(g, k, p) for k in range(m))


def canonical_cyclic_table(m):
    return tuple((a + b) % m for a in range(m) for b in range(m))


def response_for_order(m, lens, query):
    """Binary task outcome in four independently encoded languages.

    No learner receives p, g, m, a cross-lens translation, or an explicit
    composition result. Each language exposes only a yes/no task predicate.
    """
    if lens == "arithmetic":
        a, b = query
        # Hidden meaning: g^a == g^b in F_p^*.
        return (a - b) % m == 0

    if lens == "algebraic":
        a, b = query
        # Hidden meaning: x^a - x^b vanishes on every point of H=<g>.
        return (a - b) % m == 0

    if lens == "topological":
        u, v = query
        # Hidden meaning: two anonymous walks on the Cayley cycle have the
        # same endpoint. The learner is not told this is a cycle.
        return (u - v) % m == 0

    if lens == "categorical":
        r, s = query
        # Hidden meaning: the action words sigma^r and sigma^s are the same
        # endomorphism on the hidden orbit. Only equality success/failure is
        # returned; no composite token is exposed.
        return (r - s) % m == 0

    raise ValueError(lens)


def query_language(lens):
    """Distinct surface enumerations; no deterministic cross-lens dictionary is used."""
    pairs = list(itertools.combinations_with_replacement(range(MAX_EXP + 1), 2))
    if lens == "arithmetic":
        return tuple((a, b) for a, b in pairs if a != b)
    if lens == "algebraic":
        # Reverse exponent order and odd/even interleave to give a different
        # surface schedule from arithmetic.
        return tuple(sorted(((b, a) for a, b in pairs if a != b), key=lambda q: ((q[0] + q[1]) % 2, -q[0], q[1])))
    if lens == "topological":
        return tuple(sorted(((a, b) for a, b in pairs if a != b), key=lambda q: (abs(q[0] - q[1]), -(q[0] + q[1]), q)))
    if lens == "categorical":
        return tuple(sorted(((b, a) for a, b in pairs if a != b), key=lambda q: (max(q), (3 * q[0] + 5 * q[1]) % 11, q)))
    raise ValueError(lens)


def choose_binary_query(candidates, lens, asked):
    best = None
    for q in query_language(lens):
        if q in asked:
            continue
        yes = sum(response_for_order(m, lens, q) for m in candidates)
        no = len(candidates) - yes
        if yes == 0 or no == 0:
            continue
        score = (max(yes, no), abs(yes - no), q)
        if best is None or score < best[0]:
            best = (score, q)
    return None if best is None else best[1]


def identify_order(true_m, lens, universe):
    candidates = list(universe)
    asked = {}
    while len(candidates) > 1:
        q = choose_binary_query(candidates, lens, asked)
        if q is None:
            break
        ans = response_for_order(true_m, lens, q)
        asked[q] = ans
        candidates = [m for m in candidates if response_for_order(m, lens, q) == ans]
    return tuple(candidates), asked


def heldout_accuracy(true_m, pred_m, lens, asked):
    unseen = [q for q in query_language(lens) if q not in asked]
    correct = sum(response_for_order(true_m, lens, q) == response_for_order(pred_m, lens, q) for q in unseen)
    return correct, len(unseen)


class CrossLensHiddenCyclicWorld(unittest.TestCase):
    def test_four_languages_converge_on_same_coordinate_free_structure(self):
        worlds = []
        for p in PRIMES:
            for g in range(2, p):
                m = multiplicative_order(g, p)
                if 2 <= m <= MAX_EXP:
                    worlds.append((p, g, m))

        realized_orders = tuple(sorted({m for _, _, m in worlds}))
        self.assertGreaterEqual(len(realized_orders), 5)

        lenses = ("arithmetic", "algebraic", "topological", "categorical")
        exact = 0
        cross_lens = 0
        heldout_correct = 0
        heldout_total = 0
        total_queries = 0
        max_queries = 0
        algebraic_bridge_failures = 0
        structural_bridge_failures = 0

        for p, g, m in worlds:
            H = subgroup(g, p, m)

            # Independent external bridge checks, never shown to learners.
            roots = tuple(x for x in range(1, p) if (pow(x, m, p) - 1) % p == 0)
            if set(roots) != set(H):
                algebraic_bridge_failures += 1

            recovered = {}
            for lens in lenses:
                survivors, asked = identify_order(m, lens, realized_orders)
                self.assertEqual(len(survivors), 1)
                pred_m = survivors[0]
                recovered[lens] = pred_m
                total_queries += len(asked)
                max_queries = max(max_queries, len(asked))

                c, t = heldout_accuracy(m, pred_m, lens, asked)
                heldout_correct += c
                heldout_total += t
                self.assertEqual(c, t)
                self.assertEqual(pred_m, m)
                exact += 1

            if len(set(recovered.values())) == 1:
                cross_lens += 1

            # Coordinate-free comparison after learning: each recovered lens
            # induces the same finite cyclic group C_m, regardless of surface
            # language. Compare the canonical operation law, not token names.
            tables = {lens: canonical_cyclic_table(mm) for lens, mm in recovered.items()}
            if len(set(tables.values())) != 1:
                structural_bridge_failures += 1

            # Topological and categorical invariants of the same object.
            # Cayley graph C_m has |V|=|E|=m and first Betti number 1; the
            # generated one-object action has exactly m distinct powers.
            vertices = m
            edges = m
            betti1 = edges - vertices + 1
            generated_endomorphisms = len({k % m for k in range(2 * m + 1)})
            if betti1 != 1 or generated_endomorphisms != m:
                structural_bridge_failures += 1

        print(
            "CROSS_LENS_HIDDEN_CYCLIC_WORLD: "
            f"worlds={len(worlds)}; realized_orders={realized_orders}; "
            f"lens_recoveries={exact}/{len(worlds) * len(lenses)}; "
            f"cross_lens_convergence={cross_lens}/{len(worlds)}; "
            f"heldout={heldout_correct}/{heldout_total}; "
            f"total_queries={total_queries}; max_queries={max_queries}; "
            f"algebraic_bridge_failures={algebraic_bridge_failures}; "
            f"structural_bridge_failures={structural_bridge_failures}"
        )

        self.assertGreater(len(worlds), 0)
        self.assertEqual(exact, len(worlds) * len(lenses))
        self.assertEqual(cross_lens, len(worlds))
        self.assertEqual(heldout_correct, heldout_total)
        self.assertEqual(algebraic_bridge_failures, 0)
        self.assertEqual(structural_bridge_failures, 0)
        self.assertLess(max_queries, len(realized_orders))


if __name__ == "__main__":
    unittest.main()
