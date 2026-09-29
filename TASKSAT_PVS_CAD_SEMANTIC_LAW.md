# TaskSAT × PVS CAD semantic law

## Current objective

Characterize the observable validity difference caused by TaskSAT's bounded-assignment ordering, then have an independent verified real-closed-field procedure decide the exact boundary.

The protected observation is now:

**Does the post-transition value satisfy TaskSAT's admissible range R?**

This supersedes earlier formulations that asked only whether the raw assignment lay in a chosen interval.

## Warranted implementation divergence

At pinned TaskSAT commit f9d6063b45967a3fea578c47f54806aadaafe1b0:

- Lean/reference output: clamp_B(a)
- current Python/Z3 output after assignment override: a

The earlier executable witness proved the implementations can change a TaskSAT property verdict. A candidate repair that re-clamps after assignment repaired that witness and preserved TaskSAT's original numeric-assignment regression.

## Contract reconciliation

Current AST/manual wording says the admissible range is effectively a subtype of bounds:

**R ⊆ B.**

TaskNetPaper's older schematic Lean semantics records the opposite direction B ⊆ R. The pinned Python well-formedness checker enforces neither direction; the executable containment audit accepts both opposite nestings.

The corpus gives additional evidence for the current R ⊆ B reading: valid examples include cumulative [0,50] bounds [0,100], rate [10,100] bounds [0,100], and tasknet55 [0,90] bounds [0,100].

## Correct observable law

Let Python validity mean a ∈ R. Let Lean/reference validity mean clamp_B(a) ∈ R.

For the current/public R ⊆ B contract, normalize:

- B = [0,W]
- R = [p,W-q]
- p,q >= 0 and p+q <= W

Then:

- if p>0 and q>0, R is strictly interior to B and both implementations have the same range-validity verdict for every assignment;
- if p=0, assignment a=-1 separates them: reference clamps to 0 ∈ R, Python keeps -1 ∉ R;
- if q=0, assignment a=W+1 separates them: reference clamps to W ∈ R, Python keeps W+1 ∉ R.

So the exact assignment-only validity criterion is:

**An observable validity divergence exists iff R touches at least one endpoint of B.**

For the opposite B ⊆ R contract, a separator always exists because raw assignments are not statically restricted to R: choose a=-left-1, which reference clamps to 0 ∈ R while Python leaves below R.

## Contract-compliant executable witness

The old R=[0,100], B=[0,10], a=20 witness belongs to the opposite containment branch and is kept only as lineage.

The decisive current-contract witness is:

- R = [10,100]
- B = [0,100]
- PRE assignment a = 110

This respects R ⊆ B and mirrors existing valid TaskSAT fixtures such as rate [10,100] bounds [0,100].

The CI gate requires:

1. pinned Python/Z3 before repair: UNSAT, because 110 is retained and violates R;
2. disposable re-clamp repair;
3. the same TaskNet after repair: SAT, because 110 clamps to 100 ∈ R.

## Verified CAD boundary

The PVS theory is a closed prenex real theory with one binding per quantifier node, exactly as pvs_cad's cad-prefix requires. It uses cad-direct, so the heuristic witness-search front end is not part of the experiment.

Eight independent formulas check:

1. clamp-output equality quotient;
2. strict-interior R ⊆ B validity agreement;
3. lower-endpoint touching separator;
4. upper-endpoint touching separator;
5. universal separator on the B ⊆ R branch;
6. re-clamp bounds invariant;
7. the contract-compliant R=[10,100], B=[0,100], a=110 witness;
8. the containment direction of the historical witness.

Only 8/8 QED promotes the algebraic characterization to WARRANTED.

## Failed and superseded experiments

- First CAD draft placed existential quantifiers inside Boolean structure. Run 36617796090 returned 4/4 OPEN. Rejected representation: pvs_cad requires a closed prenex input.
- A later draft used the wrong protected observation: raw assignment membership rather than post-transition validity. Superseded by this formulation.
- Another draft grouped multiple variables in a PVS binder. Inspection of cad-prefix showed it accepts exactly one binding per quantifier node. Superseded.

Each failure is retained because it narrowed the verified interface.

## Reusable law emerging

**semantic difference -> protected observation -> admissibility contract -> exact separator region -> independent verified decision**

A raw implementation mismatch is not yet the consequential object. The consequential object is the smallest admissible observation under which the mismatch changes a verified outcome.
