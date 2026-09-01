import itertools
import unittest


def kernel(*observations):
    n = len(observations[0])
    return tuple(
        tuple(all(obs[i] == obs[j] for obs in observations) for j in range(n))
        for i in range(n)
    )


def complement(obs):
    return tuple(1 - x for x in obs)


def xor_obs(a, b):
    return tuple(x ^ y for x, y in zip(a, b))


def expression_cost(target, interface, delta):
    """Frozen tiny implementation language.

    A primitive coordinate costs 1; combining the old interface with the new
    coordinate by XOR costs 2. Binary output relabelling is free because it
    does not change the represented distinction.
    """
    expressions = ((1, interface), (1, delta), (2, xor_obs(interface, delta)))
    for cost, obs in expressions:
        if obs == target or complement(obs) == target:
            return cost
    return None


class ConstitutionalRealizationCensus(unittest.TestCase):
    def test_unique_required_quotient_multiple_operational_realizations(self):
        # Four constitutions carry two fixed semantic coordinates:
        # authority bit a and audit bit b.  The current evidence interface sees
        # only a.  The protected decision requires b.
        constitutions = tuple(itertools.product((0, 1), repeat=2))
        interface = tuple(a for a, _b in constitutions)
        protected = tuple(b for _a, b in constitutions)
        future_xor = tuple(a ^ b for a, b in constitutions)

        old_kernel = kernel(interface)
        required_kernel = kernel(interface, protected)
        self.assertNotEqual(old_kernel, required_kernel)
        self.assertTrue(
            all(required_kernel[i][j] == (i == j) for i in range(4) for j in range(4))
        )

        # Exhaust every Boolean coordinate on the four-constitution universe.
        # A lawful realization is exactly a coordinate whose addition realizes
        # the unique coarsest required quotient.
        all_features = tuple(itertools.product((0, 1), repeat=4))
        realizers = tuple(f for f in all_features if kernel(interface, f) == required_kernel)
        self.assertEqual(len(realizers), 4)

        # Quotient away mere output relabelling delta <-> not delta.  Two
        # realization classes remain: b-like and a XOR b-like.
        unseen = set(realizers)
        orbits = []
        while unseen:
            f = min(unseen)
            orbit = {f, complement(f)}
            unseen -= orbit
            orbits.append(tuple(sorted(orbit)))
        self.assertEqual(len(orbits), 2)

        # They realize exactly the same abstract quotient, but are not
        # operationally equivalent relative to the frozen implementation
        # language.  One makes the protected b decision primitive and XOR
        # derived; the other reverses those costs.  Thus a later protected
        # question distinguishes the realizations without changing E+.
        profiles = {
            (
                expression_cost(protected, interface, orbit[0]),
                expression_cost(future_xor, interface, orbit[0]),
            )
            for orbit in orbits
        }
        self.assertEqual(profiles, {(1, 2), (2, 1)})

        print(
            "CONSTITUTIONAL_REALIZATION_CENSUS PASS "
            f"constitutions={len(constitutions)}; "
            f"all_boolean_features={len(all_features)}; "
            f"lawful_realizers={len(realizers)}; "
            f"relabeling_quotient_classes={len(orbits)}; "
            f"future_cost_profiles={sorted(profiles)}"
        )


if __name__ == "__main__":
    unittest.main()
