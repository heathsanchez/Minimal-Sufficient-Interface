import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from metalogic_arc3.developmental_controller import ProgressMemory
from metalogic_arc3.runtime import ActionToken,normalize_frame

def obs(value):
    return normalize_frame(dict(frame=[[[value]]],levels_completed=0,
        state='NOT_FINISHED',available_actions=[1,2]))

class FrontierCostContracts(unittest.TestCase):
    def test_direct_unknown_probe_does_not_scan_unrelated_state_catalogs(self):
        from metalogic_arc3.residual_exploration import frontier_continuation
        m=ProgressMemory()
        a,b,c=obs(1),obs(2),obs(3)
        m.begin(a); m.observe(a,ActionToken(1),b); m.begin(c)
        calls=[]
        def catalog(value):
            calls.append(value.frame_digest)
            return (ActionToken(1),ActionToken(2))
        decision=frontier_continuation(m,c,catalog)
        self.assertEqual(decision.rank,1)
        self.assertEqual(decision.action.action_id,1)
        self.assertEqual(calls,[c.frame_digest])
