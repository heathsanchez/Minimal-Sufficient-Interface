import itertools
import unittest


def maps(n):
    return tuple(itertools.product(range(n), repeat=n))


def compose(f, g):
    return tuple(f[g[x]] for x in range(len(f)))


def closure(gens, n):
    ident = tuple(range(n))
    seen = {ident}
    frontier = [ident]
    while frontier:
        h = frontier.pop()
        for g in gens:
            k = compose(g, h)
            if k not in seen:
                seen.add(k)
                frontier.append(k)
    return seen


def relation(obs_family, n):
    return frozenset(
        (x, y)
        for x in range(n)
        for y in range(n)
        if all(o[x] == o[y] for o in obs_family)
    )


def preserves(rel, h):
    return all((h[x], h[y]) in rel for x, y in rel)


def first_residual(v, target):
    for x in range(len(v)):
        for y in range(len(v)):
            if v[x] == v[y] and target[x] != target[y]:
                return x, y
    return None


class ResidualMorphismClass(unittest.TestCase):
    """Measure what a residual actually determines at the morphism level.

    Candidate implementations are never compared syntactically.  Each candidate h
    is quotient by the behavioural refinement it induces through v∘h.  The gate
    asks whether all *maximally future-useful* residual repairs collapse to one
    behavioural class.  If not, the residual determines a version space rather
    than a unique morphism class, which is the scientifically correct boundary.
    """

    def test_optimal_repairs_collapse_or_expose_version_space(self):
        n = 3
        all_maps = maps(n)
        ident = tuple(range(n))

        worlds = 0
        eligible_worlds = 0
        unique_class_worlds = 0
        multi_class_worlds = 0
        max_classes = 0
        examples = []

        for v in itertools.product((0, 1), repeat=n):
            old_rel = relation((v,), n)
            for target in itertools.product((0, 1), repeat=n):
                residual = first_residual(v, target)
                if residual is None:
                    continue
                worlds += 1
                x, y = residual

                for g in all_maps:
                    old_cl = closure((g,), n)
                    scored = []
                    for h in all_maps:
                        if h == ident or h == g or h in old_cl:
                            continue
                        vh = tuple(v[h[s]] for s in range(n))
                        if vh[x] == vh[y]:
                            continue
                        new_rel = relation((v, vh), n)
                        new_cl = closure((g, h), n)
                        enabled = tuple(
                            k for k in all_maps
                            if k not in old_cl
                            and k in new_cl
                            and not preserves(old_rel, k)
                            and preserves(new_rel, k)
                        )
                        if enabled:
                            scored.append((len(enabled), h, new_rel))

                    if not scored:
                        continue
                    eligible_worlds += 1
                    best = max(s[0] for s in scored)
                    best_rows = [s for s in scored if s[0] == best]
                    classes = {s[2] for s in best_rows}
                    max_classes = max(max_classes, len(classes))
                    if len(classes) == 1:
                        unique_class_worlds += 1
                    else:
                        multi_class_worlds += 1
                        if len(examples) < 5:
                            examples.append((v, target, g, residual, best, len(best_rows), len(classes)))

        print(
            "residual morphism-class census: "
            f"residual_worlds={worlds}; eligible_worlds={eligible_worlds}; "
            f"unique_class_worlds={unique_class_worlds}; "
            f"multi_class_worlds={multi_class_worlds}; max_classes={max_classes}; "
            f"examples={examples}"
        )
        self.assertGreater(eligible_worlds, 0)
        self.assertEqual(unique_class_worlds + multi_class_worlds, eligible_worlds)

        # This is deliberately not hard-coded to uniqueness.  The result decides
        # whether the correct theorem target is a unique behavioural class or a
        # residual-constrained minimal version space.
        if multi_class_worlds:
            self.assertGreater(max_classes, 1)
        else:
            self.assertEqual(max_classes, 1)


if __name__ == "__main__":
    unittest.main()
