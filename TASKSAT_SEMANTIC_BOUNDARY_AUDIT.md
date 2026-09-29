# TaskSAT semantic-boundary audit V1

## Status

**Target state after CI:** `WARRANTED_IMPLEMENTATION_DIVERGENCE` at the pinned TaskSAT revision.

This is a semantic-bridge audit, not a claim that TaskSAT, Lean, Z3, or MEXEC is unsound.

Upstream is frozen to:

- repository: `nasa-jpl/tasksat`
- commit: `f9d6063b45967a3fea578c47f54806aadaafe1b0`

## Current objective

Test whether the executable Lean timeline transition and the Python/Z3 transition preserve the same meaning for the smallest bounded numeric assignment.

The protected observation is the value immediately after one PRE assignment on a bounded cumulative timeline.

## Smallest exact witness

```text
old value = 5
range     = [0, 100]
bounds    = [0, 10]
PRE assignment = 20
delta = 0
```

The executable Lean transition computes:

```text
start := assignment if present else old
result := start + delta
new := clamp(result, bounds)
```

therefore the witness ends at `10`.

The pinned Python/Z3 cumulative transition computes:

```text
raw := old + delta
clamped := clamp(raw, bounds)
new := assignment if present else clamped
```

therefore the same witness ends at `20`.

The source-level separator is consequently exact for the assignment-only slice:

```text
Lean/reference  = clamp(a, B)
Python/Z3       = a
```

so the two orderings commute exactly when the assigned value `a` already lies inside `B`.

## Upstream evidence boundary

- Python/Z3 transition: [`tasknet_smt.py`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/smt/tasknet_smt.py#L1718-L1789) clamps the delta-derived value and then applies `ImpactAssign` as an override.
- Executable Lean transition: [`TaskNetExec/TaskNet/Semantics.lean`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/lean/TaskNetExec/TaskNet/Semantics.lean#L658-L680) applies assignment/addition and then clamps.
- The TaskSAT AST contract says `bounds` is the timeline type and computed values are clamped into it: [`tasknet_ast.py`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/smt/tasknet_ast.py).
- The SMT-encoding prose currently follows the Python ordering, so the repository itself contains two semantic descriptions rather than one already-settled contract: [`smt-encoding.md`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/website/docs/theory/smt-encoding.md#L362-L380).

## Executable falsifier

The audit generates this valid TaskSAT fragment:

```text
x : cumulative [0,100] bounds [0,10] = 5
PRE: x = 20
property: always (x <= 10)
```

Under assignment-then-clamp semantics the property holds. Under the pinned Python/Z3 transition the assignment overrides the clamp, so the property is expected to be reported `violated`.

The GitHub Action checks out the exact upstream commit, source-locks both transition shapes, runs the finite commutation test, runs TaskSAT itself, and stores the JSON evidence as an artifact.

## Epistemic ledger

### WARRANTED once the pinned action is green

- The two checked implementations use opposite assignment/clamp order on this slice.
- The algebraic separator is exact: `clamp_B(a) = a` iff `a` is inside `B`.
- The pinned Python/Z3 property checker reproduces the observable consequence on the minimized witness.

### UNKNOWN

- Which ordering the TaskSAT authors intend to be canonical.
- Whether either ordering exactly matches MEXEC semantics.
- Whether the mismatch affects any deployed JPL tasknet.

### REJECTED route

An earlier candidate claimed rate impacts might be one zone late. Inspection of the dual-rate transition rejected that: `rate[i+1]` is established at the boundary before it is used as the left-boundary rate of the following interval.

## Residual

The smallest consequential next question is not another corpus search. It is author-intent resolution:

> Are bounded numeric assignments supposed to be clamped, as the executable Lean semantics and AST/manual contract imply, or may an assignment override the bounds clamp, as the current Python/Z3 encoder and SMT-encoding prose implement?

Whichever answer is intended determines the repair direction and turns this from a semantic-drift witness into either a Python encoder fix or a Lean/specification correction.
