import copy
import json
import unittest
from pathlib import Path
import frozen_constructor as C
import composite_residual_repair as R
import verify_composite_repair as V
from run_composite_repair import worlds

ROOT=Path(__file__).resolve().parent

class CompositeRepairQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=C.rows(C.permutations(3),C.permutations(3),3,worlds(20260909)[8][1])
        cls.cert=R.acquire(cls.data)["certificate"]

    def test_frozen_source_blob(self):
        import hashlib
        raw=(ROOT/"frozen_constructor.py").read_bytes()
        self.assertEqual(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),R.SOURCE_BLOB)

    def test_frozen_baseline_reproduces(self):
        old=C.choose_extension_family(self.data)
        self.assertEqual(old,(None,None))
        for name,oracle in (("sequential",lambda f,g,x:f[g[x]]),
                            ("pointwise",lambda f,g,x:min(f[x],g[x])),
                            ("gated",lambda f,g,x:f[x] if x==0 else g[x])):
            data=C.rows(C.permutations(3),C.permutations(3),3,oracle)
            kind,model=C.choose_extension_family(data)
            self.assertIsNotNone(model)

    def test_independent_certificate(self):
        self.assertEqual(V.verify(self.cert,self.data)["status"],"FINITE_CERTIFICATE_PASS")

    def test_source_replay(self):
        self.assertEqual(R.acquire(self.data)["certificate"],self.cert)

    def test_all_saved_certificates(self):
        for p in ROOT.glob("*_certificate.json"):
            e=json.loads(p.with_name(p.name.replace("_certificate.json","_evidence.json")).read_text())
            c=json.loads(p.read_text())
            V.verify(c,e)
            self.assertEqual(R.acquire(e)["certificate"],c)

    def test_missing_labels_rejected(self):
        for data in ([(f,g,x,None) for f,g,x,_ in self.data],
                     self.data[:1]+[(self.data[1][0],self.data[1][1],self.data[1][2],None)]+self.data[2:]):
            self.assertEqual(R.acquire(data)["status"],"insufficient_evidence")

    def test_empty_and_malformed_rejected(self):
        self.assertEqual(R.acquire([])["status"],"insufficient_evidence")
        bad=list(self.data); bad[0]=(bad[0][0],bad[0][1],bad[0][2],9)
        self.assertEqual(R.acquire(bad)["status"],"malformed_evidence")

    def test_partial_evidence_not_certified(self):
        self.assertNotEqual(R.acquire(self.data[:1])["status"],"candidate")

    def test_forged_identity_rejected(self):
        c=copy.deepcopy(self.cert);c["identity"]="0"*64
        with self.assertRaises(AssertionError):V.verify(c,self.data)

    def test_rehashed_wrong_content_rejected(self):
        c=copy.deepcopy(self.cert)
        c["payload"]["table"][0][1]=(c["payload"]["table"][0][1]+1)%3
        c["identity"]=V.sha(c["payload"]);c["source"]=["call",c["identity"]]
        with self.assertRaises(AssertionError):V.verify(c,self.data)

    def test_forged_obstruction_rejected(self):
        c=copy.deepcopy(self.cert);c["obstructions"][0]["witness"]=[0,0]
        with self.assertRaises(AssertionError):V.verify(c,self.data)

    def test_missing_evidence_rejected(self):
        with self.assertRaises(AssertionError):V.verify(self.cert,self.data[:1])

    def test_source_bound_rejected(self):
        c=copy.deepcopy(self.cert);c["source_bound"]=4
        with self.assertRaises(AssertionError):V.verify(c,self.data)

    def test_actual_archive_removal(self):
        s=self.cert["source"];a={self.cert["identity"]:self.cert}
        self.assertIsNotNone(R.execute(s,a,self.data[0]))
        self.assertIsNone(R.execute(s,{},self.data[0]))

    def test_outside_grammar(self):
        oracle=lambda f,g,x:(x+f[g[x]]+g[f[x]])%3
        data=C.rows(C.permutations(3),C.permutations(3),3,oracle)
        r=R.acquire(data)
        self.assertEqual(r["status"],"grammar_insufficiency")

    def test_pair_not_preselected(self):
        specs=[s for s in R.GRAMMAR if s["kind"]=="pair"]
        self.assertEqual(len(specs),14)
        self.assertEqual(len({tuple(map(tuple,s["words"])) for s in specs}),14)
        self.assertEqual(self.cert["payload"]["spec"]["words"],[[0,1],[1,0]])
        self.assertEqual(self.cert["cost"],[3,4])
        self.assertEqual(len(self.cert["obstructions"]),21)

    def test_frozen_and_fresh_results(self):
        result=json.loads((ROOT/"results.json").read_text())
        self.assertEqual(len(result["results"]),24)
        for r in result["results"]:
            self.assertEqual(r["status"],"certified")
            self.assertEqual(r["new_coverage"],2079)
            self.assertEqual(r["new_errors"],0)
            self.assertEqual(r["ablation_coverage"],0)
            self.assertEqual(r["full_domain_errors"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
