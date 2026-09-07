# E677 order-9 three-Bad strict-surplus exclusion

Date: 2026-09-03

Status: **externally verifier-certified finite consequence**.

## Scope

This note records an exact **order-9** exclusion inside the no-HIT strict-surplus branch of the finite E677 => E255 programme. It is not a proof of the global implication.

Let `B=Bad`. Upstream reductions at frozen external commit

`5a205195a84eec54dbcb2fd766f0b2d1ded1831b`

reduce the order-9 no-HIT, `|B|=3`, strict-extra-`Omega`-root branch to exactly 24 normalized structural top forms.

The external checker is

`tools/e677_order9_no_hit_bad_count_sat.py`

with frozen Git blob

`efe356acd0047eef8ae5645b2cb04ac2a493632d`.

All checks below use PySAT `1.8.dev24` and independent `cadical195` and `glucose42` engines.

## Exact closure

All 24 normalized three-Bad strict-surplus forms are now excluded.

The late forms closed on this branch include:

- form 16: exact canonical/root-product coverage, both engines;
- form 23: 9/9 canonical outcomes and 2/2 symmetry-complete named Good-product representatives UNSAT in both engines;
- form 11: exact canonical and Good-representative coverage in both engines;
- forms 15, 21, 24: exact refinement-aware coverage in both engines;
- form 18: 6/6 canonical outcomes and 4/4 named Good-product representatives UNSAT in both engines, with no SAT or UNKNOWN residual.

The final refinement-aware matrix is GitHub Actions run

`33707685460`

from branch commit

`7015276c986a1b9fa37447748ec4f5f5b70afe9d`.

For form 18 the final verifier marker is

`ORDER9_FORM18_EXACTLY_EXCLUDED_BY_REFINEMENT_IN_TWO_ENGINES`

and, in fact, the final rerun needed no parent-cube refinement: both engines returned direct UNSAT on all six canonical outcomes and all four Good representatives.

Therefore the normalized three-Bad strict-surplus branch is exactly

```text
24/24 closed.
```

## Consequence

Combining this exact closure with the already established order-9 two-Bad and terminal-equality exclusions yields the strengthened finite continuation

```text
order-9 counterexample
  -> HIT
  or
     no HIT,
     |Bad| in {4,5,6,7,8,9},
     Z_(Bad x Bad) > |Bad|.
```

Equivalently, under order 9, no HIT, and strict Omega-root surplus, the `|Bad|=3` case is impossible.

## Boundary

This result does **not** exclude the remaining order-9 branches with `|Bad|>=4`, and it does not prove finite E677 => E255 in all orders. The global size-free frontier remains the simultaneous coloured-renewal / marked G-CROSS network. The next finite branch, if pursued, begins at `|Bad|=4`; finite brute-force enlargement should not replace the size-free structural route without evidence that it has higher information gain.
