import unittest

from experiments.consequential_atlas_v0 import Atlas, Consequence, Episode, demo


class ConsequentialAtlasV0Tests(unittest.TestCase):
    def test_demo(self):
        result = demo()
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue(result['heldout_transport'])
        self.assertEqual(result['episodes_in_live_memory'], 0)
        self.assertEqual(result['residual_forced_lens'], ('gate_relation',))

    def test_surface_identity_never_becomes_guard(self):
        works = Consequence(1, True)
        atlas = Atlas()
        atlas.append(Episode.make('a', 'surface-A', 'go', {'foo': 1}, works))
        atlas.append(Episode.make('b', 'surface-B', 'go', {'foo': 2}, works))
        self.assertEqual(len(atlas.laws), 1)
        self.assertEqual(atlas.laws[0].guard, ())
        self.assertNotIn('surface', repr(atlas.live()).lower())

    def test_counterexample_creates_residual_not_exception_memory(self):
        works = Consequence(1, True)
        fails = Consequence(0, False)
        atlas = Atlas()
        atlas.append(Episode.make('a', 'A', 'go', {'noise': 1}, works))
        atlas.append(Episode.make('b', 'B', 'go', {'noise': 2}, works))
        atlas.append(Episode.make('c', 'C', 'go', {'noise': 3}, fails))
        self.assertFalse(any(l.consequence == works for l in atlas.laws))
        self.assertTrue(any(r.consequence == works.key for r in atlas.residuals))


if __name__ == '__main__':
    unittest.main()
