import itertools
import unittest

from msi import Interface


X = (0, 1, 2)
C = (0, 1, 2)


def raw_relation(table, basis):
    """Only primitive used: equality of continuation outcomes."""
    return frozenset(
        (x, y)
        for x in X
        for y in X
        if all(table[x][c] == table[y][c] for c in basis)
    )


def kernel(table, c):
    return frozenset((x, y) for x in X for y in X if table[x][c] == table[y][c])


def intersection_kernel(table, basis):
    rel = frozenset((x, y) for x in X for y in X)
    for c in basis:
        rel = rel & kernel(table, c)
    return rel


def all_tables():
    for bits in itertools.product((0, 1), repeat=9):
        yield tuple(tuple(bits[3 * x + c] for c in C) for x in X)


def all_bases():
    for mask in range(1 << len(C)):
        yield tuple(c for c in C if mask & (1 << c))


class MinimalAlphabetCensus(unittest.TestCase):
    def test_master_equation_reconstructs_entire_interface_relation(self):
        """E_B = intersection_{c in B} ker(c), for all 512 worlds and all 8 bases."""
        checks = 0
        for table in all_tables():
            interface = Interface(X, C, lambda x, c, t=table: t[x][c])
            for basis in all_bases():
                expected = raw_relation(table, basis)
                self.assertEqual(expected, intersection_kernel(table, basis))
                self.assertEqual(expected, interface.relation(basis))
                checks += 1
        self.assertEqual(checks, 4096)

    def test_all_spec_relational_laws_follow_from_master_equation(self):
        """Exhaust L1-L6 directly from equality-kernel semantics; L7 follows by finite strict descent."""
        checks = 0
        for table in all_tables():
            full = raw_relation(table, C)
            for basis in all_bases():
                E = raw_relation(table, basis)

                # L1: equivalence.
                self.assertTrue(all((x, x) in E for x in X))
                self.assertTrue(all(((y, x) in E) for (x, y) in E))
                self.assertTrue(all(((x, z) in E) for x in X for y in X for z in X
                                    if (x, y) in E and (y, z) in E))

                # L2/L3: adding a continuation is intersection/refinement.
                for c in C:
                    E2 = raw_relation(table, tuple(dict.fromkeys(basis + (c,))))
                    self.assertEqual(E2, E & kernel(table, c))
                    self.assertTrue(E2 <= E)

                # L4/L6: residual existence exactly matches inequality from full relation.
                residual_exists = any(
                    (x, y) in E and (x, y) not in full
                    for x in X for y in X
                )
                separator_exists = any(
                    (x, y) in E and table[x][c] != table[y][c]
                    for x in X for y in X for c in C if c not in basis
                )
                self.assertEqual(residual_exists, separator_exists)
                self.assertEqual(not residual_exists, E == full)

                # L5: every witnessed separator strictly refines.
                for x in X:
                    for y in X:
                        if (x, y) not in E:
                            continue
                        for c in C:
                            if c not in basis and table[x][c] != table[y][c]:
                                E2 = E & kernel(table, c)
                                self.assertTrue(E2 < E)
                checks += 1
        self.assertEqual(checks, 4096)

    def test_outcome_names_are_not_ontological(self):
        """Independent bijective relabeling of each continuation's outcomes leaves every E_B unchanged."""
        checks = 0
        for table in all_tables():
            baseline = {basis: raw_relation(table, basis) for basis in all_bases()}
            # For binary outcomes, independently flip/not-flip each continuation.
            for flips in itertools.product((0, 1), repeat=3):
                relabeled = tuple(
                    tuple(table[x][c] ^ flips[c] for c in C)
                    for x in X
                )
                for basis in all_bases():
                    self.assertEqual(baseline[basis], raw_relation(relabeled, basis))
                    checks += 1
        self.assertEqual(checks, 512 * 8 * 8)

    def test_only_equality_pattern_per_continuation_matters(self):
        """The common codomain O can be erased: heterogeneous labels with the same equality fibers induce the same interface."""
        table = (
            (0, "red", (1,)),
            (0, "blue", (1,)),
            (1, "blue", (1,)),
        )
        encoded = (
            ("same-a", 10, False),
            ("same-a", 20, False),
            ("other", 20, False),
        )
        for basis in all_bases():
            self.assertEqual(raw_relation(table, basis), raw_relation(encoded, basis))

    def test_finite_repair_terminates_using_no_extra_state_primitive(self):
        """Residual repair implemented only as repeated kernel intersection terminates at E_C."""
        terminal_checks = 0
        max_steps = 0
        for table in all_tables():
            target = raw_relation(table, C)
            for start in all_bases():
                basis = list(start)
                E = raw_relation(table, basis)
                steps = 0
                while E != target:
                    witness = None
                    for x in X:
                        for y in X:
                            if (x, y) not in E:
                                continue
                            for c in C:
                                if c not in basis and table[x][c] != table[y][c]:
                                    witness = c
                                    break
                            if witness is not None:
                                break
                        if witness is not None:
                            break
                    self.assertIsNotNone(witness)
                    E2 = E & kernel(table, witness)
                    self.assertTrue(E2 < E)
                    basis.append(witness)
                    E = E2
                    steps += 1
                    self.assertLessEqual(steps, len(C) - len(start))
                self.assertEqual(E, target)
                max_steps = max(max_steps, steps)
                terminal_checks += 1
        self.assertEqual(terminal_checks, 4096)
        self.assertLessEqual(max_steps, 3)


if __name__ == "__main__":
    unittest.main()
