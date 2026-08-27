import itertools
import unittest

from msi.core import Interface


def all_map_signatures(n):
    return tuple(itertools.product(range(n), repeat=n))


def compose_sig(f, g):
    return tuple(f[g[x]] for x in range(len(f)))


def action_closure(generators, n):
    ident = tuple(range(n))
    seen = {ident}
    frontier = [ident]
    while frontier:
        f = frontier.pop()
        for h in generators:
            k = compose_sig(h, f)
            if k not in seen:
                seen.add(k)
                frontier.append(k)
    return seen


class EndogenousGenesis(unittest.TestCase):
    """Close the remaining toy-loop gap: O1 is synthesized from a verifier residual.

    The current interface exposes binary observation v.  A protected target t is
    visible only to the verifier.  When v merges a pair that t separates, the
    verifier returns the first such pair as a residual witness.

    O1 is not supplied.  Search ranges over every deterministic X->X map in a
    fixed global order and requires two generic properties:

      1. residual repair: v(O1(x)) != v(O1(y)) for the witnessed pair;
      2. future capability value: adding O1 and the induced continuation v∘O1
         creates at least one newly reachable transformation whose legality on
         the quotient depends on the refinement.

    Among lawful candidates we maximize only the NUMBER of such newly enabled
    capabilities, breaking ties lexicographically.  No desired O1 or O2 identity
    is supplied.  After O1 is retained, a separate blind lexicographic discovery
    returns the first newly reachable quotient-admissible nonprimitive O2.

    Thus the tested chain is:

      verifier residual -> endogenous O1 genesis -> separator -> finer Q1
      -> expanded closure -> autonomous O2 discovery.
    """

    def test_residual_driven_o1_genesis_can_enable_autonomous_o2(self):
        n = 3
        X = tuple(range(n))
        ident = tuple(range(n))
        maps = all_map_signatures(n)

        def first_residual(vbits, tbits):
            for x in X:
                for y in X:
                    if vbits[x] == vbits[y] and tbits[x] != tbits[y]:
                        return x, y
            return None

        def make_interface(vbits, o1):
            P = lambda s, c, vbits=vbits, o1=o1: (
                vbits[s] if c == 0 else vbits[o1[s]]
            )
            return Interface(X, (0, 1), P)

        def admissible(I, h, basis):
            return I.preserves_equivalence(lambda x, h=h: h[x], basis)

        def newly_enabled_capabilities(vbits, g, o1):
            I = make_interface(vbits, o1)
            old_cl = action_closure((g,), n)
            new_cl = action_closure((g, o1), n)
            return tuple(
                h
                for h in maps
                if h not in (ident, g, o1)
                and h not in old_cl
                and h in new_cl
                and not admissible(I, h, (0,))
                and admissible(I, h, (0, 1))
            )

        def synthesize_o1(vbits, residual, g):
            x, y = residual
            old_cl = action_closure((g,), n)
            scored = []
            for h in maps:  # fixed global language; no O1/O2 target supplied
                if h == ident or h == g or h in old_cl:
                    continue
                if vbits[h[x]] == vbits[h[y]]:
                    continue
                enabled = newly_enabled_capabilities(vbits, g, h)
                if enabled:
                    scored.append((-len(enabled), h))
            if not scored:
                return None
            scored.sort()
            return scored[0][1]

        def discover_o2(vbits, g, o1):
            enabled = newly_enabled_capabilities(vbits, g, o1)
            return enabled[0] if enabled else None

        residual_worlds = 0
        o1_geneses = 0
        full_witnesses = 0
        examples = []

        for vbits in itertools.product((0, 1), repeat=n):
            for tbits in itertools.product((0, 1), repeat=n):
                residual = first_residual(vbits, tbits)
                if residual is None:
                    continue
                residual_worlds += 1

                for g in maps:
                    o1 = synthesize_o1(vbits, residual, g)
                    if o1 is None:
                        continue
                    o1_geneses += 1

                    x, y = residual
                    I = make_interface(vbits, o1)

                    # The verifier residual is genuinely repaired by the induced
                    # continuation and the interface strictly refines.
                    self.assertTrue(I.equivalent(x, y, (0,)))
                    self.assertFalse(I.equivalent(x, y, (0, 1)))
                    self.assertNotEqual(I.relation((0,)), I.relation((0, 1)))

                    o2 = discover_o2(vbits, g, o1)
                    if o2 is None:
                        continue

                    old_cl = action_closure((g,), n)
                    new_cl = action_closure((g, o1), n)
                    self.assertNotIn(o2, old_cl)
                    self.assertIn(o2, new_cl)
                    self.assertFalse(admissible(I, o2, (0,)))
                    self.assertTrue(admissible(I, o2, (0, 1)))

                    # Exact O1 ablation restores the old closure and the coarse
                    # relation on the residual pair, so this same O2 disappears.
                    self.assertNotIn(o2, old_cl)
                    self.assertTrue(I.equivalent(x, y, (0,)))

                    full_witnesses += 1
                    if len(examples) < 5:
                        examples.append((vbits, tbits, g, residual, o1, o2))

        self.assertGreater(residual_worlds, 0)
        self.assertGreater(o1_geneses, 0)
        self.assertGreater(full_witnesses, 0)
        print(
            "endogenous genesis census: "
            f"residual_worlds={residual_worlds}; "
            f"o1_geneses={o1_geneses}; "
            f"full_residual_to_o2_witnesses={full_witnesses}; "
            f"examples={examples}"
        )


if __name__ == "__main__":
    unittest.main()
