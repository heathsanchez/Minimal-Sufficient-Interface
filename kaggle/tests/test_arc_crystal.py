import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import unittest
from metalogic_arc3.arc_crystal import ArcCrystal,CapabilityEvidence
class ArcCrystalTests(unittest.TestCase):
 def test_conflict_demotes_to_unknown(self):
  c=ArcCrystal(); r=("toggle",1)
  c.observe(CapabilityEvidence(r,"A","g1")); self.assertEqual(c.predict(r),"A")
  c.observe(CapabilityEvidence(r,"B","g2")); self.assertIsNone(c.predict(r)); self.assertTrue(c.conflicted(r))
 def test_conservative_unknown_charge(self):
  p={("h1","a"):"x",("h2","a"):None,("h3","a"):"y"}
  self.assertEqual(ArcCrystal.conservative_separator(("h1","h2","h3"),("a",),p)[:2],(2,1))
if __name__=="__main__":unittest.main()
