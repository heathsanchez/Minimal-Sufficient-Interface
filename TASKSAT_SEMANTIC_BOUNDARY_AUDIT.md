# TaskSAT semantic-boundary audit V1

## Status

**WARRANTED_IMPLEMENTATION_DIVERGENCE** at pinned TaskSAT commit `f9d6063b45967a3fea578c47f54806aadaafe1b0`.

**WARRANTED_FOR_MINIMIZED_WITNESS:** the smallest candidate repair flips the exact counterexample from `VIOLATED` to `HOLDS` in a disposable checkout.

This is a semantic-bridge audit, not a claim that TaskSAT, Lean, Z3, or MEXEC is unsound.

## Smallest exact witness

```text
old value = 5
range     = [0, 100]
bounds    = [0, 10]
PRE assignment = 20
delta = 0
```

Executable Lean computes assignment first and then clamps, giving `10`. The pinned Python/Z3 cumulative transition clamps the pre-assignment value and then lets the assignment override that clamp, giving `20`.

For the assignment-only slice:

```text
Lean/reference  = clamp_B(a)
Python/Z3       = a
```

so the orderings commute exactly iff the assigned value `a` is already inside `B`.

## Runtime reproduction

The source-locked audit asks TaskSAT itself to verify:

```text
x : cumulative [0,100] bounds [0,10] = 5
PRE: x = 20
property: always (x <= 10)
```

Pinned TaskSAT reports **VIOLATED**. The executable-Lean/reference transition yields `x = 10`.

First green reproduction: https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/36610083034

## Upstream evidence

- Python/Z3: [`tasknet_smt.py`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/smt/tasknet_smt.py#L1718-L1789) clamps the delta-derived value, then applies assignment as an override.
- Executable Lean: [`TaskNetExec/TaskNet/Semantics.lean`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/lean/TaskNetExec/TaskNet/Semantics.lean#L658-L680) applies assignment/addition, then clamps.
- AST contract: [`tasknet_ast.py`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/src/smt/tasknet_ast.py) says `bounds` is the timeline type and computed values are clamped into it.
- Public tutorial: [`tutorial.md`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/website/docs/getting-started/tutorial.md) says cumulative values always remain within bounds, bounds ensure clamping, and tasks may assign values.
- SMT encoding prose: [`smt-encoding.md`](https://github.com/nasa-jpl/tasksat/blob/f9d6063b45967a3fea578c47f54806aadaafe1b0/website/docs/theory/smt-encoding.md) follows the Python ordering, so the repository currently contains two incompatible semantic descriptions.

## Causal lineage

Commit [`1b9d81fe`](https://github.com/nasa-jpl/tasksat/commit/1b9d81fe1b127177f871fc3ac19391633c6cf7a0) introduced numeric assignments on 2026-01-06. Its patch explicitly started from the clamped delta value and then installed numeric assignments as an override.

The regression fixture added in the same commit assigned `60` into bounds `[0,100]`. That lies inside the bounds, exactly where both orderings commute, so the test could not distinguish the two semantics.

The executable Lean semantics lineage predates that change and retains assignment/addition followed by clamping.

## Candidate repair experiment

The disposable repair re-applies bounds after any value-assignment override on bounded cumulative and rate timelines.

On run `36610650690`:

- the original pinned encoder reproduced `VIOLATED`;
- after the repair, the same property became `HOLDS`;
- the broad `tests/test_verifier1.py` run reported **26 passed, 1 failed**;
- the sole failure was `test_tasknet11_priority`, whose fixture contains only a state timeline and therefore never executes either modified cumulative/rate branch. Its failure was an expected-schedule inclusion mismatch, not a numeric semantics failure.

The workflow now gates directly on TaskSAT's original numeric-assignment regression `test_tasknet12_assign_numeric` so the repair decision is not contaminated by that unrelated schedule-selection test.

## Epistemic ledger

### WARRANTED

- The two pinned implementations use opposite assignment/clamp order.
- The assignment-only separator law above is exact.
- TaskSAT itself reproduces the property disagreement.
- The user-facing bounds contract and executable Lean agree on clamping, while the current SMT encoder/theory prose use the opposite ordering.
- The divergence traces to the numeric-assignment introduction commit.
- Re-clamping after assignment repairs the minimized witness.

### CANDIDATE

- Re-clamping after assignment is the correct general TaskSAT repair for cumulative and rate value assignments.

### UNKNOWN

- Whether TaskSAT's authors intentionally exempt value assignment from bounds despite the bounds-as-type wording.
- Whether either ordering exactly matches MEXEC semantics.
- Whether any deployed JPL tasknet exercises an out-of-bounds assignment.

### REJECTED

- The earlier hypothesis that rate impacts were one zone late; inspection of the dual-rate transition falsified it.
- Treating the unrelated state-only priority-test failure as evidence against the numeric repair.

## Residual

Once the explicit upstream numeric-assignment regression is green, the cheapest decisive remaining step is specification authority: ask TaskSAT/JPL whether bounded value assignments are intended to clamp. That answer determines whether the Python encoder or the Lean/docs side should change.
