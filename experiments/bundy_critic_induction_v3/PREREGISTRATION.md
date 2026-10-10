# V3 — certified induction-repair constructor (preregistered)

Date 2026-10-11. Parent V2 `7d4c040aaaaa10518fd0cc8ad2eccdfc9a13f154` / successful CI 38090889155. This protocol must be committed **before** implementation and before importing the held-out module. Isolate work; no mainline merge, unsolicited contact, or claim of an unconditional breakthrough.

## Research question
Can a critic infer a reusable, universally quantified *accumulator invariant* from a failed induction obligation, rather than merely selecting equality congruence or enumerating existing proof scripts? Does an interpreter-selected invariant transfer across fresh (including externally inspired) recursion functions and carrier/operator types, with source-exact kernel checks and causal ablations?

## Independently authored reference and frozen scope
External programme: David Thrane Christiansen, *Functional Programming in Lean* (Lean FRO), pinned GitHub `leanprover/fp-lean@0abeea545d560a324e2561f7210fbd6ed154fa02`, chapters on tail recursion and proving equivalence. Inspired development/training function: non-tail list reversal versus accumulator reversal. Future corpus **frozen before implementation** includes distinct list sum, list product, reverse-map, and word-list concatenation functions. The latter two are local adaptations. These are *not randomly sampled natural proof tasks*; do not call them that. Frozen source functions are task inputs; the invariant, generator program, and proofs are not in the frozen source module.

## Truth/verification authority
Lean 4.24 kernel independently checks each emitted universal theorem, and an independent executable evaluator exhaustively checks bounded finite instances as a diagnostic. A formal generic fold/action theorem may be used as an independently checked *semantic consequence*, but must not be injected as the generator's preselected answer. The proof-plan compiler is untrusted unless independently verified; generated Lean terms are authoritative only for those exact source obligations.

## Old critic and complete limitation
Old C0: first-order equality, congruence, and fully unbounded premise chaining (qualified V2) plus induction with the auxiliary accumulator **fixed**. It does **not** generalise accumulator parameters or conjecture auxiliary quantified invariants. An old-C0 obstruction must be certified relative to those expressly declared proof programs, not all Lean tactics, all possible induction proofs or all proof critics.

## Lower generator and expected controls
Lower supplied substrate: a typed expression AST over goal-source terms, a generic fold/recursor abstraction, monoid operators supplied by task semantics, abstract-variable introduction, finite extensional discriminator search, induction-plan construction, and independent kernel verification. Candidate invariant forms are enumerated from expression ASTs with the accumulator at either side of the reference computation and a small strictly specified size bound; they must not embed labels such as `reverse`, `sum`, `product`, or a protected task name. Ambiguous or incomplete search => UNKNOWN_CHOICE / UNKNOWN_SEARCH, not arbitrary admission.

Freeze a selected abstract critic AST and its digest before loading the held-out source. Compare: old C0; learned/retained critic; fully equipped schema-aware stateless inference given the same task semantics, generator and proof environment; and exact executable-memory replay (expected tie). Include negative functions for which the proposed invariant is false, candidate-model counterexamples, operator/position mutations, relevant capability deletion, irrelevant deletion, prior-proof preservation, certificate tampering and correct UNKNOWN routing. Include full acquisition, finite checking, kernel calls and future reuse costs separately; no general savings claims if the strong structural baseline ties.

## Promotion thresholds
`WARRANTED_BOUNDED_INDUCTION_CRITIC`: independent Lean source-exact CI for the generated candidate and all emitted proofs; frozen source, no target-specific implementation branches; source-dependence, no false certs, conditional relevance of fresh invariant, and prospective reuse. `BREAKTHROUGH`: additionally genuine new constructor-language semantics beyond supplied abstract/fold/induction interpreter, independent naturally sampled proof problems and a costed advantage over strong schema-aware stateless construction or genuinely distinct protected proof class. The latter is NOT assumed and must not be inferred from merely passing a constructed suite.

Expected initial status: CANDIDATE. Historical V1/V2 qualified positive/negative records remain unchanged, even if this experiment fails.