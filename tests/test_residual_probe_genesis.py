import itertools
import unittest


def apply_word(word, f, g, x):
    y = x
    for symbol in reversed(word):
        y = (f if symbol == 0 else g)[y]
    return y


def generate_probe_words(max_depth):
    """Blindly generate executable trace probes over F and G.

    The learner starts with only x, F(x), G(x). Composite probes are not named;
    they are generated from the same executable alphabet only after the current
    interface is shown insufficient by verifier residuals.
    """
    words = [()]
    frontier = [()]
    for _ in range(max_depth):
        nxt = []
        for word in frontier:
            nxt.append((0,) + word)
            nxt.append((1,) + word)
        words.extend(nxt)
        frontier = nxt
    return tuple(sorted(set(words), key=lambda w: (len(w), w)))


def all_maps(n):
    return tuple(itertools.product(range(n), repeat=n))


def permutations(n):
    return tuple(m for m in all_maps(n) if len(set(m)) == n)


def make_rows(fs, gs, n, verifier):
    return [
        (f, g, x, verifier(f, g, x))
        for f in fs
        for g in gs
        for x in range(n)
    ]


def key_for(row, probes):
    f, g, x, _ = row
    return tuple(apply_word(word, f, g, x) for word in probes)


def sufficient(rows, probes):
    seen = {}
    for row in rows:
        key = key_for(row, probes)
        y = row[3]
        if key in seen and seen[key] != y:
            return False
        seen[key] = y
    return True


def residual_pairs(rows, probes):
    """All verified disagreements hidden by the current interface."""
    buckets = {}
    residuals = []
    for row in rows:
        key = key_for(row, probes)
        bucket = buckets.setdefault(key, [])
        for previous in bucket:
            if previous[3] != row[3]:
                residuals.append((previous, row))
        bucket.append(row)
    return tuple(residuals)


def separates(probe, residual):
    a, b = residual
    return key_for(a, (probe,)) != key_for(b, (probe,))


def synthesize_missing_probe(rows, current_probes, max_depth=2):
    """Infer a new probe from residuals rather than from a named feature list."""
    residuals = residual_pairs(rows, current_probes)
    if not residuals:
        return None, residuals, ()

    generated = tuple(
        w for w in generate_probe_words(max_depth)
        if w not in set(current_probes)
    )

    # Choose the shortest lexicographic generated probe that resolves every
    # disagreement hidden by the old interface.
    survivors = tuple(
        w for w in generated
        if all(separates(w, residual) for residual in residuals)
    )
    if not survivors:
        return None, residuals, generated
    return min(survivors, key=lambda w: (len(w), w)), residuals, generated


def synthesize_output_table(rows, probe):
    """Learn only the output law over the newly created one-coordinate view."""
    table = {}
    for f, g, x, y in rows:
        value = apply_word(probe, f, g, x)
        if value in table and table[value] != y:
            raise ValueError("new probe is not sufficient")
        table[value] = y
    return table


class ResidualProbeGenesis(unittest.TestCase):
    def test_residuals_force_a_probe_not_present_in_current_interface(self):
        n = 3
        discovery_maps = permutations(n)

        # Hidden verifier-only target. The learner is not given the word FG.
        verifier = lambda f, g, x: f[g[x]]
        rows = make_rows(discovery_maps, discovery_maps, n, verifier)

        # Existing interface contains every product of the currently available
        # primitive probes: x, F(x), G(x). Even the full 3-coordinate product is
        # insufficient, so no subset/recombination of those coordinates can fix it.
        current = ((), (0,), (1,))
        self.assertFalse(sufficient(rows, current))
        residuals = residual_pairs(rows, current)
        self.assertGreater(len(residuals), 0)

        learned, residuals2, generated = synthesize_missing_probe(rows, current, 2)
        self.assertEqual(residuals2, residuals)
        self.assertIsNotNone(learned)
        self.assertIn(learned, generated)
        self.assertNotIn(learned, current)

        # The missing observation is created by blind executable-program search.
        # FG is not passed to synthesize_missing_probe; it emerges as the unique
        # shortest generated probe that separates every old-interface residual.
        self.assertEqual(learned, (0, 1))
        self.assertTrue(sufficient(rows, (learned,)))

        # It is genuinely new observational information, not merely an alias of
        # one of the old coordinates on the discovery regime.
        old_vectors = {
            tuple(apply_word(p, f, g, x) for f, g, x, _ in rows)
            for p in current
        }
        learned_vector = tuple(
            apply_word(learned, f, g, x) for f, g, x, _ in rows
        )
        self.assertNotIn(learned_vector, old_vectors)

    def test_new_probe_transfers_and_ablation_restores_failure(self):
        n = 3
        maps = all_maps(n)
        discovery_maps = set(permutations(n))
        verifier = lambda f, g, x: f[g[x]]

        discovery_rows = make_rows(
            tuple(discovery_maps), tuple(discovery_maps), n, verifier
        )
        current = ((), (0,), (1,))
        learned, _, _ = synthesize_missing_probe(discovery_rows, current, 2)
        self.assertIsNotNone(learned)

        # Freeze the learned probe and learn the smallest output law on the
        # discovery regime. All three probe values occur there.
        table = synthesize_output_table(discovery_rows, learned)
        self.assertEqual(set(table), set(range(n)))

        heldout_rows = [
            row
            for row in make_rows(maps, maps, n, verifier)
            if not (row[0] in discovery_maps and row[1] in discovery_maps)
        ]

        transfer_failures = 0
        for f, g, x, expected in heldout_rows:
            value = apply_word(learned, f, g, x)
            predicted = table[value]
            if predicted != expected:
                transfer_failures += 1

        # Exact ablation criterion: removing the learned probe returns us to an
        # interface that provably aliases held-out examples with different
        # verified outputs.
        heldout_residuals_without_probe = residual_pairs(heldout_rows, current)
        heldout_residuals_with_probe = residual_pairs(heldout_rows, (learned,))

        print(
            "residual probe genesis: "
            f"discovery_maps={len(discovery_maps)}; "
            f"old_interface_residuals={len(residual_pairs(discovery_rows, current))}; "
            f"learned_probe={learned}; "
            f"heldout_rows={len(heldout_rows)}; "
            f"transfer_failures={transfer_failures}; "
            f"ablation_residuals={len(heldout_residuals_without_probe)}"
        )

        self.assertEqual(transfer_failures, 0)
        self.assertGreater(len(heldout_residuals_without_probe), 0)
        self.assertEqual(len(heldout_residuals_with_probe), 0)


if __name__ == "__main__":
    unittest.main()
