# TaskSAT × PVS CAD semantic law

## Objective

Turn the bounded-assignment counterexample from the TaskSAT audit into an exact, independently checked algebraic characterization using J. Tanner Slagel's verified PVS CAD.

This branch extends `tasksat-semantic-boundary-audit-v1`; it does not alter TaskSAT or pvs_cad.

Pinned external evidence:

- TaskSAT semantic witness: `nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0`
- pvs_cad: `j-tanner-slagel/pvs_cad@8750362e99c2ba0e9a0307dcaa39b9766c562feb`
- PVS: release `pvs8.1.2`, Linux x86_64 asset SHA-256 `5b7d859feff90fc7e566c669a36aaea0254e762c7a723260cf5fd7e1721fcf1b`
- NASALib: `nasa/pvslib@e426f69dc2680ad575491f93c5a51739ec8b25fa`

## Semantic bridge being checked

The prior executable audit warranted this implementation divergence for a bounded numeric assignment (a):

[
	ext{Lean/reference}=\operatorname{clamp}_{[ell,u]}(a),
qquad
	ext{Python/Z3}=a.
]

Rather than re-encode TaskSAT itself in PVS, this experiment asks the verified real-closed-field decision procedure to characterize the exact observation boundary between those two meanings.

## Exact laws submitted to CAD

### 1. Agreement region

The graph of clamp is encoded relationally, using only real polynomial equalities/inequalities and Boolean connectives.

CAD is asked to prove:

[
\operatorname{clamp}_{[ell,u]}(a)=a
iff
ell\le a\le u
qquad(ell\le u).
]

The PVS theorem uses an existential output variable (y), so this is genuinely the equality of the two output semantics rather than a hand-simplified arithmetic restatement.

### 2. Observable drift region

Translate nested TaskSAT intervals so that

[
R=[-L,W+R_s],qquad B=[0,W],
]

with (L,W,R_sge0). CAD is asked to prove

[
exists ain R\setminus B
iff
L>0 lor R_s>0.
]

So an assignment-clamp semantic disagreement can remain a valid TaskSAT range value exactly when the declared `range` is strictly wider than `bounds` on at least one side.

This is the general law behind the minimized witness; it is no longer a one-off example.

### 3. Repair invariant

CAD is asked to prove that the relational clamp always returns a value in the bounds interval. This is the semantic invariant restored by the candidate "re-clamp after assignment" repair.

### 4. Minimized witness

The existing TaskSAT witness

[
R=[0,100],quad B=[0,10],quad a=20
]

is also checked as a closed formula.

## Epistemic promotion rule

Only a green external run in which all four formulas finish as `QED` under pvs_cad's `(cad)` strategy promotes the general characterization to **WARRANTED**.

Until then:

- TaskSAT implementation divergence: **WARRANTED**
- exact generalized drift law: **CANDIDATE**
- candidate re-clamp repair on minimized witness: **WARRANTED_FOR_MINIMIZED_WITNESS**
- intended MEXEC semantics: **UNKNOWN**

## Why this matters

The resulting pattern is reusable:

[
	ext{two semantic implementations}
	o
	ext{minimal separator}
	o
	ext{exact disagreement region}
	o
	ext{independent verified decision}.
]

The important object is not the bug instance. It is the quotient boundary: the region where competing semantics are observationally identical versus the smallest region that separates them.
