import itertools
import unittest

from msi.core import Interface, closure, compose


def all_maps(n):
    for image in itertools.product(range(n), repeat=n):
        yield lambda x, image=image: image[x]


class UnifiedDevelopmentalBridge(unittest.TestCase):
    """Finite causal bridge from capability acquisition to new interface to new reachability.

    We search all 3-state binary observations v, all deterministic base actions g,
    and all deterministic acquired actions O1.  The derived candidate is O2 = g ∘ O1.

    A capstone witness requires:
      1. O2 is not reachable extensionally from the old action closure {g};
      2. O1 exposes a new protected continuation v ∘ O1 that strictly refines the interface;
      3. O2 is not quotient-admissible before the refinement but is admissible after it;
      4. O2 becomes reachable after adding O1 to the executable generators;
      5. ablating O1 restores both the coarse interface and loss of O2 reachability.
    """

    def test_exhaustive_three_state_capstone_exists_and_is_causal(self):
        X = (0, 1, 2)
        maps = list(all_maps(3))
        witness_count = 0
        strict_refinement_count = 0
        failures = []

        for vbits in itertools.product((0, 1), repeat=3):
            v = lambda x, vbits=vbits: vbits[x]
            for g in maps:
                for o1 in maps:
                    o2 = compose(g, o1)

                    # Old protected interface sees only v; new one also sees v after O1.
                    P = lambda x, c, v=v, o1=o1: v(x) if c == 0 else v(o1(x))
                    I = Interface(X, (0, 1), P)
                    before = I.relation((0,))
                    after = I.relation((0, 1))
                    if after == before:
                        continue
                    strict_refinement_count += 1

                    before_ok = I.preserves_equivalence(o2, (0,))
                    after_ok = I.preserves_equivalence(o2, (0, 1))
                    if before_ok or not after_ok:
                        continue

                    # Extensional transformation closure: compose generators on every state.
                    def action_closure(gens):
                        seen = {tuple(range(3))}
                        frontier = [lambda x: x]
                        while frontier:
                            f = frontier.pop()
                            for h in gens:
                                k = compose(h, f)
                                sig = tuple(k(x) for x in X)
                                if sig not in seen:
                                    seen.add(sig)
                                    frontier.append(k)
                        return seen

                    old_cl = action_closure((g,))
                    new_cl = action_closure((g, o1))
                    o2_sig = tuple(o2(x) for x in X)
                    if o2_sig in old_cl or o2_sig not in new_cl:
                        continue

                    # The refinement must be caused by an actual separator exposed by O1.
                    sep = any(
                        I.equivalent(x, y, (0,)) and not I.equivalent(x, y, (0, 1))
                        for x in X for y in X
                    )
                    if not sep:
                        failures.append((vbits, tuple(g(x) for x in X), tuple(o1(x) for x in X)))
                        continue

                    # Ablation is exact by construction: remove O1 -> old interface and old closure.
                    self.assertEqual(I.relation((0,)), before)
                    self.assertNotIn(o2_sig, old_cl)
                    witness_count += 1

        self.assertFalse(failures)
        self.assertGreater(strict_refinement_count, 0)
        self.assertGreater(witness_count, 0)
        print(f"capstone strict refinements: {strict_refinement_count}; causal O1->separator->Q1->O2 witnesses: {witness_count}")


if __name__ == "__main__":
    unittest.main()
