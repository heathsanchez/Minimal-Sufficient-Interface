# TaskSAT × PVS CAD semantic law

## Objective

Use J. Tanner Slagel's verified PVS CAD as an independent real-algebraic oracle for the exact semantic boundary exposed by the TaskSAT bounded-assignment audit.

Pinned evidence:

- TaskSAT: `nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0`
- pvs_cad: `j-tanner-slagel/pvs_cad@8750362e99c2ba0e9a0307dcaa39b9766c562feb`
- PVS: `pvs8.1.2`, Linux x86_64 SHA-256 `5b7d859feff90fc7e566c669a36aaea0254e762c7a723260cf5fd7e1721fcf1b`
- NASALib: `nasa/pvslib@e426f69dc2680ad575491f93c5a51739ec8b25fa`

## Warranted before CAD

The executable TaskSAT audit established:

[
	ext{Lean/reference}=\operatorname{clamp}_{[\ell,u]}(a),
qquad
	ext{Python/Z3}=a
]

for a bounded numeric assignment (a). The minimized witness (R=[0,100]), (B=[0,10]), (a=20) gives 10 versus 20 and produces an observable TaskSAT property disagreement.

## The interval-contract fork

Source reconciliation found two incompatible contracts:

- AST/manual: (R\subseteq B) — range is effectively a subtype of bounds;
- TaskNetPaper Lean skeleton: (B\subseteq R) — its field is literally `bounds_in_range`.

The pinned Python well-formedness checker compares neither interval against the other. The executable contract audit on this branch accepts both opposite nesting directions, so the implementation itself does not resolve the source conflict.

## Exact CAD questions

The clamp is represented by its polynomial graph. CAD is asked to decide:

1. **Agreement quotient:** on the clamp graph, (y=a) exactly when (a\in B).
2. **If (B\subseteq R):** an admissible separator exists exactly when (R) is strictly wider than (B) on at least one side. The two directions are separate prenex theorems.
3. **If (R\subseteq B):** no range-valid assignment can be outside (B), hence this assignment-only difference is invisible to the range predicate.
4. **Repair invariant:** re-clamping has a bounded output for every assignment.
5. **Concrete witness:** the existing (a=20) witness is outside (B=[0,10]), inside (R=[0,100]), and selects the (B\subseteq R) branch.

## pvs_cad interface boundary

Two earlier drafts are deliberately retained in Git history as failed experiments.

- Draft 1 placed existential quantifiers inside Boolean structure. Run `36617796090` returned all formulas **OPEN**. pvs_cad's `cad-direct` expects a closed prenex formula.
- Draft 2 moved quantifiers to the prefix but grouped several variables in one PVS binder. Inspection of pvs_cad's `cad-prefix` showed that it accepts **exactly one binding per quantifier node**.

This version is therefore the first representation matching the verifier interface exactly: one explicit `FORALL` or `EXISTS` per real variable, followed by a quantifier-free Boolean combination of polynomial sign conditions.

The proof commands use `(cad-direct)`, the verified decision path without the heuristic witness-search front end.

## Promotion rule

Seven `cad-direct` calls must end in `QED`. Only then are the algebraic laws **WARRANTED**.

Separately, the already-green TaskSAT static containment audit promotes:

[
oxed{	ext{Python well-formedness enforces neither }R\subseteq B	ext{ nor }B\subseteq R}
]

to **WARRANTED_MISSING_CONTAINMENT_CHECK**.

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

The key lesson is that a semantic difference matters only outside the quotient induced by the surrounding admissibility contract, and the admissibility contract itself must be verified rather than inferred from prose.
