from __future__ import annotations
import importlib.util,json
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from metalogic_arc3.consequence_controller import ConsequenceController
from metalogic_arc3.pattern_controller import PatternController,repeated_cohort

POSITIONS=[(x,y) for y in range(3) for x in range(3) if (x,y)!=(1,1)]

def scene(active, colours=(4,10), shift=0):
 g=[[0]*36 for _ in range(36)]
 vectors=[[1,0,1,1,0,0,0,1],[0,1,1,0,1,0,1,1],[1,1,0,0,0,1,1,0],list(active)]
 for (ox,oy),bits in zip([(2,2),(18,2),(2,18),(18,18)],vectors):
  for (x,y),value in zip(POSITIONS,bits):
   for dy in range(2):
    for dx in range(2):g[oy+shift+4*y+dy][ox+shift+4*x+dx]=colours[value]
 return dict(frame=[g],levels_completed=0,state='NOT_FINISHED',available_actions=[6])

def solve(cls, target, colours=(4,10), shift=0):
 p=cls((6,),archived_capabilities=());bits=[0]*8
 for steps in range(1,401):
  token=p.observe_and_choose(scene(bits,colours,shift))
  for j,(x,y) in enumerate(POSITIONS):
   if 18+shift+4*x<=token.x<20+shift+4*x and 18+shift+4*y<=token.y<20+shift+4*y:
    bits[j]^=1;break
  if bits==target:
   last=scene(bits,colours,shift);last.update(levels_completed=1,state='WIN');p.observe_terminal(last)
   return steps,p
 return None,p

class PatternAcquisitionContracts(unittest.TestCase):
 def test_unknown_binary_goal_is_acquired_from_live_interventions(self):
  for number in (83,166):
   target=[(number>>i)&1 for i in range(8)]
   steps,p=solve(PatternController,target)
   self.assertIsNotNone(steps)
   self.assertEqual(p.memory.capability_count,1)
 def test_palette_relabeling_and_translation_preserve_acquisition(self):
  target=[(173>>i)&1 for i in range(8)]
  a,_=solve(PatternController,target)
  b,_=solve(PatternController,target,(15,2),2)
  self.assertIsNotNone(a);self.assertIsNotNone(b)
  self.assertEqual(a,b)
 def test_no_editable_cohort_is_admitted_without_intervention_evidence(self):
  self.assertIsNone(repeated_cohort(tuple(map(tuple,scene([0]*8)['frame'][0])),[]))
 def test_pattern_memory_survives_reset_and_canonical_restart(self):
  _,p=solve(PatternController,[(83>>i)&1 for i in range(8)])
  p.reset_episode();saved=p.snapshot_memory()
  q=PatternController((6,),archived_capabilities=());q.restore_memory(saved)
  self.assertEqual(saved,q.snapshot_memory())
  self.assertEqual(p.observe_and_choose(scene([0]*8)),q.observe_and_choose(scene([0]*8)))

if __name__=='__main__':unittest.main(verbosity=2)
