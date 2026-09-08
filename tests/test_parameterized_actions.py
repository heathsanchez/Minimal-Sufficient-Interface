import sys, unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from parameterized_actions import action_catalog, decode

class ActionGroundingTests(unittest.TestCase):
    def frame(self):
        return {'frame':[[[0]*16 for _ in range(16)]], 'levels_completed':0,
                'state':'NOT_FINISHED','available_actions':[1,6]}
    def test_bounded_public_lattice(self):
        space=[SimpleNamespace(value=1,is_simple=lambda:True),SimpleNamespace(value=6,is_simple=lambda:False)]
        actions,unsupported=action_catalog(space,self.frame(),8,20)
        self.assertEqual(unsupported,())
        self.assertEqual(actions[:5],(1,(6,4,4),(6,12,4),(6,4,12),(6,12,12)))
        self.assertEqual(len(actions),20)
        self.assertEqual(len(actions),len(set(actions)))
    def test_unsupported_is_not_silently_promoted(self):
        space=[SimpleNamespace(value=7,is_simple=lambda:False)]
        self.assertEqual(action_catalog(space,self.frame()),((),(7,)))
    def test_bad_bounds_and_image(self):
        with self.assertRaises(ValueError):action_catalog([],self.frame(),0)
        with self.assertRaises(ValueError):action_catalog([],{'frame':[]})
    def test_decode_preserves_coordinates(self):
        action,data=decode((6,12,7))
        self.assertEqual(int(action.value),6)
        self.assertEqual(data,{'x':12,'y':7})
        with self.assertRaises(ValueError):decode((7,1,2))

if __name__=='__main__':unittest.main()
