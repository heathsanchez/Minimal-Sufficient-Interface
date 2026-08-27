import itertools
import unittest



def compose(f, g):
    """Return f ∘ g for tuple maps."""
    return tuple(f[g[x]] for x in range(len(g)))


def identity(n):
    return tuple(range(n))


def eval_word(word, generators, n):
    """Execute a word left-to-right as sequential primitive actions.

    The learner is given only primitive actions plus this generic sequential
    execution mechanism.  It is not given the generated monoid, its elements,
    or the target behavioural quotient.
    """
    out = identity(n)
    for i in word:
        out = compose(generators[i], out)
    return out


def all_words(num_generators, max_len):
    yield ()
    for k in range(1, max_len + 1):
        yield from itertools.product(range(num_generators), repeat=k)


def hidden_closure(generators, n):
    """Verifier-side complete closure, used only as the external judge."""
    seen = {identity(n)}
    frontier = [identity(n)]
    while frontier:
        h = frontier.pop()
        for g in generators:
            gh = compose(g, h)
            if gh not in seen:
                seen.add(gh)
                frontier.append(gh)
    return seen


def signature(x, maps, obs):
    return tuple(obs[m[x]] for m in maps)


def relation(maps, obs, n):
    return tuple(tuple(signature(x, maps, obs) == signature(y, maps, obs) for y in range(n)) for x in range(n))


def residual_pair(current_maps, target_maps, obs, n):
    """Verifier returns only a merged pair that the hidden full future family splits."""
    cur = relation(current_maps, obs, n)
    tgt = relation(target_maps, obs, n)
    for x in range(n):
        for y in range(x + 1, n):
            if cur[x][y] and not tgt[x][y]:
                return (x, y)
    return None


def discover_separator(pair, current_maps, generators, obs, n):
    """Blind syntax search for the shortest new composite separating the pair.

    No closure table or target separator is supplied.  We enumerate words over
    primitive actions by length, execute them, deduplicate extensionally, and
    stop at the first genuinely new behaviour that separates the residual.
    A finite transformation monoid on n states has at most n^n maps, so length
    n^n is a safe finite bound for finding any reachable map.
    """
    x, y = pair
    current = set(current_maps)
    seen = set()
    max_len = n ** n
    for word in all_words(len(generators), max_len):
        m = eval_word(word, generators, n)
        if m in seen:
            continue
        seen.add(m)
        if m in current:
            continue
        if obs[m[x]] != obs[m[y]]:
            return word, m
    return None


def developmental_discovery(generators, obs, n):
    """Counterexample -> synthesized composite -> refined interface until silent."""
    target = hidden_closure(generators, n)  # oracle only
    current = [identity(n)] + list(generators)
    # extensional dedup while preserving order
    current = list(dict.fromkeys(current))
    discoveries = []
    while True:
        pair = residual_pair(current, target, obs, n)
        if pair is None:
            return current, discoveries, target
        found = discover_separator(pair, current, generators, obs, n)
        if found is None:
            raise AssertionError(("live residual had no synthesized separator", pair, generators, obs))
        word, m = found
        current.append(m)
        discoveries.append((pair, word, m))


def invariant(rel, maps, n):
    for m in maps:
        for x in range(n):
            for y in range(n):
                if rel[x][y] and not rel[m[x]][m[y]]:
                    return False
    return True


class CounterexampleCompositionDiscovery(unittest.TestCase):
    def test_four_state_single_primitive_discovers_needed_composites(self):
        n = 4
        total = 0
        worlds_needing_discovery = 0
        total_discovered = 0
        failures = 0
        congruence_failures = 0
        ablation_witnesses = 0
        examples = []

        for obs in itertools.product(range(2), repeat=n):
            for g in itertools.product(range(n), repeat=n):
                total += 1
                current, discoveries, target = developmental_discovery([g], obs, n)
                target_rel = relation(target, obs, n)
                learned_rel = relation(current, obs, n)
                if learned_rel != target_rel:
                    failures += 1
                    continue
                if not invariant(learned_rel, target, n):
                    congruence_failures += 1

                if discoveries:
                    worlds_needing_discovery += 1
                    total_discovered += len(discoveries)
                    # exact causal ablation of the last discovered composite
                    ablated = current[:-1]
                    if relation(ablated, obs, n) != target_rel:
                        ablation_witnesses += 1
                    if len(examples) < 5:
                        examples.append((obs, g, discoveries))

        print(
            "counterexample composition discovery census: "
            f"total_worlds={total}; "
            f"worlds_needing_discovery={worlds_needing_discovery}; "
            f"total_synthesized_composites={total_discovered}; "
            f"recovery_failures={failures}; "
            f"congruence_failures={congruence_failures}; "
            f"ablation_witnesses={ablation_witnesses}; "
            f"examples={examples}"
        )

        self.assertEqual(total, 4096)
        self.assertGreater(worlds_needing_discovery, 0)
        self.assertEqual(failures, 0)
        self.assertEqual(congruence_failures, 0)
        self.assertEqual(ablation_witnesses, worlds_needing_discovery)

    def test_system_is_not_given_composite_separator_identity(self):
        # A concrete world from the earlier compositional census.
        n = 4
        obs = (0, 0, 0, 1)
        g = (0, 2, 3, 0)
        current, discoveries, target = developmental_discovery([g], obs, n)
        self.assertTrue(discoveries)
        pair, word, m = discoveries[0]
        # The learned separator is a proper composite word, not a primitive.
        self.assertGreater(len(word), 1)
        self.assertNotEqual(m, g)
        self.assertEqual(relation(current, obs, n), relation(target, obs, n))


if __name__ == "__main__":
    unittest.main()
