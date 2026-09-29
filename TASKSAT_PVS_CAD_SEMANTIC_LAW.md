# TaskSAT × PVS CAD semantic law

## Objective

Use J. Tanner Slagel's verified PVS CAD as an independent real-algebraic oracle for the exact semantic boundary exposed by the TaskSAT bounded-assignment audit.

Pinned evidence:

- TaskSAT: `nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0`
- pvs_cad: `j-tanner-slagel/pvs_cad@8750362e99c2ba0e9a0307dcaa39b9766c562feb`
- PVS: `pvs8.1.2`, Linux x86_64 SHA-256 `5b7d859feff90fc7e566c669a36aaea0254e762c7a723260cf5fd7e1721fcf1b`
- NASALib: `nasa/pvslib@e426f69dc2680ad575491f93c5a51739ec8b25fa`

## Warranted before CAD

The prior executable audit established, for a bounded numeric assignment (a),

[
	ext{Lean/reference}=\operatorname{clamp}_{[\ell,u]}(a),
qquad
	ext{Python/Z3}=a.
]

The minimized TaskSAT witness (R=[0,100], B=[0,10], a=20) is reported `VIOLATED` by the Python/Z3 property checker and evaluates to (10) under the executable Lean assignment/clamp ordering. Re-clamping after assignment flips the property to `HOLDS` and preserves TaskSAT's original numeric-assignment regression.

## The interval-contract fork

Source reconciliation found two incompatible contracts:

- current AST/manual: `range` is a subtype of `bounds`, i.e. (R\subseteq B);
- TaskNetPaper Lean skeleton: `bounds_in_range`, i.e. (B\subseteq R).

The pinned Python well-formedness checker contains no comparison of the two intervals. The executable contract audit on this branch requires both opposite nesting directions to be accepted before it reports `WARRANTED_MISSING_CONTAINMENT_CHECK`.

This means the algebraic observability question is conditional on which contract the authors intend.

## CAD formulation

All submitted formulas are explicit **closed prenex formulas**, matching pvs_cad's declared `cad-direct` interface. Clamp is represented by its graph rather than by an unverified `IF`/min/max wrapper.

### Agreement quotient

For any (y) on the clamp graph,

[
y=a quad\Longleftrightarrowquad \ell\le a\le u.
]

The PVS theorem spells this as the two implications inside the bounds/clamp-graph guard.

### (B\subseteq R) branch

Normalize (R=[-L,W+R_s]), (B=[0,W]), with nonnegative parameters.

CAD separately checks both directions of the exact statement

[
exists a\in R\setminus B
quad\Longleftrightarrowquad
L>0\lor R_s>0.
]

The split into an all-universal theorem and an (orallorallorallexists) theorem keeps each formula prenex.

### (R\subseteq B) branch

Normalize (R=[0,W]), (B=[-L,W+R_s]). CAD checks universally that every range-valid (a) is in the bounds, hence there is no range-valid separator on this assignment-only slice.

### Repair invariant

A (orallorallorallexists) formula checks that a clamp-graph output always exists and lies in the declared bounds.

### Concrete witness

Two one-quantifier closed formulas independently check that (a=20) is range-valid/outside (B=[0,10]) for (R=[0,100]), and that this witness selects the (B\subseteq R) containment branch.

## Promotion rule

Seven `cad-direct` proofs must end in `QED`. Only then are the exact algebraic characterizations **WARRANTED**.

Separately, the TaskSAT contract audit must be green before “no containment direction is enforced” is **WARRANTED**.

The earlier non-prenex CAD draft is **SUPERSEDED** by this formulation; its run is evidence only about the failed experiment path, not about the mathematics.

## Reusable structure

[
	ext{implementation disagreement}
	o
	ext{minimal separator}
	o
	ext{admissibility contract}
	o
	ext{exact observable region}
	o
	ext{independent verified decision}.
]

The key lesson is sharper than “find a bug”: a semantic difference matters only outside the quotient induced by the surrounding admissibility contract, so that contract must be audited too.
