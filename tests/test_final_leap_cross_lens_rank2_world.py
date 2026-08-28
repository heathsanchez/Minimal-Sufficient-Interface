import itertools
import math
import unittest


# Hidden worlds are anonymous rank-2 finite tori.  Surface coordinates are never
# compared across lenses; the post-learning bridge is the coordinate-free Smith
# invariant of the finite abelian group.
RAW_PAIRS = tuple((m, n) for m in range(2, 9) for n in range(m, 9))
# The first attempt used 16 and left a nine-world ambiguity class because the
# Smith exponent can reach lcm(7,8)=56.  The verifier residual therefore forces
# a richer observation horizon rather than a changed hidden hypothesis family.
MAX_EXP = 64
LENSES = ("arithmetic", "algebraic", "topological", "categorical")


def smith(m, n):
    d1 = math.gcd(m, n)
    d2 = math.lcm(m, n)
    return (d1, d2)


def canonical_worlds():
    reps = {}
    for m, n in RAW_PAIRS:
        reps.setdefault(smith(m, n), (m, n))
    return tuple(sorted(reps))


def congruent(inv, u, v):
    d1, d2 = inv
    return ((u[0] - v[0]) % d1 == 0 and (u[1] - v[1]) % d2 == 0)


def response(inv, lens, q):
    (a, b), (c, d) = q
    if lens == "arithmetic":
        return congruent(inv, (a, b), (c, d))
    if lens == "algebraic":
        return congruent(inv, (a, b), (c, d))
    if lens == "topological":
        return congruent(inv, (a, b), (c, d))
    if lens == "categorical":
        return congruent(inv, (a, b), (c, d))
    raise ValueError(lens)


def base_queries():
    pts = [(a, b) for a in range(MAX_EXP + 1) for b in range(MAX_EXP + 1) if a + b <= MAX_EXP]
    qs = []
    z = (0, 0)
    for p in pts:
        if p != z:
            qs.append((p, z))
    for a in range(1, 9):
        for b in range(1, 9):
            qs.append(((a, b), (b, a)))
            qs.append(((a + b, a), (b, a + b)))
    return tuple(dict.fromkeys(qs))


def query_language(lens):
    qs = list(base_queries())
    if lens == "arithmetic":
        return tuple(qs)
    if lens == "algebraic":
        return tuple(sorted((((v[1], v[0]), (u[1], u[0])) for u, v in qs), key=lambda q: ((sum(q[0]) + sum(q[1])) % 3, q)))
    if lens == "topological":
        return tuple(sorted(qs, key=lambda q: (abs(q[0][0]-q[1][0]) + abs(q[0][1]-q[1][1]), -(sum(q[0])+sum(q[1])), q)))
    if lens == "categorical":
        return tuple(sorted(((v, u) for u, v in qs), key=lambda q: ((3*sum(q[0]) + 5*sum(q[1])) % 17, q)))
    raise ValueError(lens)


def choose_query(candidates, lens, asked):
    best = None
    for q in query_language(lens):
        if q in asked:
            continue
        yes = sum(response(inv, lens, q) for inv in candidates)
        no = len(candidates) - yes
        if yes == 0 or no == 0:
            continue
        score = (max(yes, no), abs(yes-no), q)
        if best is None or score < best[0]:
            best = (score, q)
    return None if best is None else best[1]


def identify(true_inv, lens, universe):
    candidates = list(universe)
    asked = {}
    while len(candidates) > 1:
        q = choose_query(candidates, lens, asked)
        if q is None:
            break
        ans = response(true_inv, lens, q)
        asked[q] = ans
        candidates = [inv for inv in candidates if response(inv, lens, q) == ans]
    return tuple(candidates), asked


def quotient_first_generator(inv, r):
    d1, d2 = inv
    a = math.gcd(d1, r)
    b = d2
    return smith(a, b)


def canonical_table(inv):
    d1, d2 = inv
    return tuple(
        ((a+c) % d1, (b+d) % d2)
        for a in range(d1) for b in range(d2)
        for c in range(d1) for d in range(d2)
    )


def order_only_prediction(universe, true_inv, lens, q):
    same_order = [inv for inv in universe if inv[0] * inv[1] == true_inv[0] * true_inv[1]]
    vals = {response(inv, lens, q) for inv in same_order}
    return None if len(vals) != 1 else next(iter(vals))


class FinalLeapCrossLensRank2World(unittest.TestCase):
    def test_rank2_cross_lens_genesis_intervention_and_ablation(self):
        universe = canonical_worlds()
        self.assertGreaterEqual(len(universe), 12)
        by_order = {}
        for inv in universe:
            by_order.setdefault(inv[0]*inv[1], []).append(inv)
        ambiguous_orders = {N: xs for N, xs in by_order.items() if len(xs) > 1}
        self.assertGreater(len(ambiguous_orders), 0)

        lens_recoveries = 0
        convergence = 0
        heldout_correct = heldout_total = 0
        total_queries = max_queries = 0
        algebraic_bridge_failures = 0
        structural_bridge_failures = 0
        intervention_correct = intervention_total = 0
        order_only_ambiguities = 0
        order_only_errors = 0

        for true_inv in universe:
            recovered = {}
            for lens in LENSES:
                survivors, asked = identify(true_inv, lens, universe)
                self.assertEqual(len(survivors), 1)
                pred = survivors[0]
                self.assertEqual(pred, true_inv)
                recovered[lens] = pred
                lens_recoveries += 1
                total_queries += len(asked)
                max_queries = max(max_queries, len(asked))

                for q in query_language(lens):
                    if q in asked:
                        continue
                    heldout_total += 1
                    if response(pred, lens, q) == response(true_inv, lens, q):
                        heldout_correct += 1

                same_order = [inv for inv in universe if inv[0]*inv[1] == true_inv[0]*true_inv[1]]
                if len(same_order) > 1:
                    guess = same_order[0]
                    for q in query_language(lens):
                        p = order_only_prediction(universe, true_inv, lens, q)
                        if p is None:
                            order_only_ambiguities += 1
                            if response(guess, lens, q) != response(true_inv, lens, q):
                                order_only_errors += 1

            if len(set(recovered.values())) == 1:
                convergence += 1

            tables = {lens: canonical_table(inv) for lens, inv in recovered.items()}
            if len(set(tables.values())) != 1:
                structural_bridge_failures += 1

            d1, d2 = true_inv
            algebraic_points = d1 * d2
            if algebraic_points * algebraic_points != len(canonical_table(true_inv)):
                algebraic_bridge_failures += 1

            for r in (2, 3, 4, 5):
                qinv = quotient_first_generator(true_inv, r)
                pinv = quotient_first_generator(recovered["categorical"], r)
                for lens in LENSES:
                    for q in query_language(lens):
                        intervention_total += 1
                        if response(qinv, lens, q) == response(pinv, lens, q):
                            intervention_correct += 1

        print(
            "FINAL_LEAP_CROSS_LENS_RANK2: "
            f"worlds={len(universe)}; lens_recoveries={lens_recoveries}/{len(universe)*len(LENSES)}; "
            f"cross_lens_convergence={convergence}/{len(universe)}; "
            f"heldout={heldout_correct}/{heldout_total}; total_queries={total_queries}; max_queries={max_queries}; "
            f"intervention={intervention_correct}/{intervention_total}; "
            f"order_only_ambiguities={order_only_ambiguities}; order_only_errors={order_only_errors}; "
            f"algebraic_bridge_failures={algebraic_bridge_failures}; structural_bridge_failures={structural_bridge_failures}"
        )

        self.assertEqual(lens_recoveries, len(universe)*len(LENSES))
        self.assertEqual(convergence, len(universe))
        self.assertEqual(heldout_correct, heldout_total)
        self.assertEqual(intervention_correct, intervention_total)
        self.assertGreater(order_only_ambiguities, 0)
        self.assertGreater(order_only_errors, 0)
        self.assertEqual(algebraic_bridge_failures, 0)
        self.assertEqual(structural_bridge_failures, 0)
        self.assertLess(max_queries, len(universe))


if __name__ == "__main__":
    unittest.main()
