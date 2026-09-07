# PREREGISTRATION — residual-conditioned parameter binding for constructor genesis

**Status:** FROZEN before implementation.

**Recovery (Step 1).** Existing synthesis machinery is relation-algebra level, with NO parameter binding:
- V4 relational-law synthesis: terminals `{E,O,I,U}`, ops `{converse,∩,∪,\}` — relation-level only.
- V3 coordinate-free refinement: partition/fiber level, no coordinate vocabulary.
- `consequence_compiler.py`: selects declared `realizers`. `CandidateGenesis.lean`: frozen `{head,child0,child1}`.

**Raw substrate.** Terms `T = var V | f T T` over a two-element variable type `V = {vx, vy}`, plus `child0`/`child1` extraction and decidable equality. No order, no named constant.

**Permitted primitive operations.** `child0`, `child1` (structural extraction); `=` (decidable equality); Boolean combinators (the symmetric fragment, already proved closed).

**Permitted parameter-binding operation (the one under test).** `bindFromResidual ρ : T → T → Bool` — binds `z := child0 ρ.1` (an element SUPPLIED BY the residual) and constructs `R(a,b) := (a = z)`. The residual supplies the parameter; it does not supply the completed expression.

**Residual.** `ρ = (f x y, f y x)`; the required separating condition is pair-relative: `R(x,y) ≠ R(y,x)`.

**Candidate grammar / resource bound.** The generator's output is the single constructed predicate `bindFromResidual ρ`; no search, no portfolio enumeration.

**External verifier.** Lean kernel (`kernel.yml`).

**Negative controls.**
- C1 (symmetric-only): no binding — cannot separate (already `GeneratorClosure.symmetric_fragment_blind`).
- C2 (named-answer): `constEval xT` with `xT` hard-coded by the human — separates but is answer-shaped.
- C3 (residual-shuffled): `bindFromResidual (t2, t1)` must bind the OTHER element (`yT`), proving the output is genuinely parameter-bound, not a hidden constant.
- C4 (ablation): removing `child0` extraction removes the binding source, restoring the obstruction.

**What counts as construction / selection / failure.** Construction = the predicate is produced by `bindFromResidual` from the residual (C3 proves it is residual-conditioned). Selection = the predicate is named (C2). Failure = no separator is constructible (C1, C4).

**Claim boundary.** Positive = the generator constructs the separator via generic equality + residual-supplied parameter, no order, no named constant. It does NOT claim a globally weakest substrate, nor unrestricted primitive invention — the binding operation is a *declared* generic operation, and the residual supplies the parameter.
