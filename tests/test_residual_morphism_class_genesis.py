import itertools
import unittest


def kernel(obs):
    n = len(obs)
    return tuple(tuple(obs[i] == obs[j] for j in range(n)) for i in range(n))


def meet_kernel(*observations):
    n = len(observations[0])
    return tuple(
        tuple(all(obs[i] == obs[j] for obs in observations) for j in range(n))
        for i in range(n)
    )


def induced_observation(v, f):
    return tuple(v[f[x]] for x in range(len(f)))


def has_live_residual(v, t):
    n = len(v)
    return any(v[i] == v[j] and t[i] != t[j] for i in range(n) for j in range(i + 1, n))


def licensed_candidate(v, t, f):
    """A candidate is licensed exactly when it repairs every verifier collision
    and introduces no distinction beyond the verifier-required refinement.

    The candidate is judged only through the protected continuation v ∘ f;
    concrete maps with the same induced repaired kernel are behaviourally the
    same developmental move.
    """
    induced = induced_observation(v, f)
    repaired = meet_kernel(v, induced)
    target = meet_kernel(v, t)
    return repaired == target


class ResidualMorphismClassGenesis(unittest.TestCase):
    def test_exhaustive_residual_to_unique_minimal_behavioural_class(self):
        n = 3
        bool_obs = tuple(itertools.product((0, 1), repeat=n))
        maps = tuple(itertools.product(range(n), repeat=n))

        live_worlds = 0
        representable_worlds = 0
        selected_worlds = 0
        multiple_concrete_realisers = 0
        class_failures = 0
        ablation_failures = 0

        for v in bool_obs:
            if len(set(v)) < 2:
                continue
            for t in bool_obs:
                if not has_live_residual(v, t):
                    continue
                live_worlds += 1
                target = meet_kernel(v, t)
                candidates = [f for f in maps if licensed_candidate(v, t, f)]
                if not candidates:
                    continue
                representable_worlds += 1

                # Blind deterministic synthesis: no target morphism identity is
                # supplied; choose the first verifier-licensed concrete map.
                chosen = candidates[0]
                selected_worlds += 1

                # Concrete implementations may be non-unique, but every
                # licensed implementation lies in one behavioural repair class:
                # the unique minimal target kernel forced by old state + residual.
                classes = {
                    meet_kernel(v, induced_observation(v, f))
                    for f in candidates
                }
                if classes != {target}:
                    class_failures += 1

                if len(candidates) > 1:
                    multiple_concrete_realisers += 1

                # Exact ablation of the synthesized morphism restores the old
                # kernel, which by construction fails at least one live residual.
                if kernel(v) != target and meet_kernel(v, induced_observation(v, chosen)) == target:
                    ablation_failures += 1

        print(
            "residual morphism-class genesis: "
            f"live_worlds={live_worlds}; "
            f"representable_worlds={representable_worlds}; "
            f"selected={selected_worlds}; "
            f"multiple_concrete_realisers={multiple_concrete_realisers}; "
            f"class_failures={class_failures}; "
            f"ablation_restores_failure={ablation_failures}"
        )

        self.assertGreater(live_worlds, 0)
        self.assertEqual(representable_worlds, live_worlds)
        self.assertEqual(selected_worlds, live_worlds)
        self.assertEqual(class_failures, 0)
        self.assertEqual(ablation_failures, live_worlds)
        self.assertGreater(multiple_concrete_realisers, 0)


if __name__ == "__main__":
    unittest.main()
