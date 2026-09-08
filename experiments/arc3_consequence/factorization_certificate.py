"""Lean certificate for finite consequence factorization.

Emit the finite factor map h : repaired-class -> outcome, prove the observed
rows satisfy F = h ∘ Q+, then invoke the reusable Lean theorem that this
factorization rules out all adequacy witnesses.  This avoids quadratic
normalization of the witness list.
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
    return f'''import LemmaSynthesis.ConsequenceFactorization
namespace FiniteConsequenceCertificate
private def old : List Nat := {lit(old_ids)}
private def repaired : List Nat := {lit(repaired_ids)}
private def outcome : List Nat := {lit(outcome_ids)}
private def factor : List Nat := {lit(factor)}
private def rowIds : List Nat := List.range {len(rows)}
private def qPlus (i : Nat) : Nat := repaired[i]!
private def protected (i : Nat) : Nat := outcome[i]!
private def realize (c : Nat) : Nat := factor[c]!

/-- Linear replay obligation: every observed row respects the factor map. -/
private theorem factor_rows : ∀ i ∈ rowIds, protected i = realize (qPlus i) := by
  decide

/-- Therefore the repaired quotient has no finite adequacy witness. -/
private theorem finite_factorization :
    AdequacyTester.adequacyWitnesses rowIds qPlus protected = [] := by
  exact ConsequenceFactorization.no_witnesses_of_factor
    rowIds qPlus protected realize factor_rows
{residual}
end FiniteConsequenceCertificate
'''
