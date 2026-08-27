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
    """Close the remaining toy-loop gap: O1 is discovered from a verifier residual.

    The verifier has a protected binary target observation t that is not available
    to the constructor as an intervention.  The current interface sees only v.
    If v merges a pair that t separates, the verifier returns the first such pair
    (x,y) as a residual witness.

    O1 is NOT supplied.  A fixed candidate language (all deterministic X->X maps
    in lexicographic order) is searched for the first transformation h such that
    the already-available protected observation v, after h, separates exactly that
    residual pair: v(h(x)) != v(h(y)).  This is the smallest operational sense in
    which the residual itself induces a new capability proposal.

    After verifier acceptance, h is retained as O1 and v∘O1 becomes a protected
    continuation.  We then run the same blind post-refinement discovery rule used
    in test_autonomous_discovery.py and ask whether a genuinely new O2 appears.

    A full witness therefore realizes:

      verifier residual -> autonomous O1 genesis -> new separator -> finer Q1
      -> expanded executable closure -> autonomous O2 discovery.

    Exact ablation removes O1 and restores both the coarse interface and loss of O2.
    """

    def test_residual_driven_o1_genesis_can_enable_autonomous_o2(self):
        n = 3
        X = tuple(range(n))
        ident = tuple(range(n))
        maps = all_map_signatures(n)

        def relation_for_obs(bits):
            return frozenset((x, y) for x in X for y in X if bits[x] == bits[y])

        def first_residual(vbits, tbits):
            for x in X:
                for y in X:
                    if vbits[x] == vbits[y] and tbits[x] != tbits[y]:
                        return x, y
            return None

        def synthesize_o1(vbits, residual, g):
            # Fixed global candidate order.  The search sees only v, residual pair,
            # and the primitive generator g; it is never given a desired O1 or O2.
            x, y = residual
            old_cl = action_closure((g,), n)
            for h in maps:
                if h == ident or h == g:
                    continue
                # Require genuine capability growth, not rediscovery of old closure.
                if h in old_cl:
                    continue
                if vbits[h[x]] != vbits[h[y]]:
                    return h
            return None

        def admissible(I, h, basis):
            return I.preserves_equivalence(lambda x, h=h: h[x], basis)

        def discover_o2(I, basis, generators):
            cl = action_closure(generators, n)
            primitive = set(generators)
            for h in maps:
                if h == ident or h in primitive:
                    continue
                if h not in cl:
                    continue
                if admissible(I, h, basis):
                    return h
            return None

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

                    # The discovered O1 must itself expose the verifier-requested
                    # distinction using the existing protected observation v.
                    x, y = residual
                    self.assertEqual(vbits[x], vbits[y])
                    self.assertNotEqual(vbits[o1[x]], vbits[o1[y]])

                    P = lambda s, c, vbits=vbits, o1=o1: (
                        vbits[s] if c == 0 else vbits[o1[s]]
                    )
                    I = Interface(X, (0, 1), P)
                    before = I.relation((0,))
                    after = I.relation((0, 1))
                    if after == before:
                        continue

                    # Sanity: the target really witnesses insufficiency of the old
                    # interface, but O1 was synthesized from only the residual pair.
                    target_relation = relation_for_obs(tbits)
                    if (x, y) not in before or (x, y) in target_relation:
                        continue

                    old_cl = action_closure((g,), n)
                    new_cl = action_closure((g, o1), n)
                    o2 = discover_o2(I, (0, 1), (g, o1))
                    if o2 is None:
                        continue
                    if o2 in (ident, g, o1) or o2 in old_cl or o2 not in new_cl:
                        continue

                    # The new interface is causally required for O2's legality.
                    if admissible(I, o2, (0,)):
                        continue
                    if not admissible(I, o2, (0, 1)):
                        continue

                    # Exact ablation: without O1, the same blind search cannot
                    # recover O2 and the residual pair is merged again.
                    ablated = discover_o2(I, (0,), (g,))
                    if ablated == o2 or o2 in old_cl:
                        continue
                    if not I.equivalent(x, y, (0,)):
                        continue

                    full_witnesses += 1
                    if len(examples) < 5:
                        examples.append((vbits, tbits, g, residual, o1, o2, ablated))

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
