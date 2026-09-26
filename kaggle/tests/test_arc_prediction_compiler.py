from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"kaggle"/"src"))
from metalogic_arc3.arc_prediction_compiler import CausalRolePredictor, RoleExample

class CausalRolePredictorContracts(unittest.TestCase):
    def test_deterministic_role_compilation_generalizes_across_hypothesis_names(self):
        train=(
            RoleExample("h1",(1,None,None),("toggle","left"),"x"),
            RoleExample("h1",(2,None,None),("toggle","right"),"y"),
            RoleExample("h2",(1,None,None),("toggle","left"),"x"),
            RoleExample("h2",(2,None,None),("toggle","right"),"y"),
        )
        p=CausalRolePredictor.fit(train)
        self.assertEqual(p.predict(("toggle","left")),"x")
        self.assertEqual(p.predict(("toggle","right")),"y")

    def test_conflicting_role_is_unknown_not_majority_vote(self):
        p=CausalRolePredictor.fit((
            RoleExample("h1",(1,None,None),("guarded","same"),"x"),
            RoleExample("h2",(1,None,None),("guarded","same"),"y"),
        ))
        self.assertIsNone(p.predict(("guarded","same")))
        self.assertIn(("guarded","same"),p.conflicted_roles)

    def test_unseen_role_is_unknown(self):
        p=CausalRolePredictor.fit((RoleExample("h1",(1,None,None),("a",),"x"),))
        self.assertIsNone(p.predict(("b",)))

if __name__=="__main__": unittest.main(verbosity=2)
