import itertools
import unittest
from collections import Counter


N = 4
CONTEXT_COUNT = 1 << N  # every Boolean continuation c : X -> {0,1}
FAMILY_COUNT = 1 << CONTEXT_COUNT  # every protected continuation family C
PAIRS = tuple((i, j) for i in range(N) for j in range(i + 1, N))
ALL_PAIR_BITS = (1 << len(PAIRS)) - 1


def kernel_bits(context):
    """Pair bit is 1 exactly when this continuation cannot distinguish the pair."""
    out = 0
    for bit, (i, j) in enumerate(PAIRS):
        if ((context >> i) & 1) == ((context >> j) & 1):
            out |= 1 << bit
    return out


KERNELS = tuple(kernel_bits(c) for c in range(CONTEXT_COUNT))


def induced_equivalences():
    """E_C = intersection_{c in C} ker(c), for all 2^16 families."""
    eq = [0] * FAMILY_COUNT
    eq[0] = ALL_PAIR_BITS
    for family in range(1, FAMILY_COUNT):
        low = family & -family
        c = low.bit_length() - 1
        eq[family] = eq[family ^ low] & KERNELS[c]
    return tuple(eq)


EQUIV = induced_equivalences()


def representation_kernel(values):
    out = 0
    for bit, (i, j) in enumerate(PAIRS):
        if values[i] == values[j]:
            out |= 1 << bit
    return out


def is_equivalence_relation(bits):
    # Reflexivity is implicit because only off-diagonal unordered pairs are encoded.
    def same(i, j):
        if i == j:
            return True
        if i > j:
            i, j = j, i
        return bool(bits & (1 << PAIRS.index((i, j))))

    for i in range(N):
        for j in range(N):
            for k in range(N):
                if same(i, j) and same(j, k) and not same(i, k):
                    return False
    return True


def direct_meta_signature(family):
    """At the meta-level, a raw observation language is judged only by which pairs it separates."""
    signature = 0
    for bit, (i, j) in enumerate(PAIRS):
        separated = False
        for c in range(CONTEXT_COUNT):
            if family & (1 << c):
                if ((c >> i) & 1) != ((c >> j) & 1):
                    separated = True
                    break
        if separated:
            signature |= 1 << bit
    return signature


class GoldenLawExhaustive(unittest.TestCase):
    def test_all_finite_boolean_worlds_obey_golden_equation(self):
        """Exhaust all 65,536 protected-continuation families on four states."""
        strict_refinements = 0
        inert_additions = 0

        for family, old in enumerate(EQUIV):
            self.assertTrue(is_equivalence_relation(old))
            for c in range(CONTEXT_COUNT):
                # Golden developmental law:
                # E_{C union {c}} = E_C intersection ker(c).
                new = EQUIV[family | (1 << c)]
                self.assertEqual(new, old & KERNELS[c])
                if new == old:
                    inert_additions += 1
                else:
                    strict_refinements += 1
                    # A genuine separator can only remove identifications.
                    self.assertEqual(new & old, new)

        self.assertEqual(strict_refinements + inert_additions, FAMILY_COUNT * CONTEXT_COUNT)
        self.assertEqual(strict_refinements, 11_432)
        self.assertEqual(inert_additions, 1_037_144)

        print(
            "GOLDEN_LAW_EXHAUSTIVE "
            f"worlds={FAMILY_COUNT} transitions={FAMILY_COUNT * CONTEXT_COUNT} "
            f"strict_refinements={strict_refinements} inert={inert_additions}"
        )

    def test_quotient_is_unique_coarsest_sufficient_representation(self):
        """Check the universal property against every 4^4 finite representation map.

        For each distinct consequential equivalence E_C, any representation whose equal
        codes always preserve all protected consequences must have kernel contained in E_C.
        Conversely E_C itself is realizable as a representation kernel. Thus X/E_C is the
        unique coarsest sufficient quotient, up to renaming of quotient labels.
        """
        distinct_equivalences = sorted(set(EQUIV))
        self.assertEqual(len(distinct_equivalences), 15)  # Bell number B_4

        representation_kernels = {
            representation_kernel(values)
            for values in itertools.product(range(N), repeat=N)
        }
        self.assertEqual(len(representation_kernels), 15)

        for e in distinct_equivalences:
            self.assertIn(e, representation_kernels)
            for r in representation_kernels:
                sufficient = (r & ~e) == 0  # r identifies no pair that consequence separates
                if sufficient:
                    self.assertEqual(r & e, r)

            # No strictly coarser sufficient equivalence exists.
            coarser_sufficient = [
                r for r in representation_kernels
                if (r & ~e) == 0 and r != e and (e & ~r) == 0
            ]
            self.assertEqual(coarser_sufficient, [])

        print(
            "MINIMAL_STRUCTURE_EXHAUSTIVE "
            f"raw_worlds={FAMILY_COUNT} behavioural_quotients={len(distinct_equivalences)} "
            f"representation_kernels={len(representation_kernels)}"
        )

    def test_the_law_applies_to_observation_languages_themselves(self):
        """Self-application: make the representations themselves the objects.

        Raw objects are all 65,536 continuation families. Meta-continuations ask only
        whether a family can separate each unordered state pair. The same consequential
        quotient collapses those 65,536 syntactically different languages to exactly the
        15 behavioural equivalence structures they induce.
        """
        class_sizes = Counter()
        for family, e in enumerate(EQUIV):
            meta = direct_meta_signature(family)
            self.assertEqual(meta, (~e) & ALL_PAIR_BITS)
            class_sizes[meta] += 1

        self.assertEqual(len(class_sizes), 15)
        self.assertEqual(sum(class_sizes.values()), FAMILY_COUNT)

        print(
            "SELF_APPLICATION_EXHAUSTIVE "
            f"raw_languages={FAMILY_COUNT} meta_quotient_classes={len(class_sizes)} "
            f"largest_class={max(class_sizes.values())} smallest_class={min(class_sizes.values())}"
        )

    def test_coordinate_names_do_not_matter(self):
        """The induced structure is equivariant under every permutation of the four states."""
        representatives = {}
        for family, e in enumerate(EQUIV):
            representatives.setdefault(e, family)
        self.assertEqual(len(representatives), 15)

        pair_to_bit = {pair: bit for bit, pair in enumerate(PAIRS)}

        def permute_context(c, perm):
            out = 0
            for old_state in range(N):
                value = (c >> old_state) & 1
                new_state = perm[old_state]
                out |= value << new_state
            return out

        def permute_family(family, perm):
            out = 0
            for c in range(CONTEXT_COUNT):
                if family & (1 << c):
                    out |= 1 << permute_context(c, perm)
            return out

        def permute_relation(e, perm):
            out = 0
            for bit, (i, j) in enumerate(PAIRS):
                if e & (1 << bit):
                    a, b = sorted((perm[i], perm[j]))
                    out |= 1 << pair_to_bit[(a, b)]
            return out

        checks = 0
        for e, family in representatives.items():
            for perm in itertools.permutations(range(N)):
                transformed_family = permute_family(family, perm)
                self.assertEqual(EQUIV[transformed_family], permute_relation(e, perm))
                checks += 1

        self.assertEqual(checks, 15 * 24)
        print(f"PRESENTATION_INVARIANCE checks={checks}")


if __name__ == "__main__":
    unittest.main()
