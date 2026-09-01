import unittest

from tests.test_difference_test import action_closure, orbit_separator


class DifferenceParametricFamily(unittest.TestCase):
    """Cardinality-only robustness for the deliberately elementary family.

    X_n = Z_n x {0,1}; g(i,b) = (i+1 mod n,b).

    This does NOT test structural variation: the hidden coordinate and its role
    are fixed by construction. It tests only that the same residual-orbit
    constructor is independent of carrier cardinality and that |<g>| = n.
    """

    def test_family_n_2_through_16(self):
        rows = []
        for n in range(2, 17):
            X = tuple(range(2 * n))

            # Encode (phase, hidden) as 2*phase + hidden.
            g = tuple(2 * (((z // 2) + 1) % n) + (z % 2) for z in X)
            x, y = 0, 1

            closure = action_closure(g)
            self.assertEqual(len(closure), n)

            # Old observation exposes phase only. Every old continuation keeps
            # the residual endpoints observationally identical.
            old_obs = lambda z: z // 2
            self.assertTrue(
                all(old_obs(a[x]) == old_obs(a[y]) for a in closure)
            )

            # The unchanged residual-orbit constructor recovers the invariant
            # hidden coordinate up to complement for every n.
            delta = orbit_separator(g, x, y, X)
            self.assertIsNotNone(delta)
            target = tuple(z % 2 for z in X)
            flipped = tuple(1 - b for b in delta)
            self.assertTrue(delta == target or flipped == target)

            rows.append((n, len(X), len(closure)))

        self.assertEqual(rows[0], (2, 4, 2))
        self.assertEqual(rows[-1], (16, 32, 16))
        print(f"DIFFERENCE PARAMETRIC FAMILY PASS rows={rows}")


if __name__ == "__main__":
    unittest.main()
