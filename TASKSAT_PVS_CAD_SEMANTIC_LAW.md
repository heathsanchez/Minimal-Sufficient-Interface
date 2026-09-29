# TaskSAT × PVS CAD semantic law

## Current objective

Use J. Tanner Slagel's verified PVS CAD as an independent real-algebraic oracle for the exact semantic boundary exposed by the TaskSAT bounded-assignment audit.

This branch extends `tasksat-semantic-boundary-audit-v1`; it changes neither TaskSAT nor pvs_cad.

Pinned evidence:

- TaskSAT: `nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0`
- pvs_cad: `j-tanner-slagel/pvs_cad@8750362e99c2ba0e9a0307dcaa39b9766c562feb`
- PVS: `pvs8.1.2`, Linux x86_64 asset SHA-256 `5b7d859feff90fc7e566c669a36aaea0254e762c7a723260cf5fd7e1721fcf1b`
- NASALib: `nasa/pvslib@e426f69dc2680ad575491f93c5a51739ec8b25fa`

## What changed after the first CAD launch

The first formulation silently treated TaskSAT's interval contract as (B\subseteq R). A source reconciliation found that the repository itself does not have one interval contract.

### Contract A — public AST/manual

`src/smt/tasknet_ast.py` says:

- `range`: interval a valid schedule must stay within;
- `bounds`: the timeline's type, with computed values clamped into it;
- “`range` is effectively a subtype of `bounds`.”

The public manual says the same thing. This is

[
R\subseteq B.
]

### Contract B — TaskNetPaper Lean skeleton

`src/lean/TaskNetPaper/TaskNet/semantics.lean` explicitly declares

[
B\subseteq R
]

via `bounds_in_range : Rlo ≤ Blo ∧ Bhi ≤ Rhi`.

This file describes itself as a semantics skeleton and contains schematic material, so it is not being treated as stronger authority than the executable validator or current public manual. It is nevertheless direct evidence that the opposite contract exists in the repository.

### Executable Python well-formedness

`src/smt/tasknet_wellformedness.py` contains no comparison of timeline `range` and `bounds`. The executable audit on this branch supplies both opposite nestings to the pinned checker and requires both to be accepted.

Therefore the containment direction is itself part of the semantic residual; it must not be silently chosen.

## Already warranted implementation divergence

For a bounded numeric assignment (a), the prior source-locked executable audit established:

[
	ext{Lean/reference}=\operatorname{clamp}_{[\ell,u]}(a),
qquad
	ext{Python/Z3}=a.
]

The minimized TaskSAT witness (R=[0,100], B=[0,10], a=20) is reported `VIOLATED` by the Python/Z3 property checker and evaluates to (10) under the executable Lean assignment/clamp ordering. The candidate re-clamp repair flips the property to `HOLDS` and preserves TaskSAT's original numeric-assignment regression.

## What CAD now decides

The PVS theory avoids `min`, `max`, and `IF`: clamp is represented by its graph, entirely with polynomial equalities/inequalities.

### 1. Exact agreement quotient

CAD proves or rejects:

[
\operatorname{clamp}_{B}(a)=a
iff
a\in B.
]

This is the exact observational quotient for the assignment-only divergence.

### 2. If (B\subseteq R)

Normalize

[
R=[-L,W+R_s],qquad B=[0,W],
]

where (L,W,R_s\ge0). CAD checks:

[
exists a\in R\setminus B
iff
L>0\lor R_s>0.
]

Thus the drift is observable on a range-valid assignment exactly when the admissible range is strictly wider than the clamping interval.

### 3. If (R\subseteq B)

Normalize

[
R=[0,W],qquad B=[-L,W+R_s].
]

CAD checks:

[
\neg\exists a\in R\setminus B.
]

Under this contract, the assignment/clamp ordering difference cannot be exposed by a range-valid assignment on this slice: the range predicate quotients the two implementations together.

### 4. Repair invariant

CAD checks that re-clamping always returns an output in the declared bounds.

### 5. Concrete witness and contract direction

The original (R=[0,100],B=[0,10],a=20) witness is checked as range-valid/outside-bounds, and a separate formula records that it belongs to the (B\subseteq R) branch rather than (R\subseteq B).

## Promotion rule

Only an external run in which all six PVS formulas finish `QED` under pvs_cad's `(cad)` strategy promotes these algebraic laws to **WARRANTED**.

Separately, only a green TaskSAT static audit that accepts both opposite nestings promotes the missing-containment-check claim to **WARRANTED**.

Until those gates finish:

- TaskSAT assignment/clamp implementation divergence: **WARRANTED**
- candidate re-clamp repair on minimized witness: **WARRANTED_FOR_MINIMIZED_WITNESS**
- interval-contract fork: **WARRANTED_SOURCE_CONFLICT**
- missing containment check: **CANDIDATE**
- exact CAD characterizations: **CANDIDATE**
- intended MEXEC containment/clamping semantics: **UNKNOWN**

## Reusable structure

The experiment now exposes a more general semantic-audit law:

[
	ext{implementation disagreement}
	o
	ext{observation quotient}
	o
	ext{admissibility contract}
	o
	ext{observable disagreement region}.
]

A semantic difference is consequential only where the surrounding admissibility contract does not quotient it away. That contract must itself be audited rather than assumed.
