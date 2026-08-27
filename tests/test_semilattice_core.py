from itertools import combinations
import unittest


def partitions(xs):
    """Enumerate set partitions canonically."""
    xs = tuple(xs)
    if not xs:
        yield ()
        return
    first, rest = xs[0], xs[1:]
    for p in partitions(rest):
        # first starts a new block
        yield ((first,),) + p
        # first joins each existing block
        for i in range(len(p)):
            blocks = list(p)
            blocks[i] = tuple(sorted((first,) + blocks[i]))
            yield tuple(sorted(blocks, key=lambda b: b[0]))


def relation_of_partition(p):
    return frozenset((x, y) for block in p for x in block for y in block)


def eq_relations(n):
    seen = set()
    for p in partitions(tuple(range(n))):
        r = relation_of_partition(p)
        if r not in seen:
            seen.add(r)
            yield r


def meet(a, b):
    return a & b


class SemilatticeCompression(unittest.TestCase):
    def test_all_equivalences_on_four_states_form_meet_semilattice(self):
        # Bell(4)=15: exhaustive over every observational quotient on 4 states.
        E = tuple(eq_relations(4))
        self.assertEqual(len(E), 15)
        Eset = set(E)
        top = frozenset((x, y) for x in range(4) for y in range(4))
        self.assertIn(top, Eset)

        # Closure, commutativity, idempotence, top identity.
        for a in E:
            self.assertEqual(meet(a, a), a)
            self.assertEqual(meet(a, top), a)
            for b in E:
                self.assertIn(meet(a, b), Eset)
                self.assertEqual(meet(a, b), meet(b, a))
                for c in E:
                    self.assertEqual(meet(meet(a, b), c), meet(a, meet(b, c)))

    def test_refinement_order_is_exactly_inclusion(self):
        E = tuple(eq_relations(4))
        # In a meet-semilattice, a <= b iff a meet b = a.
        # Here this is exactly set inclusion: finer relations contain fewer pairs.
        for a in E:
            for b in E:
                self.assertEqual(meet(a, b) == a, a <= b)

    def test_every_finite_continuation_family_reduces_to_its_meet(self):
        E = tuple(eq_relations(3))
        self.assertEqual(len(E), 5)
        top = frozenset((x, y) for x in range(3) for y in range(3))

        # Exhaust all ordered three-continuation kernel families (5^3=125)
        # and all retained subsets (8). The induced interface is only the meet.
        for k0 in E:
            for k1 in E:
                for k2 in E:
                    ks = (k0, k1, k2)
                    for mask in range(8):
                        selected = [ks[i] for i in range(3) if mask & (1 << i)]
                        e = top
                        for k in selected:
                            e = meet(e, k)
                        direct = frozenset(
                            (x, y)
                            for x in range(3)
                            for y in range(3)
                            if all((x, y) in k for k in selected)
                        )
                        self.assertEqual(e, direct)

    def test_update_order_and_duplicate_labels_are_semantically_irrelevant(self):
        E = tuple(eq_relations(4))
        top = frozenset((x, y) for x in range(4) for y in range(4))
        for a in E:
            for b in E:
                # Order does not change the interface state.
                self.assertEqual(meet(meet(top, a), b), meet(meet(top, b), a))
                # Reapplying a continuation with the same kernel changes nothing.
                self.assertEqual(meet(meet(top, a), a), a)

    def test_strict_progress_is_strict_meet(self):
        E = tuple(eq_relations(4))
        for state in E:
            for k in E:
                nxt = meet(state, k)
                if nxt != state:
                    self.assertTrue(nxt < state)
                else:
                    self.assertEqual(nxt, state)


if __name__ == "__main__":
    unittest.main()
