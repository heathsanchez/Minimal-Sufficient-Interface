"""Source-blind finite tests. These are constructed-domain tests, not ARC scores."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'/'arc3_consequence'))
from agent import Transition
from consequence_selection import ConsequenceController, select_consequence, signatures, prediction_score


def obs(v):
    return {'frame':[[[v]]],'levels_completed':0,'state':'NOT_FINISHED','available_actions':[1,2]}


def rows(n=24):
    # Same visual source; the action determines whether the observation changes.
    return [Transition(obs(0),(),1 if i%2==0 else 2,obs(1 if i%2==0 else 0),(0,'NOT_FINISHED')) for i in range(n)]


class ConsequenceSelectionTests(unittest.TestCase):
    def test_discover_predictive_consequence(self):
        result=select_consequence(rows())
        self.assertEqual(result.status,'HELDOUT_PREDICTIVE')
        self.assertEqual(result.candidate.name,'changed')
        self.assertEqual(result.evidence['accuracy'],1.0)
        self.assertLess(result.evidence['baseline'],1.0)

    def test_no_unevidenced_promotion(self):
        self.assertEqual(select_consequence(rows(4)).status,'NO_QUALIFIED_CONSEQUENCE')
        constant=[Transition(obs(0),(),1,obs(0),(0,'NOT_FINISHED')) for _ in range(24)]
        self.assertEqual(select_consequence(constant).status,'NO_QUALIFIED_CONSEQUENCE')

    def test_exact_development_ablation(self):
        warm=ConsequenceController((1,2),enabled=True,retain_scripts=False)
        cold=ConsequenceController((1,2),enabled=False,retain_scripts=False)
        for d in (warm,cold):
            d.records=list(rows())
            d.refresh_intermediate()
        self.assertEqual(warm.intermediate.name,'changed')
        self.assertIsNone(cold.intermediate)
        self.assertEqual(warm.snapshot()['selected_consequence'],'changed')
        self.assertIsNone(cold.snapshot()['selected_consequence'])

    def test_prediction_does_not_use_holdout_to_fit(self):
        data=rows()
        # Reverse the response in the held-out third. A training fit must fail.
        for i in range(16,24):
            r=data[i]
            data[i]=Transition(r.source,r.history,r.action,obs(0 if r.action==1 else 1),r.outcome)
        changed=next(c for c in signatures() if c.name=='changed')
        result=prediction_score(data,changed)
        self.assertEqual(result['accuracy'],0.0)
        self.assertEqual(select_consequence(data).status,'NO_QUALIFIED_CONSEQUENCE')

    def test_failure_does_not_erase_protected_outcome(self):
        d=ConsequenceController((1,2),enabled=True,retain_scripts=False)
        d.records=list(rows())
        d.refresh_intermediate()
        self.assertEqual(d.records[0].outcome,(0,'NOT_FINISHED'))
        self.assertEqual(d.intermediate.evaluate(d.records[0]),True)

if __name__=='__main__':unittest.main()
