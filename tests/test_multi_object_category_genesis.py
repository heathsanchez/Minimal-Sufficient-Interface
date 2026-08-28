import itertools
import unittest


def transitive_closure(n, edges):
    reach = [[False] * n for _ in range(n)]
    for i in range(n):
        reach[i][i] = True
    for i, j in edges:
        reach[i][j] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    return reach


def make_thin_category(n, edge_mask):
    primitive = [(0, 1), (0, 2), (1, 2)]
    edges = [e for bit, e in enumerate(primitive) if edge_mask & (1 << bit)]
    reach = transitive_closure(n, edges)
    arrows = [(i, j) for i in range(n) for j in range(n) if reach[i][j]]
    index = {a: k for k, a in enumerate(arrows)}

    def compose(g, f):
        # g ∘ f exists exactly when cod(f) = dom(g).
        if f[1] != g[0]:
            return None
        return (f[0], g[1])

    return arrows, index, compose


def permute_tokens(arrows, shift):
    m = len(arrows)
    perm = {old: (old + shift) % m for old in range(m)}
    inv = {new: old for old, new in perm.items()}
    return perm, inv


def verifier_table(arrows, index, compose, perm, inv):
    m = len(arrows)
    table = {}
    for g_tok in range(m):
        for f_tok in range(m):
            g = arrows[inv[g_tok]]
            f = arrows[inv[f_tok]]
            out = compose(g, f)
            table[(g_tok, f_tok)] = None if out is None else perm[index[out]]
    return table


def learn_from_residuals(table, m):
    """Start from the one-object hypothesis that every arrow pair composes.

    Every invalid verifier response is a residual forcing a typed separation.
    Valid responses also reveal the anonymously named composite token. The
    learned object/type structure is reconstructed only after the full partial
    composition behaviour has been accumulated.
    """
    predicted_total = {(g, f): True for g in range(m) for f in range(m)}
    residuals = []
    learned = {}
    for pair in sorted(predicted_total):
        out = table[pair]
        if out is None:
            residuals.append(pair)
        learned[pair] = out
    return learned, residuals


def discover_identities(table, m):
    identities = []
    for e in range(m):
        if table[(e, e)] != e:
            continue
        ok = True
        for a in range(m):
            left = table[(e, a)]
            right = table[(a, e)]
            if left is not None and left != a:
                ok = False
                break
            if right is not None and right != a:
                ok = False
                break
        if ok:
            identities.append(e)
    return identities


def recover_typed_structure(table, m):
    ids = discover_identities(table, m)
    src = {}
    dst = {}
    for a in range(m):
        right_ids = [e for e in ids if table[(a, e)] == a]
        left_ids = [e for e in ids if table[(e, a)] == a]
        if len(right_ids) != 1 or len(left_ids) != 1:
            raise AssertionError("object boundary is not uniquely recoverable")
        src[a] = right_ids[0]
        dst[a] = left_ids[0]
    return ids, src, dst


def verify_recovered_category(table, m, ids, src, dst):
    # Typing exactly predicts defined composition.
    for g in range(m):
        for f in range(m):
            should_compose = dst[f] == src[g]
            if (table[(g, f)] is not None) != should_compose:
                return False
            if should_compose:
                h = table[(g, f)]
                if src[h] != src[f] or dst[h] != dst[g]:
                    return False

    # Recovered identities are local identities for all typed arrows.
    for a in range(m):
        if table[(a, src[a])] != a:
            return False
        if table[(dst[a], a)] != a:
            return False

    # Associativity wherever the typed composites exist.
    for h in range(m):
        for g in range(m):
            for f in range(m):
                gf = table[(g, f)]
                hg = table[(h, g)]
                if gf is None or hg is None:
                    continue
                left = table[(h, gf)]
                right = table[(hg, f)]
                if left != right:
                    return False
    return True


class MultiObjectCategoryGenesis(unittest.TestCase):
    def test_untyped_tokens_residuals_recover_objects_homs_and_composition(self):
        n = 3
        worlds = 0
        nontrivial_worlds = 0
        total_residuals = 0
        recovery_failures = 0
        invariance_failures = 0

        for edge_mask in range(8):
            arrows, index, compose = make_thin_category(n, edge_mask)
            canonical_object_count = n
            canonical_arrow_count = len(arrows)
            signatures = []

            # Independent anonymous presentations of the same latent category.
            for shift in range(len(arrows)):
                perm, inv = permute_tokens(arrows, shift)
                table = verifier_table(arrows, index, compose, perm, inv)
                learned, residuals = learn_from_residuals(table, len(arrows))
                ids, src, dst = recover_typed_structure(learned, len(arrows))

                worlds += 1
                total_residuals += len(residuals)
                if len(residuals) > 0:
                    nontrivial_worlds += 1

                if len(ids) != canonical_object_count:
                    recovery_failures += 1
                    continue
                if not verify_recovered_category(learned, len(arrows), ids, src, dst):
                    recovery_failures += 1
                    continue

                # Coordinate-free signature: object count, arrow count, and
                # multiset of hom-set cardinalities. This must be invariant to
                # anonymous token renaming.
                hom_counts = []
                for x in ids:
                    for y in ids:
                        hom_counts.append(sum(1 for a in range(len(arrows)) if src[a] == x and dst[a] == y))
                signatures.append((len(ids), canonical_arrow_count, tuple(sorted(hom_counts))))

            if len(set(signatures)) != 1:
                invariance_failures += 1

        print(
            "multi-object category genesis: "
            f"worlds={worlds}; nontrivial_worlds={nontrivial_worlds}; "
            f"residuals={total_residuals}; recovery_failures={recovery_failures}; "
            f"presentation_invariance_failures={invariance_failures}"
        )

        self.assertGreater(worlds, 0)
        self.assertGreater(nontrivial_worlds, 0)
        self.assertGreater(total_residuals, 0)
        self.assertEqual(recovery_failures, 0)
        self.assertEqual(invariance_failures, 0)


if __name__ == "__main__":
    unittest.main()
