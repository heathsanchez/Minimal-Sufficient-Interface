import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import austin_completion_development as d
from austin_capability_installation import DevelopmentState, develop as acquire, obligation, law40909
from austin_critical_pair_residual import V, e40909_seed, e11116_seed, promote40909, promote11116

class CompletionDevelopmentTests(unittest.TestCase):
    def test_generic_promotion(self):
        self.assertEqual(d.promote(e40909_seed()), promote40909(e40909_seed(), V('w')))
        self.assertEqual(d.promote(e11116_seed()), promote11116(e11116_seed(), V('w')))

    def test_promoted_residuals(self):
        for seed in (e40909_seed(), e11116_seed()):
            r = d.residual(seed)
            self.assertIn(1, r['pair'][:2])
            self.assertNotEqual(r['left_nf'], r['right_nf'])
            self.assertTrue(all(d.trace(t, r['rules'])[2] for t in (r['left'],r['right'])))

    def test_installation_and_ablation(self):
        parent, evidence = acquire(DevelopmentState(), obligation('E40909', law40909))
        self.assertIsNotNone(evidence)
        before = d.State(parent)
        after, evidence = d.develop(before, e40909_seed())
        self.assertIsNotNone(evidence)
        self.assertTrue(d.verify(after))
        self.assertEqual(after.parent, before.parent)
        self.assertEqual(after.bound, before.bound)
        self.assertEqual(len(d.SOURCE), after.bound)
        self.assertIsNone(d.close(before, e11116_seed()))
        self.assertIsNotNone(d.close(after, e11116_seed()))
        self.assertIsNone(d.close(d.State(after.parent), e11116_seed()))
        with self.assertRaises(ValueError):
            d.verify(d.State(DevelopmentState(), (d.certificate(),)))

    def test_proof_generation(self):
        for name, seed in (('40909',e40909_seed()),('11116',e11116_seed())):
            source, r, equality = d.theorem_source(name,seed)
            self.assertIn('hLeft.symm.trans hRight',source) if d.size(equality[0]) == d.size(r['left_nf']) else self.assertIn('hRight.symm.trans hLeft',source)
            self.assertNotIn('sorry',source)
            self.assertNotIn('admit',source)
        self.assertEqual(d.lean_source(),d.lean_source())

if __name__ == '__main__':
    unittest.main()
