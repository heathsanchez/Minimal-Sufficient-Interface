import unittest


def delayed_separator_world(horizon):
    """Two deterministic branches indistinguishable until exactly horizon+1 steps."""
    depth = horizon + 1
    # States are ('a',i) and ('b',i), 0 <= i <= depth.
    states = tuple((branch, i) for branch in ("a", "b") for i in range(depth + 1))

    def step(s):
        branch, i = s
        return (branch, min(i + 1, depth))

    def obs(s):
        branch, i = s
        # Only the terminal A state is observable as 1.
        return int(branch == "a" and i == depth)

    return states, step, obs, ("a", 0), ("b", 0)


def iterate(f, x, n):
    for _ in range(n):
        x = f(x)
    return x


class HorizonBoundary(unittest.TestCase):
    def test_no_fixed_finite_lookahead_is_uniformly_sufficient(self):
        """For every tested horizon H, construct a world first split at H+1.

        This does not challenge the all-futures theorem. It falsifies the stronger
        operational shortcut that a fixed finite context depth can certify global
        behavioural equivalence across arbitrary finite worlds.
        """
        for H in range(0, 21):
            _, step, obs, x, y = delayed_separator_world(H)
            for k in range(H + 1):
                self.assertEqual(obs(iterate(step, x, k)), obs(iterate(step, y, k)))
            self.assertNotEqual(
                obs(iterate(step, x, H + 1)),
                obs(iterate(step, y, H + 1)),
            )

    def test_adaptive_residual_search_finds_the_delayed_separator(self):
        H = 12
        _, step, obs, x, y = delayed_separator_world(H)
        found = None
        for k in range(0, H + 2):
            if obs(iterate(step, x, k)) != obs(iterate(step, y, k)):
                found = k
                break
        self.assertEqual(found, H + 1)


if __name__ == "__main__":
    unittest.main()
