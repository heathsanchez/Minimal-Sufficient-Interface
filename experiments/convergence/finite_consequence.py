"""Executable finite instance of AdequacyTester / quotient refinement.

No domain ontology is encoded here. Q and F are caller-supplied functions.
A residual forces E+ = E intersect ker(F). A candidate feature is only a
realization of that obligation, and is never confused with the obligation.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from itertools import combinations
import hashlib, json


def freeze(value):
    if hasattr(value, 'tolist'):
        value = value.tolist()
    if isinstance(value, dict):
        return tuple((k, freeze(v)) for k, v in sorted(value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def witnesses(rows, q, f):
    """Exact finite failed-factorization witnesses, not a heuristic score."""
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[freeze(q(row))].append((i, freeze(f(row))))
    return tuple((group[i][0], group[j][0]) for group in groups.values()
                 for i, j in combinations(range(len(group)), 2)
                 if group[i][1] != group[j][1])


def conflict_count(rows, q, f):
    groups = defaultdict(lambda: defaultdict(int))
    for row in rows:
        groups[freeze(q(row))][freeze(f(row))] += 1
    return sum((sum(v.values()) ** 2 - sum(n*n for n in v.values())) // 2
               for v in groups.values())


def sufficient(rows, q, f):
    return conflict_count(rows, q, f) == 0


def necessary_refinement(q, f):
    return lambda row: (freeze(q(row)), freeze(f(row)))


@dataclass(frozen=True)
class Candidate:
    name: str
    rank: int
    evaluate: object


@dataclass(frozen=True)
class Repair:
    features: tuple
    before: int
    after: int
    status: str
    witness: tuple | None
    evidence_sha256: str
    candidate_count: int
    evaluated_combinations: int
    alternatives: tuple = ()


def synthesize(rows, q, f, candidates, max_features=3, max_combinations=50000):
    """Find a cardinality-minimal sufficient feature set within declared bounds.

    Coarseness is checked extensionally, not inferred from a programmer's rank.
    Among equal-cardinality adequate repairs, prefer fewer induced classes,
    then declared complexity and name. An exhausted bound is not impossibility.
    """
    before = conflict_count(rows, q, f)
    evidence = digest([(freeze(q(r)), freeze(f(r))) for r in rows])
    if not before:
        return Repair((), 0, 0, 'ALREADY_ADEQUATE', None, evidence, 0, 0)
    old = [freeze(q(r)) for r in rows]
    outcomes = [freeze(f(r)) for r in rows]
    pool = []
    seen = set()
    for c in candidates:
        col = tuple(freeze(c.evaluate(r)) for r in rows)
        if len(set(col)) <= 1 or col in seen:
            continue
        seen.add(col)
        pool.append((c, col))
    # A feature that separates no required pair cannot help any conjunction.
    pool = [(c, col) for c, col in pool
            if conflict_count(range(len(rows)), lambda i: (old[i], col[i]), lambda i: outcomes[i]) < before]
    pool.sort(key=lambda x: (x[0].rank, x[0].name))
    checked = 0
    for size in range(1, min(max_features, len(pool)) + 1):
        best = None
        alternatives = []
        for combo in combinations(pool, size):
            if checked >= max_combinations:
                return Repair((), before, before, 'BOUND_EXHAUSTED', witnesses(rows,q,f)[0],
                              evidence, len(pool), checked)
            checked += 1
            cols = tuple(col for _, col in combo)
            keys = [(old[i],) + tuple(col[i] for col in cols) for i in range(len(rows))]
            if conflict_count(range(len(rows)), lambda i: keys[i], lambda i: outcomes[i]):
                continue
            quality = (len(set(keys)), sum(c.rank for c, _ in combo),
                       tuple(c.name for c, _ in combo))
            if best is None or quality < best[0]:
                best = (quality, tuple(c for c, _ in combo), keys)
            alternatives.append((quality, tuple(c.name for c, _ in combo)))
        if best is not None:
            return Repair(best[1], before, 0, 'FINITE_ADEQUATE', None, evidence, len(pool), checked,
                          tuple(names for _, names in sorted(alternatives)[:32]))
    return Repair((), before, before, 'NO_REPAIR_IN_GRAMMAR', witnesses(rows,q,f)[0],
                  evidence, len(pool), checked)


def replay(rows, q, f, repair):
    new_q = lambda r: (freeze(q(r)),) + tuple(freeze(c.evaluate(r)) for c in repair.features)
    return conflict_count(rows, new_q, f)


def lean_certificate(rows, q, f, repair):
    """Generate a data-only certificate checked by the existing Lean tester.

    Values are canonicalized to finite Nat IDs. The checker proves only the
    recorded table, not unobserved environment transitions or causal transfer.
    """
    if replay(rows, q, f, repair):
        raise ValueError('Cannot certify an inadequate repair')
    old = [freeze(q(r)) for r in rows]
    out = [freeze(f(r)) for r in rows]
    new = [(old[i],) + tuple(freeze(c.evaluate(r)) for c in repair.features)
           for i, r in enumerate(rows)]
    def ids(values):
        table = {}; result=[]
        for v in values:
            if v not in table: table[v] = len(table)
            result.append(table[v])
        return result
    qids, fids, nids = ids(old), ids(out), ids(new)
    def lit(xs): return '[' + ', '.join(map(str,xs)) + ']'
    return f'''import LemmaSynthesis.AdequacyTester
namespace FiniteConsequenceCertificate
private def old : List Nat := {lit(qids)}
private def outcome : List Nat := {lit(fids)}
private def repaired : List Nat := {lit(nids)}
private def rowIds : List Nat := List.range {len(rows)}
private def lookup (xs : List Nat) (i : Nat) : Nat := xs[i]!
private theorem finite_replay :
    AdequacyTester.adequacyWitnesses rowIds (lookup repaired) (lookup outcome) = [] := by
  decide
private theorem old_residual :
    AdequacyTester.adequacyWitnesses rowIds (lookup old) (lookup outcome) ≠ [] := by
  decide
end FiniteConsequenceCertificate
''' if repair.before else f'''import LemmaSynthesis.AdequacyTester
namespace FiniteConsequenceCertificate
private def repaired : List Nat := {lit(nids)}
private def outcome : List Nat := {lit(fids)}
private theorem finite_replay : AdequacyTester.adequacyWitnesses (List.range {len(rows)}) (fun i => repaired[i]!) (fun i => outcome[i]!) = [] := by decide
end FiniteConsequenceCertificate
'''
