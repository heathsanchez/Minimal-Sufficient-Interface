import itertools
import unittest


STATES = tuple(range(4))


def bit0(x):
    return (x >> 0) & 1


def bit1(x):
    return (x >> 1) & 1


def semantics(term):
    tag = term[0]
    if tag == "b0":
        return tuple(bit0(x) for x in STATES)
    if tag == "b1":
        return tuple(bit1(x) for x in STATES)
    if tag == "not":
        a = semantics(term[1])
        return tuple(1 - v for v in a)
    a = semantics(term[1])
    b = semantics(term[2])
    if tag == "and":
        return tuple(x & y for x, y in zip(a, b))
    if tag == "xor":
        return tuple(x ^ y for x, y in zip(a, b))
    raise ValueError(tag)


def size(term):
    if term[0] in ("b0", "b1"):
        return 1
    if term[0] == "not":
        return 1 + size(term[1])
    return 1 + size(term[1]) + size(term[2])


def generated_observations(max_depth=2):
    """Generate an observation language without naming any target observation."""
    layers = {0: {("b0",), ("b1",)}}
    all_terms = set(layers[0])
    for d in range(1, max_depth + 1):
        prev = set().union(*(layers[i] for i in range(d)))
        layer = set()
        for a in prev:
            layer.add(("not", a))
        for a in prev:
            for b in prev:
                layer.add(("and", a, b))
                layer.add(("xor", a, b))
        layers[d] = layer - all_terms
        all_terms |= layer

    # Keep the shortest deterministic representative of each extensional
    # observation. The learner sees terms and verifier answers, not target IDs.
    best = {}
    for term in all_terms:
        sem = semantics(term)
        key = (size(term), repr(term))
        if sem not in best or key < (size(best[sem]), repr(best[sem])):
            best[sem] = term
    return tuple(sorted(best.values(), key=lambda t: (size(t), repr(t))))


def eq_from_basis(basis):
    return {
        (x, y)
        for x in STATES
        for y in STATES
        if all(obs[x] == obs[y] for obs in basis)
    }


def residuals(current_basis, hidden):
    current_eq = eq_from_basis(current_basis)
    return tuple(
        (x, y)
        for x, y in sorted(current_eq)
        if x < y and hidden[x] != hidden[y]
    )


def learn_new_observation(current_basis, hidden, terms):
    """Select the least generated observation whose induced refinement is
    exactly the verifier-required one. Hidden observation identity is never
    supplied to the candidate generator or ranking rule.
    """
    old_eq = eq_from_basis(current_basis)
    target_eq = eq_from_basis(current_basis + (hidden,))
    live = residuals(current_basis, hidden)
    if not live:
        return None

    admissible = []
    for term in terms:
        obs = semantics(term)
        # Must repair every live collision.
        if not all(obs[x] != obs[y] for x, y in live):
            continue
        # Must introduce no verifier-unlicensed distinctions.
        if eq_from_basis(current_basis + (obs,)) != target_eq:
            continue
        # Must be genuinely new relative to the old interface.
        if eq_from_basis(current_basis + (obs,)) == old_eq:
            continue
        admissible.append(term)

    if not admissible:
        return None
    return min(admissible, key=lambda t: (size(t), repr(t)))


class ObservationLanguageGenesis(unittest.TestCase):
    def test_residuals_generate_minimal_new_observation_basis(self):
        terms = generated_observations(2)
        current = (tuple(bit0(x) for x in STATES),)

        live_worlds = 0
        recovered = 0
        exact_kernel = 0
        ablation_failures = 0

        # The verifier's hidden distinction ranges over every binary
        # observation on the four-state carrier. No target term is supplied.
        for hidden in itertools.product((0, 1), repeat=len(STATES)):
            live = residuals(current, hidden)
            if not live:
                continue
            live_worlds += 1
            term = learn_new_observation(current, hidden, terms)
            self.assertIsNotNone(term, msg=f"no generated repair for {hidden}")
            recovered += 1

            obs = semantics(term)
            target_eq = eq_from_basis(current + (hidden,))
            warm_eq = eq_from_basis(current + (obs,))
            cold_eq = eq_from_basis(current)

            if warm_eq == target_eq:
                exact_kernel += 1
            if cold_eq != target_eq:
                ablation_failures += 1

            # Minimality in the generated language: no smaller candidate can
            # satisfy the exact verifier-licensed refinement.
            for other in terms:
                if size(other) >= size(term):
                    continue
                other_obs = semantics(other)
                self.assertNotEqual(eq_from_basis(current + (other_obs,)), target_eq)

        print(
            "observation-language genesis: "
            f"live_worlds={live_worlds}; recovered={recovered}; "
            f"exact_kernel={exact_kernel}; ablation_failures={ablation_failures}; "
            f"generated_extensional_atoms={len(terms)}"
        )

        self.assertGreater(live_worlds, 0)
        self.assertEqual(recovered, live_worlds)
        self.assertEqual(exact_kernel, live_worlds)
        self.assertEqual(ablation_failures, live_worlds)


if __name__ == "__main__":
    unittest.main()
