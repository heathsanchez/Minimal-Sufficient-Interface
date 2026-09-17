from __future__ import annotations
import importlib.util
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
if importlib.util.find_spec('metalogic_arc3.pattern_controller') is None:
 from metalogic_arc3.consequence_controller import ConsequenceController
else:
 from metalogic_arc3.pattern_controller import PatternController as ConsequenceController
from metalogic_arc3.runtime import normalize_frame

def obs(grid,layers=None):
 return dict(frame=layers or [grid],available_actions=[6],levels_completed=0,state='NOT_FINISHED')

def board():
 g=[[0]*20 for _ in range(20)]
 for x,y in [(2,2),(12,12)]:
  for j in range(y,y+3):
   for i in range(x,x+3):g[j][i]=8
 return g

class ConsequenceRepairContracts(unittest.TestCase):
 def test_animation_prefix_does_not_repurchase_same_settled_probe(self):
  p=ConsequenceController((6,),archived_capabilities=());g=board()
  for colour in range(5):
   p.observe_and_choose(obs(g,[[[colour]*20 for _ in range(20)],g]))
  self.assertEqual(len({key[0] for key in p.effects.edges}),1)
 def test_untried_location_outranks_negative_appearance_prior(self):
  p=ConsequenceController((6,),archived_capabilities=());g=board()
  f=obs(g);p._grid=tuple(map(tuple,g));o=normalize_frame(f);c=p._catalog(o)
  self.assertGreaterEqual(len(p._primary),2)
  first=p._primary[0];last=p._primary[-1]
  # Many negative observations at one appearance must not prohibit sampling
  # another untried physical intervention with that appearance.
  p.effects.descriptors[p._descriptor(first)]=[10000,0]
  p._decision_tick=1
  a=p._select_probe(o,c)
  self.assertNotEqual((a.x,a.y),(last.x,last.y), 'known bias monopolised the probes')

if __name__=='__main__':unittest.main(verbosity=2)
