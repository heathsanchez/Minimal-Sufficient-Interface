"""Lean certificate for finite consequence factorization.

Instead of enumerating all O(n^2) adequacy-witness pairs, emit the factor map
h : repaired-class -> outcome and check each observed row against h.
"""
from __future__ import annotations
from finite_consequence import freeze, replay


def lean_factorization_certificate(rows, q, f, repair):
    if replay(rows, q, f, repair):
        raise ValueError("Cannot certify an inadequate repair")
    old = [freeze(q(r)) for r in rows]
    outcomes = [freeze(f(r)) for r in rows]
    repaired = [(old[i],) + tuple(freeze(c.evaluate(r)) for c in repair.features)
                for i, r in enumerate(rows)]

    def ids(values):
        table = {}; result = []
        for value in values:
            if value not in table:
                table[value] = len(table)
            result.append(table[value])
        return table, result

    repaired_table, repaired_ids = ids(repaired)
    _, outcome_ids = ids(outcomes)
    factor = [None] * len(repaired_table)
    for rid, oid in zip(repaired_ids, outcome_ids):
        if factor[rid] is None:
            factor[rid] = oid
        elif factor[rid] != oid:
            raise ValueError("Repaired representation does not determine outcome")
    if any(v is None for v in factor):
        raise AssertionError("Non-contiguous repaired-class IDs")

    _, old_ids = ids(old)
    old_to_outcome = {}
    old_witness = None
    for i, (qid, oid) in enumerate(zip(old_ids, outcome_ids)):
        prior = old_to_outcome.get(qid)
        if prior is None:
            old_to_outcome[qid] = (oid, i)
        elif prior[0] != oid:
            old_witness = (prior[1], i)
            break

    def lit(xs): return "[" + ", ".join(map(str, xs)) + "]"
    residual = ""
    if old_witness is not None:
        i, j = old_witness
        residual = f"""
private theorem old_residual :
    old[{i}]! = old[{j}]! ∧ outcome[{i}]! ≠ outcome[{j}]! := by decide
"""
    return f'''import LemmaSynthesis.AdequacyTester
namespace FiniteConsequenceCertificate
private def old : List Nat := {lit(old_ids)}
private def repaired : List Nat := {lit(repaired_ids)}
private def outcome : List Nat := {lit(outcome_ids)}
private def factor : List Nat := {lit(factor)}

/-- The observed consequence factors through the repaired representation. -/
private theorem finite_factorization :
    (repaired.zip outcome).all (fun p => factor[p.1]! == p.2) = true := by
  decide
{residual}
end FiniteConsequenceCertificate
'''
