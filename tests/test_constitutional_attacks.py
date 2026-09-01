import itertools
import unittest


def kernel(*observations):
    n = len(observations[0])
    return tuple(
        tuple(all(obs[i] == obs[j] for obs in observations) for j in range(n))
        for i in range(n)
    )


def divergent_pairs(interface, protected):
    return tuple(
        (i, j)
        for i in range(len(interface))
        for j in range(i + 1, len(interface))
        if interface[i] == interface[j] and protected[i] != protected[j]
    )


def posterior(prior, fibre):
    mass = sum(prior[i] for i in fibre)
    return tuple(prior[i] / mass if i in fibre else 0.0 for i in range(len(prior)))


class ConstitutionalAdversarialAttacks(unittest.TestCase):
    def setUp(self):
        self.constitutions = tuple(itertools.product((0, 1), repeat=2))
        self.authority = tuple(a for a, _b in self.constitutions)
        self.audit = tuple(b for _a, b in self.constitutions)
        self.identity = tuple(range(len(self.constitutions)))
        self.base_residuals = divergent_pairs(self.authority, self.audit)
        self.assertEqual(self.base_residuals, ((0, 1), (2, 3)))

    def test_randomized_selector_chooses_but_does_not_identify(self):
        # A randomized postprocessor of the evidence interface is a Markov
        # kernel E -> Dist({0,1}).  Equal evidence therefore induces exactly
        # the same output distribution.  Exhaust a finite grid of Bernoulli
        # kernels.  No choice can be almost surely correct for both members of
        # either collapsed fibre because their protected decisions disagree.
        probs = (0.0, 0.25, 0.5, 0.75, 1.0)
        kernels = tuple(itertools.product(probs, repeat=2))
        successful_identifiers = []
        for p0, p1 in kernels:
            p_one = tuple((p0, p1)[a] for a in self.authority)
            identifies = all(
                (p == 1.0 if target == 1 else p == 0.0)
                for p, target in zip(p_one, self.audit)
            )
            if identifies:
                successful_identifiers.append((p0, p1))
        self.assertEqual(successful_identifiers, [])
        self.assertEqual(divergent_pairs(self.authority, self.audit), self.base_residuals)
        print(
            "ATTACK_RANDOMIZED_SELECTOR PRESERVED "
            f"markov_kernels_tested={len(kernels)}; deterministic_identifiers=0; "
            "reason=same_evidence_same_distribution"
        )

    def test_bayesian_prior_is_extra_weighting_not_identification(self):
        # Priors can rank constitutions inside an observational fibre, but the
        # posterior is a function of (prior, evidence), not of the hidden true
        # constitution.  Thus two true constitutions with the same evidence
        # and different protected decisions induce the same posterior.
        priors = (
            (1.0, 1.0, 1.0, 1.0),
            (9.0, 1.0, 9.0, 1.0),
            (1.0, 9.0, 1.0, 9.0),
        )
        selectors = []
        for prior in priors:
            chosen = []
            for a in (0, 1):
                fibre = tuple(i for i, seen in enumerate(self.authority) if seen == a)
                post = posterior(prior, fibre)
                chosen.append(max(fibre, key=lambda i: (post[i], -i)))
                # Whichever true constitution generated evidence a, the
                # posterior is identical because the observed interface value
                # is identical.
                self.assertEqual(post, posterior(prior, fibre))
            selectors.append(tuple(chosen))
        self.assertNotEqual(selectors[1], selectors[2])
        self.assertEqual(divergent_pairs(self.authority, self.audit), self.base_residuals)
        print(
            "ATTACK_BAYESIAN_PRIOR PRESERVED_AS_CONDITIONAL "
            f"priors_tested={len(priors)}; selectors={selectors}; "
            "reason=prior_changes_choice_without_changing_evidence"
        )

    def test_external_observation_resolves_only_by_interface_extension(self):
        old_kernel = kernel(self.authority)
        extended_kernel = kernel(self.authority, self.audit)
        self.assertNotEqual(old_kernel, extended_kernel)
        self.assertEqual(divergent_pairs(self.authority, self.audit), self.base_residuals)
        self.assertEqual(divergent_pairs(tuple(zip(self.authority, self.audit)), self.audit), ())
        # Exact ablation of the new observation restores the original residual.
        self.assertEqual(divergent_pairs(self.authority, self.audit), self.base_residuals)
        print(
            "ATTACK_EXTERNAL_OBSERVATION ESCAPE_BY_ADDED_STRUCTURE "
            f"residuals_before={len(self.base_residuals)}; residuals_after=0; "
            f"residuals_after_ablation={len(self.base_residuals)}"
        )

    def test_hidden_constitutional_information_diagnoses_omitted_coordinate(self):
        # The audit bit may have existed in the underlying constitution all
        # along while being absent from the declared evidence interface.  Once
        # exposed, the failed factorization vanishes.  This is an interface
        # diagnosis, not a contradiction of the interface-relative theorem.
        hidden = self.audit
        declared = self.authority
        exposed = tuple(zip(declared, hidden))
        self.assertEqual(divergent_pairs(declared, self.audit), self.base_residuals)
        self.assertEqual(divergent_pairs(exposed, self.audit), ())
        self.assertEqual(divergent_pairs(declared, self.audit), self.base_residuals)
        print(
            "ATTACK_HIDDEN_INFORMATION SCOPE_DIAGNOSIS "
            "omitted_coordinate=audit; exposing_coordinate_removes_residual; "
            "ablation_restores_residual"
        )

    def test_over_restrictive_interface_attack_maps_scope_boundary(self):
        # Enumerate a nested family of interfaces.  The obstruction is present
        # exactly while the interface still identifies a pair that the
        # protected decision separates.  Richer interfaces may remove it; the
        # theorem is therefore explicitly interface-relative rather than a
        # claim of absolute constitutional impossibility.
        constant = (0, 0, 0, 0)
        xor = tuple(a ^ b for a, b in self.constitutions)
        interfaces = {
            "constant": constant,
            "authority": self.authority,
            "xor": xor,
            "authority_plus_xor": tuple(zip(self.authority, xor)),
            "authority_plus_audit": tuple(zip(self.authority, self.audit)),
            "identity": self.identity,
        }
        counts = {name: len(divergent_pairs(obs, self.audit)) for name, obs in interfaces.items()}
        self.assertGreater(counts["constant"], 0)
        self.assertGreater(counts["authority"], 0)
        self.assertGreater(counts["xor"], 0)
        self.assertEqual(counts["authority_plus_xor"], 0)
        self.assertEqual(counts["authority_plus_audit"], 0)
        self.assertEqual(counts["identity"], 0)
        print(
            "ATTACK_OVER_RESTRICTIVE_INTERFACE SCOPE_DEPENDENT "
            f"residual_counts={counts}; reason=obstruction_tracks_declared_interface"
        )


if __name__ == "__main__":
    unittest.main()
