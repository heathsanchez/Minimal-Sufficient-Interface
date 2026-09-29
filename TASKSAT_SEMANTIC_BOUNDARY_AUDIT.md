# TaskSAT semantic-boundary audit V1

## Status

**Reproduced:** `WARRANTED_IMPLEMENTATION_DIVERGENCE` at pinned TaskSAT commit `f9d6063b45967a3fea578c47f54806aadaafe1b0`.

This is a semantic-bridge audit, not a claim that TaskSAT, Lean, Z3, or MEXEC is unsound.

## Current objective

Test whether the executable Lean timeline transition and the Python/Z3 transition preserve the same meaning for the smallest bounded numeric assignment.

## Smallest exact witness

```text
old value = 5
range     = [0, 100]
bounds    = [0, 10]
PRE assignment = 20
delta = 0
```

Executable Lean computes assignment first and then clamps, giving `10`. The pinned Python/Z3 cumulative transition clamps the pre-assignment value and then lets the assignment override that clamp, giving `20`.

For the assignment-only slice the separator is exact:

```text
Lean/reference  = clamp_B(a)
Python/Z3       = a
```

so the two orderings commute exactly when the assigned value `a` already lies inside `B`.

## Runtime reproduction

The audit asks TaskSAT itself to verify:

```text
x : cumulative [0,100] bounds [0,10] = 5
PRE: x = 20
property: always (x <= 10)
```

At the pinned commit TaskSAT reports the property **VIOLATED**. The source-locked reference/executable-Lean transition yields `x = 10`, for which the property holds.

Run evidence: https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/36610083034

## Upstream evidence boundary

- Python/Z3 transition: [`tasknet_smt.py`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/smt/tasknet_smt.py#L1718-L1789) clamps the delta-derived value and then applies `ImpactAssign` as an override.
- Executable Lean transition: [`TaskNetExec/TaskNet/Semantics.lean`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/lean/TaskNetExec/TaskNet/Semantics.lean#L658-L680) applies assignment/addition and then clamps.
- The AST contract says `bounds` is the timeline type and computed values are clamped into it: [`tasknet_ast.py`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/smt/tasknet_ast.py).
- The public tutorial likewise says cumulative values always remain within `bounds`, that the bounds interval ensures clamping, and that tasks may assign values to the timeline: [`tutorial.md`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/website/docs/getting-started/tutorial.md).
- The SMT-encoding prose follows the Python ordering and says assignments override the accumulated/clamped value: [`smt-encoding.md`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/website/docs/theory/smt-encoding.md).

## Causal lineage

The divergence can be localized historically.

Commit [`1b9d81fe`](https://github.com/nasa-jpl/tasksat/commit/1b9d81fe1b127177f871fc3ac19391633c6cf7a0) introduced numeric assignments on 2026-01-06. Its patch explicitly started from the already-clamped delta value and then added assignments as an override. The regression fixture added in that commit assigned `60` into bounds `[0,100]`, exactly a case where both orderings commute, so it could not expose the semantic difference.

The executable Lean semantics file predates that change (its lineage begins in the 2025-12-17 repository import) and still implements assignment/addition followed by clamping. This explains how the two implementations could diverge while ordinary in-bounds tests remained green.

## Candidate repair

The smallest repair consistent with the executable Lean semantics and the public bounds-as-type wording is to re-apply bounds after any value-assignment override on cumulative and rate timelines.

The audit workflow applies this only to a disposable pinned TaskSAT checkout, then:

1. re-runs the minimized property and requires it to become `HOLDS`;
2. runs TaskSAT's existing `tests/test_verifier1.py`, which includes the original numeric-assignment regression.

This repair is a candidate until those gates are green. No upstream source is modified.

## Epistemic ledger

### WARRANTED

- The pinned Python/Z3 and executable Lean implementations use opposite assignment/clamp order.
- The finite algebraic law above exactly characterizes the assignment-only separator.
- TaskSAT itself reproduces the observable property disagreement on the minimized witness.
- The public AST/tutorial semantics say bounds clamp computed timeline values, while the SMT-encoding prose documents the contrary ordering.
- The historical introduction point is the numeric-assignment commit `1b9d81fe`.

### CANDIDATE

- Re-clamping after assignment is the smallest implementation repair consistent with the Lean and user-facing bounds contract.

### UNKNOWN

- Whether TaskSAT's authors intentionally want assignments to escape `bounds` despite the public bounds-as-type wording.
- Whether either ordering exactly matches MEXEC semantics.
- Whether the mismatch affects any deployed JPL tasknet.

### REJECTED

- A prior candidate that rate impacts were one zone late. The dual-rate transition establishes `rate[i+1]` at the boundary before it becomes the left-boundary rate of the following interval.

## Residual

If the candidate repair passes the pinned upstream regression gate, the only consequential residual is specification authority: confirm with TaskSAT/JPL whether value assignments are intended to be clamped by `bounds`.
