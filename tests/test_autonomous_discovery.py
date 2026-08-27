import itertools
import unittest

from msi.core import Interface, compose


def all_map_signatures(n):
    return tuple(itertools.product(range(n), repeat=n))


def apply_sig(sig, x):
    return sig[x]


def compose_sig(f, g):
    # f ∘ g
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


class AutonomousDiscovery(unittest.TestCase):
    """Search for O2 without constructing or naming it in advance.

    Candidate language: every deterministic transformation X -> X, in a fixed
    lexicographic order independent of the current world.

    Discovery rule at interface B and executable generator set A:
      choose the lexicographically first candidate h such that
        * h is reachable from A by composition,
        * h is quotient-admissible under B,
        * h is not identity and not one of the supplied primitive generators.

    A developmental witness requires that after acquiring O1 and exposing
    v ∘ O1, this blind search returns a genuinely emergent transformation O2
    that was not in the old executable closure and was quotient-inadmissible
    before refinement. Ablating O1 must remove O2 from both the search result
    and the executable closure.
    """

    def test_autonomous_o2_discovery_after_refinement(self):
        n = 3
        X = tuple(range(n))
        ident = tuple(range(n))
        maps = all_map_signatures(n)

        def admissible(I, h, basis):
            f = lambda x, h=h: h[x]
            return I.preserves_equivalence(f, basis)

        def discover(I, basis, generators):
            cl = action_closure(generators, n)
            primitive = set(generators)
            for h in maps:  # fixed global order: no target O2 supplied
                if h == ident or h in primitive:
                    continue
                if h not in cl:
                    continue
                if admissible(I, h, basis):
                    return h
            return None

        strict_refinements = 0
        autonomous_witnesses = 0
        old_discoveries = 0
        examples = []

        for vbits in itertools.product((0, 1), repeat=n):
            for g in maps:
                old_cl = action_closure((g,), n)
                for o1 in maps:
                    if o1 == ident or o1 == g:
                        continue

                    P = lambda x, c, vbits=vbits, o1=o1: (
                        vbits[x] if c == 0 else vbits[o1[x]]
                    )
                    I = Interface(X, (0, 1), P)

                    before = I.relation((0,))
                    after = I.relation((0, 1))
                    if after == before:
                        continue
                    strict_refinements += 1

                    old_found = discover(I, (0,), (g,))
                    if old_found is not None:
                        old_discoveries += 1

                    new_found = discover(I, (0, 1), (g, o1))
                    if new_found is None:
                        continue

                    # The discovered capability must be genuinely new relative
                    # to the old executable world, rather than merely renamed.
                    if new_found in old_cl:
                        continue
                    if new_found in (ident, g, o1):
                        continue

                    # The interface refinement must matter to its legality.
                    if admissible(I, new_found, (0,)):
                        continue
                    if not admissible(I, new_found, (0, 1)):
                        continue

                    # The new capability must be executable only because O1 was
                    # added to the generator language.
                    new_cl = action_closure((g, o1), n)
                    if new_found not in new_cl:
                        continue
                    if new_found in old_cl:
                        continue

                    # Exact ablation: remove O1 and the blind discovery cannot
                    # recover this capability under the old interface/closure.
                    ablated = discover(I, (0,), (g,))
                    if ablated == new_found or new_found in old_cl:
                        continue

                    autonomous_witnesses += 1
                    if len(examples) < 5:
                        examples.append((vbits, g, o1, new_found, ablated))

        self.assertGreater(strict_refinements, 0)
        self.assertGreater(autonomous_witnesses, 0)
        print(
            "autonomous discovery census: "
            f"strict_refinements={strict_refinements}; "
            f"old_nonprimitive_discoveries={old_discoveries}; "
            f"autonomous_post_refinement_witnesses={autonomous_witnesses}; "
            f"examples={examples}"
        )


if __name__ == "__main__":
    unittest.main()
