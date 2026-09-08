"""Regression and matched finite-world qualification of the existing pieces."""
import copy
import hashlib
import unittest
import unified_qualification as U
import generate_unified_lean as G
import composite_residual_repair as R
import verify_composite_repair as V
import frozen_constructor as C
import closed_feedback_v2 as F

class UnifiedQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle=staticmethod(U.worlds(20260909)[8][1])
        cls.result=U.acquire_world(lambda:U.QueryWorld(cls.oracle))

    def test_01_source_pins(self):
        U.verify_sources()

    def test_02_replay_and_missing_label(self):
        q=(C.permutations(3)[0],C.permutations(3)[1],0)
        archive=F.FeedbackArchive()
        row=U.acquire_label(lambda:U.QueryWorld(self.oracle),q,archive)
        self.assertEqual(row[3],self.oracle(*q))
        self.assertEqual(archive.snapshot()["options"],1)
        with self.assertRaises(ValueError):
            U.acquire_label(lambda:U.QueryWorld(lambda f,g,x:None),q,F.FeedbackArchive())

    def test_03_residual_selects_pair_and_changes_future_search(self):
        r=self.result
        self.assertEqual(r["status"],"FINITE_CERTIFICATE_PASS")
        self.assertEqual(r["certificate"]["payload"]["spec"]["words"],[[0,1],[1,0]])
        self.assertEqual(len(r["certificate"]["obstructions"]),21)
        fixed=U.acquire_world(lambda:U.QueryWorld(self.oracle),feedback=False)
        self.assertNotEqual(r["order"][1],fixed["order"][1])
        self.assertEqual(r["acquisition_actions"],216)

    def test_04_actual_planning_and_archive_ablation(self):
        p=U.evaluate_planning(self.oracle,self.result)
        self.assertGreater(p["planned_wins"],p["baseline_wins"])
        self.assertEqual(p["planned_wins"],p["planned_coverage"])
        self.assertIsNone(U.plan(self.result["source"],{},[(C.all_maps(3)[0],)*2+(0,)],2))

    def test_05_finite_certificate_adversaries(self):
        cert=self.result["certificate"]; data=self.result["evidence"]
        self.assertEqual(V.verify(cert,data)["status"],"FINITE_CERTIFICATE_PASS")
        bad=copy.deepcopy(cert);bad["identity"]="0"*64
        with self.assertRaises(AssertionError):V.verify(bad,data)
        bad=copy.deepcopy(cert)
        bad["payload"]["table"][0][1]=(bad["payload"]["table"][0][1]+1)%3
        bad["identity"]=V.sha(bad["payload"]);bad["source"]=["call",bad["identity"]]
        with self.assertRaises(AssertionError):V.verify(bad,data)
        with self.assertRaises(AssertionError):V.verify(cert,data[:1])
        self.assertNotEqual(R.acquire(data[:1])["status"],"candidate")
        self.assertEqual(R.acquire([(f,g,x,None) for f,g,x,_ in data])["status"],"insufficient_evidence")

    def test_06_ambiguous_and_outside_grammar(self):
        ident=(0,1,2)
        data=[(ident,ident,x,x) for x in range(3)]
        self.assertEqual(R.search(data)["status"],"ambiguous_extension")
        oracle=lambda f,g,x:(x+f[g[x]]+g[f[x]])%3
        data=C.rows(C.permutations(3),C.permutations(3),3,oracle)
        self.assertEqual(R.acquire(data)["status"],"grammar_insufficiency")

    def test_07_actual_gate_source_replay(self):
        source=G.render(self.result["certificate"],self.result["evidence"])
        self.assertIn("promoteIfReplayAdequate",source)
        self.assertIn("forged_empty_replay_refuses",source)
        self.assertIn("stale_stored_replay_does_not_block",source)
        self.assertIn(self.result["certificate"]["identity"],source)
        self.assertEqual(source,G.render(self.result["certificate"],self.result["evidence"]))

    def test_08_original_and_fresh_cohorts(self):
        for seed in (20260909,20260910):
            entries=[U.evaluate_world(name,oracle) for name,oracle in U.worlds(seed)]
            self.assertEqual(sum(e["old_exact"] for e in entries),8)
            self.assertEqual(sum(e["new_exact"] for e in entries),12)
            self.assertEqual(sum(e["errors"] for e in entries),0)
            self.assertTrue(all(e["new_coverage"]==2079 for e in entries))
            self.assertGreater(sum(e["planning"]["planned_wins"] for e in entries),
                               sum(e["planning"]["baseline_wins"] for e in entries))

if __name__=="__main__":
    unittest.main(verbosity=2)
