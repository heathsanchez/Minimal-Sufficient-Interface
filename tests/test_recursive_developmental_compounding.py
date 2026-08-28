import unittest
from collections import defaultdict


SOURCE_LABELS = (1, 1, 1, 0, 0, 0)
SOURCE_QUERIES = {
    "s0": (1, 1, 0, 0, 0, 1),
    "s1": (1, 1, 0, 0, 1, 0),
    "s2": (0, 0, 0, 0, 0, 1),
    "s3": (1, 0, 1, 1, 0, 1),
    "s4": (0, 1, 1, 1, 0, 1),
    "s5": (0, 1, 0, 0, 1, 0),
    "s6": (1, 0, 1, 1, 1, 1),
    "s7": (1, 1, 0, 1, 0, 0),
}
SOURCE_ORDER = tuple(SOURCE_QUERIES)

# Source-distinct target: different state ordering, different observation table,
# disjoint query identities. The retained policy can transfer only through the
# mechanically computed query fingerprint, not by replaying literal source IDs.
TARGET_LABELS = (1, 0, 1, 0, 1, 0)
TARGET_QUERIES = {
    "t0": (0, 1, 0, 1, 1, 1),
    "t1": (1, 1, 0, 1, 0, 0),
    "t2": (0, 1, 0, 1, 0, 1),
    "t3": (1, 0, 1, 1, 1, 0),
    "t4": (0, 1, 1, 0, 0, 1),
    "t5": (0, 0, 0, 1, 0, 0),
    "t6": (1, 0, 1, 0, 1, 1),
    "t7": (1, 0, 1, 0, 1, 0),
}
TARGET_ORDER = tuple(TARGET_QUERIES)

# Downstream capability. It collapses each protected future class to a
# representative. Under the matched one-query target interfaces it is
# quotient-admissible only after the retained policy discovers t2.
DOWNSTREAM_ACTION = (0, 1, 0, 1, 0, 1)


def residual(labels, queries, chosen):
    """First verifier-certified pair still merged but future-distinct."""
    n = len(labels)
    for i in range(n):
        for j in range(i + 1, n):
            if labels[i] == labels[j]:
                continue
            if all(queries[q][i] == queries[q][j] for q in chosen):
                return (i, j)
    return None


def sufficient(labels, queries, chosen):
    return residual(labels, queries, chosen) is None


def query_fingerprint(column):
    """Anonymous, source-independent structural fingerprint.

    Complementary observations receive the same fingerprint. No semantic query
    name or source-state identity is retained.
    """
    ones = sum(column)
    return min(ones, len(column) - ones)


def relation(queries, chosen, n):
    return {
        (i, j)
        for i in range(n)
        for j in range(n)
        if all(queries[q][i] == queries[q][j] for q in chosen)
    }


def quotient_admissible(action, queries, chosen):
    rel = relation(queries, chosen, len(action))
    return all((action[i], action[j]) in rel for (i, j) in rel)


def cold_episode(labels, queries, order, budget):
    chosen = []
    history = []
    for _ in range(budget):
        pair = residual(labels, queries, chosen)
        if pair is None:
            break
        history.append(pair)
        separating = [
            q for q in order
            if q not in chosen and queries[q][pair[0]] != queries[q][pair[1]]
        ]
        if not separating:
            break
        chosen.append(separating[0])
    return tuple(chosen), tuple(history)


def compile_policy(queries, order, certified_residual_history):
    """Compress verified residual history into an anonymous query policy.

    For each mechanically generated fingerprint, retain the mean number of
    certified source residuals separated by queries of that class. The compiler
    sees only verifier-returned pairs plus executable query observations.
    """
    total = defaultdict(float)
    count = defaultdict(int)
    for q in order:
        f = query_fingerprint(queries[q])
        coverage = sum(
            queries[q][i] != queries[q][j]
            for i, j in certified_residual_history
        )
        total[f] += coverage
        count[f] += 1
    return {f: total[f] / count[f] for f in total}


def policy_episode(labels, queries, order, budget, policy, literal_priority=()):
    chosen = []
    history = []
    literal_priority = tuple(literal_priority)
    for _ in range(budget):
        pair = residual(labels, queries, chosen)
        if pair is None:
            break
        history.append(pair)
        separating = [
            q for q in order
            if q not in chosen and queries[q][pair[0]] != queries[q][pair[1]]
        ]
        if not separating:
            break

        # RAW_HISTORY may replay literal source query identities. Target IDs are
        # disjoint by construction, so literal replay has no privileged match.
        literal = [q for q in literal_priority if q in separating]
        if literal:
            q = literal[0]
        elif policy:
            index = {q: k for k, q in enumerate(order)}
            q = max(
                separating,
                key=lambda x: (
                    policy.get(query_fingerprint(queries[x]), 0.0),
                    -index[x],
                ),
            )
        else:
            q = separating[0]
        chosen.append(q)
    return tuple(chosen), tuple(history)


class RecursiveDevelopmentalCompounding(unittest.TestCase):
    def test_source_episode_induces_a_nonliteral_policy(self):
        chosen, history = cold_episode(
            SOURCE_LABELS, SOURCE_QUERIES, SOURCE_ORDER, budget=8
        )
        self.assertTrue(sufficient(SOURCE_LABELS, SOURCE_QUERIES, chosen))
        self.assertEqual(chosen, ("s0", "s1", "s7"))
        self.assertEqual(history, ((0, 3), (0, 5), (2, 3)))

        policy = compile_policy(SOURCE_QUERIES, SOURCE_ORDER, history)
        self.assertGreater(policy[3], policy[2])
        self.assertGreater(policy[3], policy[1])

    def test_development_changes_later_development_under_matched_budget(self):
        source_chosen, source_history = cold_episode(
            SOURCE_LABELS, SOURCE_QUERIES, SOURCE_ORDER, budget=8
        )
        warm_policy = compile_policy(SOURCE_QUERIES, SOURCE_ORDER, source_history)

        # Deterministically corrupted residual history: same source carrier and
        # same compiler, but false pair structure. This makes fingerprint 2
        # preferred instead of fingerprint 3.
        sham_history = ((0, 1), (0, 2), (2, 4))
        sham_policy = compile_policy(SOURCE_QUERIES, SOURCE_ORDER, sham_history)

        budget = 1

        cold_chosen, _ = policy_episode(
            TARGET_LABELS, TARGET_QUERIES, TARGET_ORDER, budget, policy={}
        )
        raw_chosen, _ = policy_episode(
            TARGET_LABELS,
            TARGET_QUERIES,
            TARGET_ORDER,
            budget,
            policy={},
            literal_priority=source_chosen,
        )
        warm_chosen, _ = policy_episode(
            TARGET_LABELS, TARGET_QUERIES, TARGET_ORDER, budget, warm_policy
        )
        sham_chosen, _ = policy_episode(
            TARGET_LABELS, TARGET_QUERIES, TARGET_ORDER, budget, sham_policy
        )
        ablated_chosen, _ = policy_episode(
            TARGET_LABELS, TARGET_QUERIES, TARGET_ORDER, budget, policy={}
        )

        # All arms have the same target language, verifier and one-query budget.
        self.assertEqual(cold_chosen, ("t0",))
        self.assertEqual(raw_chosen, cold_chosen)
        self.assertEqual(sham_chosen, ("t0",))
        self.assertEqual(ablated_chosen, cold_chosen)
        self.assertEqual(warm_chosen, ("t2",))

        # Only the retained developmental policy reaches the exact target MSI.
        self.assertFalse(sufficient(TARGET_LABELS, TARGET_QUERIES, cold_chosen))
        self.assertFalse(sufficient(TARGET_LABELS, TARGET_QUERIES, raw_chosen))
        self.assertFalse(sufficient(TARGET_LABELS, TARGET_QUERIES, sham_chosen))
        self.assertFalse(sufficient(TARGET_LABELS, TARGET_QUERIES, ablated_chosen))
        self.assertTrue(sufficient(TARGET_LABELS, TARGET_QUERIES, warm_chosen))

        # The later executable capability is present in the common raw language.
        # After the matched one-query developmental episode it is admissible only
        # on WARM's exact target interface. The zero-query indiscrete quotient is
        # deliberately not used as a comparator: every function descends there
        # trivially, which is not the developmental claim under test.
        self.assertFalse(
            quotient_admissible(DOWNSTREAM_ACTION, TARGET_QUERIES, cold_chosen)
        )
        self.assertFalse(
            quotient_admissible(DOWNSTREAM_ACTION, TARGET_QUERIES, raw_chosen)
        )
        self.assertFalse(
            quotient_admissible(DOWNSTREAM_ACTION, TARGET_QUERIES, sham_chosen)
        )
        self.assertFalse(
            quotient_admissible(DOWNSTREAM_ACTION, TARGET_QUERIES, ablated_chosen)
        )
        self.assertTrue(
            quotient_admissible(DOWNSTREAM_ACTION, TARGET_QUERIES, warm_chosen)
        )

        # Exact ancestor ablation restores the cold developmental frontier.
        self.assertEqual(ablated_chosen, cold_chosen)

    def test_source_and_target_do_not_share_literal_query_identity(self):
        self.assertTrue(set(SOURCE_QUERIES).isdisjoint(TARGET_QUERIES))
        self.assertNotEqual(tuple(SOURCE_QUERIES.values()), tuple(TARGET_QUERIES.values()))
        self.assertNotEqual(SOURCE_LABELS, TARGET_LABELS)


if __name__ == "__main__":
    unittest.main()
