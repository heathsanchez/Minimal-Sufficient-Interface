# TaskSAT × verified PVS CAD — closeout

## Final status

**WARRANTED**, subject to the exact pinned verifier boundary below.

This closeout composes the TaskSAT executable semantic audits with J. Tanner
Slagel's independently verified PVS CAD decision procedure. It does not claim
that TaskSAT as a whole, PVS, Lean, Z3, MEXEC, or pvs_cad is unsound.

Pinned boundary:

- TaskSAT: `nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0`
- pvs_cad: `j-tanner-slagel/pvs_cad@8750362e99c2ba0e9a0307dcaa39b9766c562feb`
- NASALib: `nasa/pvslib@e426f69dc2680ad575491f93c5a51739ec8b25fa`
- PVS: `pvs8.1.2`
- PVS Linux x86_64 asset SHA-256:
  `5b7d859feff90fc7e566c669a36aaea0254e762c7a723260cf5fd7e1721fcf1b`

## 1. Bounded assignment: exact semantic boundary

At the pinned TaskSAT revision, a bounded numeric assignment has two
implemented meanings:

[
L(a)=operatorname{clamp}_{B}(a),
qquad
P(a)=a,
]

where (L) is the executable Lean/reference ordering and (P) is the current
Python/Z3 assignment override.

The raw outputs agree exactly when the assignment already lies inside the
clamp bounds. That law is CAD-QED.

The consequential observation is not raw output equality. TaskSAT validity
also requires the resulting value to lie in its admissible `range` (R).

### Public/current contract: (Rsubseteq B)

Normalize

[
B=[0,W],qquad R=[p,W-q],
]

with

[
Wge0,quad pge0,quad qge0,quad p+qle W.
]

Verified CAD establishes:

- if (p>0) and (q>0), the two transition meanings have the same
  range-validity verdict for **every** assignment;
- if (p=0), (a=-1) is a separator: reference clamps to (0in R), Python
  keeps (-1
otin R);
- if (q=0), (a=W+1) is a separator: reference clamps to (Win R), Python
  keeps (W+1
otin R);
- the cases are exhaustive.

Therefore:

[
oxed{
exists a:;
[operatorname{clamp}_B(a)in R]

e
[ain R]
quadLongleftrightarrowquad
R	ext{ touches at least one endpoint of }B.
}
]

Equivalently in the normalization:

[
oxed{p=0 lor q=0.}
]

This is the final exact assignment-only observable-drift criterion.

### Opposite contract: (Bsubseteq R)

Verified CAD also shows a validity separator always exists when raw
assignments themselves are not statically restricted to (R): taking a value
strictly below the lower range endpoint is enough, because reference clamping
moves it back into (R) while Python leaves it outside.

## 2. Contract-compliant executable witness

The decisive witness under the public (Rsubseteq B) reading is

[
R=[10,100],qquad B=[0,100],qquad a=110.
]

This TaskNet is well-formed at the pinned revision.

Before repair, current Python/Z3 leaves (110), so the schedule is **UNSAT**.

The disposable candidate repair re-applies bounds after value assignment,
mapping (110mapsto100). The same TaskNet becomes **SAT**, and TaskSAT's
original numeric-assignment regression remains green.

Thus the implementation difference is consequential even under the current
public containment contract.

## 3. The containment contract is itself not enforced

The current AST/manual describes `range` as effectively a subtype of
`bounds`, while an older TaskNetPaper Lean semantics skeleton contains the
opposite `bounds_in_range` relation.

The pinned Python well-formedness checker accepts examples in **both**
containment directions. Therefore:

[
oxed{	ext{WARRANTED_MISSING_CONTAINMENT_CHECK}}
]

at this revision.

This does not decide which containment direction MEXEC intends.

## 4. Independent rate-timeline semantic fork

The public manual's own documented example

```tasknet
rate [-5,5] bounds [0,100] = 50 initial_rate = -0.1
```

passes TaskSAT well-formedness but is **UNSAT** under the pinned Python/Z3
encoding. Changing only the first interval to `[0,100]` makes the control
**SAT**.

The implementation therefore treats the first interval as constraining the
timeline VALUE, while the manual explicitly labels that interval **Rate
bounds**.

This is:

[
oxed{	ext{WARRANTED_RATE_INTERVAL_DOCUMENTATION_IMPLEMENTATION_DIVERGENCE}.}
]

Historical inspection localizes the contradiction to upstream commit
`094f61abe00835927278d90c0020654a8dc44da2`, where separate rate state,
`initial_rate`, the SMT changes, and the contradictory manual example were
introduced together.

## 5. CAD evidence

The final gate replays ten CAD-QED obligations on one warm PVS server:

- seven established semantic/repair/witness obligations;
- the two minimized implications replacing the single expensive five-variable
  strict-interior presentation;
- one case-exhaustion theorem proving the endpoint/interior cases cover the
  full public contract.

The failed five-variable formula is preserved as a **performance negative
result**, not as a mathematical counterexample. The two logically equivalent
smaller implications both proved QED.

## 6. What this establishes

The reusable result is stronger than either bug instance.

A raw semantic implementation difference becomes consequential only after
choosing the protected observation and admissibility contract. The exact
research pattern is:

[
oxed{
	ext{semantic implementations}
	o
	ext{minimal separator}
	o
	ext{protected observation}
	o
	ext{admissibility quotient}
	o
	ext{exact separator region}
	o
	ext{independent verified decision}.
}
]

In this case verified CAD did not replace TaskSAT's solver. It independently
certified the boundary at which competing TaskSAT meanings do or do not alter
a valid outcome.

## Remaining authority question

The computational residual is closed by the final gate once green.

The remaining non-computational question is source-of-truth authority:

- What containment relation between `range` and `bounds` is intended?
- On rate timelines, is the first interval a value admissibility range, a rate
  bound, or is the current syntax/documentation conflating two separate
  concepts?
- Are value assignments intended to be clamped before validity is checked?

Those are specification decisions for TaskSAT/MEXEC authors, not unresolved
algebra.
