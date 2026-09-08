import unittest
import itertools
from dataclasses import replace
from grammar_genesis import *

class GrammarTests(unittest.TestCase):
    def test_exhaustive_operator_tables(self):
        for table in range(16):
            cert = synthesize(TrustedOracle(table))
            if table in unary_functions():
                self.assertIsNone(cert)
            else:
                self.assertEqual(tuple(bit(table, x, y) for x, y in DOMAIN), cert.table)
                state = install(State(), cert, TrustedOracle(table))
                self.assertEqual(evaluate(exact_search(state, table), state), table)

    def test_acquisition_transfer_ablation(self):
        q = qualification(7, 6)
        self.assertEqual(len(q["transfer"].gates), 4)
        self.assertIsNone(exact_search(q["before"], 6))
        self.assertEqual(evaluate(q["transfer"], q["after"]), 6)
        self.assertEqual(q["before"].bound, q["after"].bound)

    def test_forgery_and_dependencies(self):
        o = TrustedOracle(7)
        c = synthesize(o)
        for bad in (replace(c, table=(0,0,0,0)), replace(c, identity="forged"),
                    replace(c, dependencies=("missing",))):
            with self.assertRaises(ValueError):
                install(State(), bad, o)
        with self.assertRaises(ValueError):
            install(install(State(), c, o), c, o)

    def test_budget_and_uncertified_operator(self):
        s = State()
        with self.assertRaises(ValueError):
            exact_search(State(bound=5), 6)
        with self.assertRaises(ValueError):
            evaluate(Program((Gate("unknown",(2,3)),),4), s)
        with self.assertRaises(ValueError):
            evaluate(Program((Gate("not",(99,)),),4), s)

    def test_truth_table_evaluator(self):
        for table in range(16):
            for a,b in itertools.product(range(16),repeat=2):
                expected=sum(bit(table,bit(a,x,y),bit(b,x,y)) << (2*x+y) for x,y in DOMAIN)
                self.assertEqual(gate_mask(table,2,(a,b)),expected)

import json
from pathlib import Path
import grammar_genesis as gg
from verify_grammar_genesis import check as independent_check

ACQUISITION = 7
HELDOUT = 6
BASELINE_SHA256 = "c7209c8dafa1f4fa645c68b0d83a124e156a8f9d8cb968ddcf9a0a91e7813f63"
LEAN_TEMPLATE = Path(__file__).with_name("grammar_genesis_template.lean").read_text()

def lean_table(table):
    return "⟨" + ", ".join("true" if v else "false" for v in table) + "⟩"

def lean_program(p, cert):
    names = {"not": ".not", cert.identity: ".learned"}
    gates = ["⟨" + names[g.op] + ", " + str(g.args[0]) + ", " +
             str(g.args[1] if len(g.args) > 1 else 0) + "⟩" for g in p.gates]
    return "⟨[" + ", ".join(gates) + "], " + str(p.output) + "⟩"

def lean_source():
    q = gg.qualification(ACQUISITION, HELDOUT)
    return (LEAN_TEMPLATE
        .replace("@@LEARNED@@", lean_table(q["certificate"].table))
        .replace("@@ACQUISITION_TABLE@@", lean_table(tuple(gg.bit(ACQUISITION,x,y) for x,y in gg.DOMAIN)))
        .replace("@@HELDOUT_TABLE@@", lean_table(tuple(gg.bit(HELDOUT,x,y) for x,y in gg.DOMAIN)))
        .replace("@@ACQUIRED@@", lean_program(q["acquisition"], q["certificate"]))
        .replace("@@TRANSFERRED@@", lean_program(q["transfer"], q["certificate"])))

def report():
    q = gg.qualification(ACQUISITION, HELDOUT)
    result = gg.result_json(q)
    result["baseline_sha256"] = BASELINE_SHA256
    result["acquisition_table"] = [gg.bit(ACQUISITION,x,y) for x,y in gg.DOMAIN]
    result["heldout_table"] = [gg.bit(HELDOUT,x,y) for x,y in gg.DOMAIN]
    result["lean_sha256"] = __import__("hashlib").sha256(lean_source().encode()).hexdigest()
    return result

class ArtifactTests(unittest.TestCase):
    def test_independent_replay(self):
        r = report()
        self.assertTrue(independent_check(r, r["acquisition_table"], r["heldout_table"]))

    def test_corrupted_artifacts_rejected(self):
        from copy import deepcopy
        r = report()
        for mutate in (
            lambda x: x["certificate"].update(identity="forged"),
            lambda x: x["certificate"].update(table=[0,0,0,0]),
            lambda x: x["transfer"]["gates"][0].update(args=[99,3]),
            lambda x: x["transfer"].update(output=99),
        ):
            bad = deepcopy(r)
            mutate(bad)
            with self.assertRaises(ValueError):
                independent_check(bad, r["acquisition_table"], r["heldout_table"])

    def test_source_replay(self):
        actual = Path("lean/LemmaSynthesis/GrammarGenesis.lean").read_bytes()
        self.assertEqual(actual, lean_source().encode())
        self.assertNotIn(b"\nsorry", actual)
        self.assertNotIn(b"\nadmit", actual)

if __name__ == "__main__":
    unittest.main(verbosity=2)
