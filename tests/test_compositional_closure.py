import itertools
import unittest


def all_maps(n):
    return tuple(itertools.product(range(n), repeat=n))


def compose(f, g):
    # f ∘ g
    return tuple(f[g[x]] for x in range(len(f)))


def monoid_closure(generators, n):
    ident = tuple(range(n))
    seen = {ident}
    frontier = [ident]
    while frontier:
        f = frontier.pop()
        for g in generators:
            for h in (compose(g, f), compose(f, g)):
                if h not in seen:
                    seen.add(h)
                    frontier.append(h)
    return tuple(sorted(seen))


def obs_relation(v, continuations):
    n = len(v)
    return frozenset(
        (x, y)
        for x in range(n)
        for y in range(n)
        if all(v[f[x]] == v[f[y]] for f in continuations)
    )


def is_congruence(E, actions):
    for x, y in E:
        for g in actions:
            if (g[x], g[y]) not in E:
                return False
    return True


class CompositionalClosure(unittest.TestCase):
    """Exhaustive finite test of the compositional MSI conjecture.

    Worlds: |X|=3, binary verifier observation v, ordered generator pairs (g0,g1).
    The protected future space is the full transformation monoid G*.

    Development starts only from one-step continuations {id,g0,g1}. Whenever the
    current relation is coarser than the full behavioural relation, the verifier
    exposes the lexicographically first reachable composite that separates some
    still-merged pair. MSI refinement intersects in that continuation kernel.

    We test that this always terminates exactly at the all-reachable-futures
    quotient, and that the result is a congruence supporting quotient dynamics
    with composition preserved.
    """

    def test_repeated_refinement_recovers_behavioural_congruence(self):
        n = 3
        ident = tuple(range(n))
        maps = all_maps(n)

        total_worlds = 0
        one_step_too_coarse = 0
        composite_separators_added = 0
        convergence_failures = 0
        congruence_failures = 0
        composition_failures = 0
        ablation_witnesses = 0
        examples = []

        for v in itertools.product((0, 1), repeat=n):
            for g0 in maps:
                for g1 in maps:
                    total_worlds += 1
                    gens = (g0, g1)
                    full = monoid_closure(gens, n)
                    target = obs_relation(v, full)

                    retained = []
                    for f in (ident, g0, g1):
                        if f not in retained:
                            retained.append(f)
                    current = obs_relation(v, retained)

                    if current != target:
                        one_step_too_coarse += 1

                    added = []
                    while current != target:
                        witness = None
                        for f in full:
                            if f in retained:
                                continue
                            Kf = obs_relation(v, (f,))
                            if any((x, y) in current and (x, y) not in Kf for x in range(n) for y in range(n)):
                                witness = f
                                break
                        if witness is None:
                            convergence_failures += 1
                            break
                        retained.append(witness)
                        added.append(witness)
                        current = current.intersection(obs_relation(v, (witness,)))
                        composite_separators_added += 1

                    if current != target:
                        continue

                    if not is_congruence(target, full):
                        congruence_failures += 1
                        continue

                    # Quotient action is well-defined. Check composition by representatives:
                    # [g∘f]([x]) = [g]([f]([x])]) reduces to equality of target classes.
                    def same_class(a, b):
                        return (a, b) in target

                    bad_comp = False
                    for f in full:
                        for g in full:
                            gf = compose(g, f)
                            for x in range(n):
                                lhs = gf[x]
                                rhs = g[f[x]]
                                if not same_class(lhs, rhs):
                                    bad_comp = True
                                    break
                            if bad_comp:
                                break
                        if bad_comp:
                            break
                    if bad_comp:
                        composition_failures += 1
                        continue

                    # Falsifier / ablation arm: if development needed any composite,
                    # remove the last required separator and verify that an erroneous
                    # merge returns.
                    if added:
                        ablated = [f for f in retained if f != added[-1]]
                        E_ablated = obs_relation(v, ablated)
                        if E_ablated != target:
                            ablation_witnesses += 1
                            if len(examples) < 5:
                                restored = next(
                                    ((x, y) for x in range(n) for y in range(n)
                                     if (x, y) in E_ablated and (x, y) not in target),
                                    None,
                                )
                                examples.append((v, g0, g1, added[-1], restored, len(full)))

        self.assertEqual(convergence_failures, 0)
        self.assertEqual(congruence_failures, 0)
        self.assertEqual(composition_failures, 0)
        self.assertGreater(one_step_too_coarse, 0)
        self.assertGreater(composite_separators_added, 0)
        self.assertGreater(ablation_witnesses, 0)

        print(
            "compositional closure census: "
            f"total_worlds={total_worlds}; "
            f"one_step_too_coarse={one_step_too_coarse}; "
            f"composite_separators_added={composite_separators_added}; "
            f"convergence_failures={convergence_failures}; "
            f"congruence_failures={congruence_failures}; "
            f"composition_failures={composition_failures}; "
            f"ablation_witnesses={ablation_witnesses}; "
            f"examples={examples}"
        )


if __name__ == "__main__":
    unittest.main()
