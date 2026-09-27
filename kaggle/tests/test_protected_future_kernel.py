import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import unittest
from metalogic_arc3.protected_future_kernel import ProtectedFutureKernel,context

class ProtectedFutureKernelTests(unittest.TestCase):
 def test_conflict_forces_minimum_consequential_separator(self):
  k=ProtectedFutureKernel()
  k.observe("PROGRESS","p1",context(noise=1,mode="A"))
  k.observe("PROGRESS","p2",context(noise=2,mode="A"))
  k.observe("STUCK","n1",context(noise=1,mode="B"))
  self.assertEqual(len(k.residual_kernel()),1)
  self.assertEqual(k.refine(("noise","mode")),"mode")
  self.assertEqual(k.separators,("mode",))
  self.assertEqual(k.residual_kernel(),())
  self.assertEqual(k.predict(context(noise=99,mode="A")),"PROGRESS")
  self.assertEqual(k.predict(context(noise=99,mode="B")),"STUCK")

 def test_unseparated_conflict_is_obstruction_not_guess(self):
  k=ProtectedFutureKernel(); c=context(kind="CLICK")
  k.observe("PROGRESS","p",c); k.observe("STUCK","n",c)
  self.assertIsNone(k.refine(("kind",)))
  self.assertTrue(k.expressive_obstruction)
  self.assertIsNone(k.predict(c))

 def test_irrelevant_difference_is_not_retained(self):
  k=ProtectedFutureKernel()
  k.observe("PROGRESS","p1",context(texture="red",mode="A"))
  k.observe("PROGRESS","p2",context(texture="blue",mode="A"))
  self.assertEqual(k.separators,())
  self.assertEqual(k.predict(context(texture="green",mode="A")),"PROGRESS")

if __name__=="__main__": unittest.main()
