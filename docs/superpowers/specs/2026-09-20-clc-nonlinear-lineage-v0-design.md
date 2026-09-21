# CLC Nonlinear Lineage V0 — Design Specification

**Status:** Draft for user review  
**Source contract:** `Certified_Lineage_Calculus_V1.docx`  
**Repository:** `heathsanchez/Minimal-Sufficient-Interface`  
**Feature branch:** `clc-nonlinear-lineage-v0`  
**Base branch:** `qck-v1-documentation` at `baef39cd7b32c860e2d7aa80a95f3826b8a52738`

## 1. Purpose

CLC Nonlinear Lineage V0 is the smallest finite Lean development intended to prove one central statement:

> A certified projection can collapse inactive historical node distinctions without removing any declared protected answer along a compatible future development.

The formal capstone is query-relative and finite. Let `C` be a closed certified nonlinear lineage, `q` a structurally admissible continuation-safe projection, `E` a finite source-certified quotient-compatible event trace, and `Q` a query in the declared protected language. V0 must prove:

\[
\operatorname{Ans}_Q(\operatorname{GrowSource}(C,E))
=
\operatorname{Ans}_Q
  (\operatorname{GrowProjected}(\operatorname{Project}(q,C),
    \operatorname{ProjectTrace}(q,C,E))).
\]

The result is not obtained by defining admissibility as equality of all query answers. Admissibility is stated using local structural laws—typed and ranked fibre coherence, continuation-safe merging, one-step path lifting, base-support aggregation, rank-local support-rule commutation, and event commutation. Query preservation, closure commutation, and the finite-trace theorem are derived from those laws.

## 2. Why this host and architecture

The existing `qcklean/` project already pins Lean `v4.35.0-rc2` and Mathlib commit `44ba35c6daa9d69aff8fed9fff9bbde17ded774d`. `QCKCore.lean` already proves context-stable quotienting, all-word substitution, operation descent, and explicit defects for the qualified linear kernel. V0 extends that proof repository without modifying the frozen QCK theorem surface.

The `realitygraph` repository remains the runtime home for causal ledgers and developmental control, but it does not currently contain a Lean project. The first mechanization therefore lives beside QCK and exports a small boundary suitable for a later RealityGraph adapter.

V0 uses a finite structural model rather than forcing nonlinear occurrence graphs into the existing linear-algebraic QCK representation. A later bridge may instantiate the discrete continuation-safe relation from a QCK certificate. V0 does not redefine or compete with QCK's frozen linear semantics.

## 3. Scope

V0 includes:

1. a trivalent information order;
2. finite state–test forms;
3. strict and developmental certified transports;
4. identity, composition, associativity, and decisive-verdict preservation;
5. continuation-safe equivalence and forward congruence;
6. finite typed occurrence hypergraphs with nonlinear hyperedges;
7. explicit dependency masks and conjunctive parent support;
8. minimal alternative-support antichains, live tokens, and irrevocable revocation identifiers;
9. a four-constructor protected query language;
10. structural quotient admissibility and query-by-query preservation;
11. finite insertion/revocation reclosure and Flash-versus-batch exactness;
12. finite event-list growth and the grow–dissolve theorem;
13. an executable negative fixture for the spurious quotient-path counterexample.

V0 deliberately excludes:

- cryptographic algorithms, clocks, delegation chains, and real-world authority;
- empirical truth or complete real-world provenance;
- unrestricted generation of fresh identifier types at runtime;
- arbitrary cyclic proof dependencies;
- arbitrary factorization of whole-boundary tests into node-local component tests;
- infinite traces, final coalgebras, fairness, and eternal-productivity theorems;
- approximate, probabilistic, or nondeterministic evaluators;
- a universal query-preservation claim;
- complexity claims stronger than finite termination;
- automatic discovery of the quotient or consequence contract.

## 4. Finite model boundary

Each executable model fixes finite types `FormCode`, `NodeId`, `EdgeId`, `Token`, and `CertId`, all equipped with `Fintype` and `DecidableEq`. Events activate reserved identifiers or update support and liveness fields inside these finite universes. They do not change the universe types or mutate an activated node payload or edge occurrence.

This bounded-universe choice makes checking, exhaustive fixtures, event-list execution, and closure iteration total. It is a V0 engineering boundary, not a claim that development is globally finite.

The active occurrence graph is acyclic in V0. Each node has a natural-number rank, and every dependency selected by an active hyperedge goes from a lower rank to a higher rank. Nonlinearity means one-to-many, many-to-one, and many-to-many incidence; it does not require cycles. Cyclic occurrence semantics are deferred.

The transport-authority snapshot `Ωauth` is fixed during one V0 trace. The lineage's support-token snapshot `σ` evolves under enablement and revocation events. V0 revocation ranges over `Token`, not `CertId`. Revoking an occurrence token changes present warrant, but it does not retroactively erase the historical edge or invalidate the proof that its transport was lawful when activated.

## 5. Verdicts, forms, and transports

### 5.1 Verdict order

`Verdict` has exactly three constructors:

```lean
inductive Verdict
  | unknown
  | eq
  | dist
```

The information order is flat: `unknown ≤ eq`, `unknown ≤ dist`, and each verdict is below itself. `eq` and `dist` are incomparable. V0 proves reflexivity, antisymmetry, transitivity, and that `unknown` is least.

`Decisive v` means `v = eq ∨ v = dist`. The primary order lemma states that if `v` is decisive and `v ≤ w`, then `w = v`.

### 5.2 Finite forms

A `Form` contains finite state and test types, decidable equality, a Boolean protected-test predicate, and a total evaluator:

```lean
structure Form where
  State : Type
  Test : Type
  stateFinite : Fintype State
  testFinite : Fintype Test
  decState : DecidableEq State
  decTest : DecidableEq Test
  protected : Test → Bool
  eval : State → Test → Verdict
```

`Protected A` is the subtype of tests whose predicate is `true`.

A transport is **strict** when evaluation after transport equals evaluation after pullback for every target test. It is **developmental** when it satisfies only the information-refinement law below. Every strict transport is developmental; V0 permits developmental transports so that `unknown` may refine to a decisive verdict.

### 5.3 Transport data and verification

For forms `A` and `B`, `TransportData A B` contains:

- `mapState : A.State → B.State`;
- `pullTest : B.Test → A.Test`;
- `liftProtected : Protected A → Protected B`;
- proof that every protected target test pulls back to a protected source test;
- the refinement law `A.eval x (pullTest d) ≤ B.eval (mapState x) d`;
- the split law `pullTest (liftProtected p) = p`;
- inspectable certificate data.

`VerifiedTransport Ωauth A B` extends this runtime data with erased proofs that the authority-snapshot checker accepts the certificate and that the certificate is live at `Ωauth`.

The V0 snapshot interface supplies canonical identity-certificate data, certificate composition with checker/liveness closure laws, and a declared semantic certificate equality `CertEq`. `CertEq` is an equivalence, acceptance and liveness respect it, composition is congruent under it, and the identity/associativity laws hold under it. This is an abstract authority boundary, not a cryptographic implementation or a requirement that certificate bytes be literally equal.

`TransportEq a b` is the declared equality for verified transports. It requires pointwise equality of `mapState` and `pullTest`, equality of the underlying lifted protected-test values, and `CertEq a.cert b.cert`. Proof fields and raw certificate representation are not compared by Lean structure equality.

V0 defines identity and composition and proves:

- left and right identity under `TransportEq`;
- associativity under `TransportEq`;
- preservation of protected decisive verdicts;
- closure of verification under identity and composition.

## 6. Continuation-safe equivalence

For a fixed authority snapshot `Ωauth`, form `A`, and states `x y : A.State`, define:

```lean
ContinuationSafe Ωauth A x y :=
  ∀ (B : Form) (a : VerifiedTransport Ωauth A B) (p : Protected B),
    B.eval (a.mapState x) p = B.eval (a.mapState y) p
```

Because identity is a verified transport, this relation implies immediate protected agreement. V0 proves that it is an equivalence relation.

The crucial right-congruence theorem is:

```lean
theorem continuationSafe_map
    (a : VerifiedTransport Ωauth A B)
    (hxy : ContinuationSafe Ωauth A x y) :
    ContinuationSafe Ωauth B (a.mapState x) (a.mapState y)
```

The proof composes an arbitrary future transport out of `B` with `a` and applies `hxy`. This is the formal QCK/CLC bridge used by quotient merge certificates.

`ProtectedReduct A` keeps `A.State` but uses `Protected A` as its entire test type, so every reduct test is protected. Immediate protected agreement therefore makes observation well defined on the semantic quotient type `Quotient (ContinuationSafe Ωauth A)`. V0 defines that observation, the induced quotient action of every verified transport, and the naturality square. It does **not** package this generally noncomputable semantic quotient as a finite executable `Form`, and it does not claim that arbitrary unprotected tests descend. Graph admissibility carries a proof of `ContinuationSafe`; V0 does not claim an algorithm that discovers such proofs.

The graph theorem below consumes the merge-safety judgment. Its compressed graph is a certified structural projection, not a claim that an original whole-boundary transport can automatically be retyped over a boundary whose nodes have been collapsed.

## 7. Certified nonlinear lineage

### 7.1 Nodes and whole-boundary hyperedges

A certified source node has:

- a stable `NodeId`;
- a `FormCode`;
- a state in the form assigned to that code;
- a rank;
- an append-only base-support family.

A source lineage carries a finite family `formAt : FormCode → Form`. V0 also declares an explicit `ComponentwiseBoundaryModel` instance: for a canonically ordered finite node boundary, states are dependent tuples, tests select one component test, and evaluation is componentwise. This is a restricted executable reference model. It is **not** a theorem that arbitrary CLC whole-boundary forms or tests factor into node-local products; replacing it requires a separately certified boundary model and factorization law.

An active source hyperedge has stable finite input and output **ports**, not just node sets:

- a stable `EdgeId`;
- a nonempty finite `InputPort` type and map `inputNode : InputPort → NodeId`;
- a nonempty finite `OutputPort` type and map `outputNode : OutputPort → NodeId`;
- the derived whole-input and whole-output boundary forms;
- a verified transport between those boundary forms;
- for each output port, a nonempty dependency mask of input ports;
- an occurrence certificate token.

The edge proves that transporting the current joint input-port state yields the current joint output-port state. Node payloads and activated edge occurrences are immutable in V0; later events activate reserved identifiers, append base support, enable fresh tokens, or revoke live tokens.

Ports remain distinct when their incident nodes are quotient-identified. Thus two output ports that collapse to the same quotient node still carry two separate masks; alternatives are never silently unioned into a conjunction. Likewise, two masked input ports remain two conjunctive positions even if they map to one quotient node.

The raw port hyperedge is authoritative. Its dependency mask is never flattened into unrelated binary causes. The derived immediate dependency relation contains `parent → child` exactly when an active output port for `child` masks an input port for `parent`.

One input with many outputs is a split. Many inputs supporting one output is recombination. Many inputs with many outputs is joint restructuring. A list lineage is a path projection through this primary hypergraph object.

### 7.2 Certified source and structural view

`CertifiedSource` contains semantic node payloads, verified boundary transports, port hyperedges, active identifiers, append-only base supports, and the evolving support snapshot. `RawView Label` is the smaller operational projection used by closure and queries: active labels, ranks, stable port rules, base supports, and `σ`.

`sourceView` forgets semantic payloads but retains every stable edge/port identifier and support token. `quotientView q` maps only node incidence and aggregates base supports canonically; each projected rule carries an erased witness to its certified source edge and output port. It does not fabricate a new `VerifiedTransport` over a collapsed boundary. This separation makes the quotient constructible while retaining an auditable route to every lawful occurrence.

### 7.3 Acyclicity and paths

Every selected parent has lower rank than its output. This yields a finite acyclic immediate-dependency relation. `Reachable` is its positive transitive closure; reflexive reachability is exposed separately.

## 8. Alternative and dormant support

A support is a finite set of tokens. A support family is a finite antichain under strict subset. Normalization `Min⊆` removes every strict superset while preserving incomparable alternatives. Base-support records are append-only provenance. The normalized closed family is a deterministic derived cache, and liveness is a separate view over it.

The snapshot stores:

- `liveTokens`;
- `revokedTokens`;
- a proof that the sets are disjoint.

A support is live exactly when all of its tokens are live. For the evolving support snapshot `σ`, `liveView σ F` filters a family to its live alternatives. A claim is currently warranted exactly when `liveView` of its closed family is nonempty. The unfiltered closed family remains available for audit and dormant-alternative queries.

Events may add a fresh live token, add a support alternative, or revoke a token. Revocation removes the token from `liveTokens`, adds it to `revokedTokens`, and never deletes immutable support records. A revoked identifier cannot be re-enabled; restoration requires a distinct fresh token.

“Dormant” is formalized in two useful ways:

1. a stored alternative that is not the currently selected witness but remains live; and
2. a stored alternative awaiting a not-yet-live fresh external token.

V0 proves that revoking one support does not retract a claim while another live alternative remains, and that enabling the missing fresh token can activate a previously inactive stored alternative without rewriting its provenance.

## 9. Protected query language

The complete V0 query syntax is:

```lean
inductive ProtectedQuery (Label : Type)
  | reachable (from to : Label)
  | dependsOn (parent child : Label)
  | currentlyWarranted (node : Label)
  | hasAlternativeSupport (node : Label)
```

Queries are label-relative rather than representative-relative. For a labelling map `label : NodeId → Label`:

- `reachable a b` asks whether some active node labelled `a` reaches some active node labelled `b`;
- `dependsOn a b` asks whether an immediate recorded dependency connects those labels;
- `currentlyWarranted a` asks whether the normalized union of cached closed families of active nodes labelled `a` contains a live support;
- `hasAlternativeSupport a` asks whether that same normalized label-level family contains at least two distinct alternatives, regardless of which is currently selected.

Using a label-level normalized union is essential: if a quotient fibre contains one alternative from each of two representatives, both the source query and the quotient query see the same two alternatives. The source semantics is not an existential “two alternatives at one representative” test.

No other query inherits preservation in V0. Every theorem names this grammar explicitly.

## 10. Structural quotient admissibility

A proposed node quotient is a finite map `q : NodeId → QuotNode`; active quotient nodes are exactly images of active source nodes. The projected view retains stable edge, input-port, and output-port identifiers. It maps only each port's incident node through `q`; masks remain sets of stable input ports, so parallel rules and coalesced outputs remain distinct.

For a support-family assignment `F`, define the fibre aggregation

```lean
fibreMin q F z := MinSubset (⋃ x, q x = z ∧ Active x, F x)
```

and let `rankStep L r F` compute only the support contributions whose output rank is `r`, using values of `F` at lower ranks. Both operations are finite and executable. They are independent of the protected query evaluator.

`SupportCompatible R q` packages exactly the closure-facing laws for a raw view: canonical base-support aggregation, rank-local support commutation, and use of the same support snapshot. It contains no path, query, or semantic-state claim. `AdmissibleQuotient` includes a `SupportCompatible (sourceView L) q` field in addition to the remaining certificates below.

`AdmissibleQuotient Ωauth L q` requires the following structural certificates:

1. **Active surjectivity.** Every active quotient node has an active source representative.
2. **Typed and ranked fibre coherence.** Active nodes in one fibre have the same form code and rank.
3. **Continuation-safe merge.** States of any two active nodes in one fibre satisfy `ContinuationSafe` at `Ωauth`.
4. **Forward incidence.** Every source dependency maps to a quotient dependency; this follows from quotient construction and is exposed as a theorem.
5. **Local path lifting.** For every active source node `x` and quotient immediate step from `q x` to `z`, there is a source immediate step from `x` to some `y` with `q y = z`.
6. **Base-support aggregation.** Via `SupportCompatible`, the quotient base family is exactly `fibreMin q sourceBase`.
7. **Rank-local support commutation.** Via `SupportCompatible`, at each rank frontier reached by the rank fold, aggregating `rankStep` from the source equals applying quotient `rankStep` to the aggregated lower-rank prefix. The equality is required for the actual prefix produced from the base families at that frontier; every allowed event re-establishes it for its post-event state. This finite algebraic check covers whole hyperedges, dependency masks, and occurrence tokens and forbids cross-fibre mixing of conjunctive evidence.
8. **Occurrence provenance.** Every projected port rule retains its source `EdgeId`/`OutputPort` and an erased witness to the verified source occurrence; no descended boundary transport is postulated.
9. **Snapshot identity.** Via `SupportCompatible`, source and quotient views use the same live/revoked token snapshot `σ`.

Local path lifting is a structural p-morphism condition. V0 proves by path induction that every quotient path lifts from each chosen source representative. This is the non-circular lemma that prevents a quotient from manufacturing reachability.

Rank-local support commutation is the corresponding structural homomorphism condition for conjunctive derivation. It is stronger than graph path lifting: path lifting alone would still allow support from one representative to be consumed by an edge incident to another representative after merging. V0 checks the local rank equation directly, then derives full `batchClose` commutation by induction over ranks. Admissibility never contains a protected-query equality or the capstone theorem as a field.

Using only these fields, V0 proves preservation separately for each of the four query constructors. Query evaluation depends on `RawView`/`ClosedView` data, not on a fabricated representative payload.

## 11. Events, growth, and quotient commutation

Events are atomic, eliminating ambiguous same-event phase order:

```lean
inductive SourceEvent
  | activateStructure (nodes : Finset NodeId) (edges : Finset EdgeId)
  | addBaseSupport (n : NodeId) (s : Support)
  | enableToken (t : Token)
  | revokeToken (t : Token)
```

`activateStructure` is one atomic transaction with an explicit phase rule: validate every reserved node, port boundary, rank inequality, `VerifiedTransport Ωauth` certificate, and live occurrence `Token` against the pre-state; then activate all listed nodes; then activate all listed edges simultaneously. Singleton node or edge activation is the corresponding singleton bundle. The other constructors perform only their named update. Their checker validates grounded support, fresh non-revoked enablement, or currently live revocation. A `CheckedSourceEvent C.source` packages a successful check. `AllowedStep Ωauth q C e` additionally certifies that the post-step source state preserves typed/ranked fibres, local path lifting, and the rank-local support equation.

`mapEvent C.raw q e` is intentionally state-dependent and returns a checked projected-view delta. In particular, a structural bundle containing a source node whose quotient fibre is already active still emits an `absorbNode` delta that unions the new representative's base support and records its rank/type coherence; it is not treated as a no-op. Bundled edge activation maps port incidence while retaining stable ports and masks. Support and token events map directly. `applySource` consumes the checked source event; `applyRaw` consumes its checked source-view or projected-view delta.

Raw-view commutation is stated using `ViewEq`, extensional equality of canonical active labels, port rules, normalized base families, and support snapshot. Proof fields and representative choices are excluded:

```lean
projectRaw q (applyRaw C.raw h.sourceDelta) ≈ᵥ
  applyRaw (projectRaw q C.raw) h.projectedDelta
```

where `h : AllowedStep Ωauth q C e`; both deltas are checked against their respective pre-state, and `h.projectedDelta` is the state-dependent result of `mapEvent`.

Because `CheckedViewEvent R` is indexed by its exact pre-state while commutation yields `ViewEq`, V0 provides the transport and congruence package:

```lean
rebaseChecked (h : R ≈ᵥ S) :
  CheckedViewEvent R → CheckedViewEvent S

applyRaw_congr (h : R ≈ᵥ S) (e : CheckedViewEvent R) :
  applyRaw R e ≈ᵥ applyRaw S (rebaseChecked h e)

flashStep_congr (h : C ≈ᶜ D) (e : CheckedViewEvent C.raw) :
  flashStep C e ≈ᶜ
    flashStep D (rebaseChecked h.rawEq e)
```

Use the displayed dependent types and argument order. The lemmas contain no query premise.

`AllowedTrace Ωauth q C E` is recursive: each event must be an `AllowedStep` at the closed state where it occurs, and the tail is checked against the result of `flashStep`. V0 proves admissibility and `ViewEq` after every step. `projectTrace` threads that simulation witness, rebases each next projected delta onto the actual projected pre-state, and returns a dependent checked projected trace rather than a plain `List.map`. `Grow` is the corresponding total fold over a proof-carrying allowed trace.

The V0 trace theorem ranges over source-certified, quotient-compatible events. It proves preservation for every such future trace and its state-dependent projection. It does not claim that an arbitrary quotient-only event has a source lift; that backward-simulation theorem is explicitly deferred.

## 12. Flash closure and revocation

V0 separates raw state from derived caches:

```lean
applyRaw   : (R : RawView Label) → CheckedViewEvent R → RawView Label
batchClose : RawView Label → ClosedView Label
flashStep  : (C : ClosedView Label) → CheckedViewEvent C.raw → ClosedView Label
```

`ClosedView` contains its `raw` view, normalized closed-support families, the live/warrant cache, and an erased invariant relating those fields. This prevents raw lineages, closed lineages, and post-event change information from being conflated.

`ClosedSource` pairs a `CertifiedSource` named `source` with its `ClosedView NodeId` and a proof that the latter closes `sourceView source`. `sourceClosedView` exposes that cache. The accessor `closedSupportCompatible C hq` transports `hq.supportCompatible` across this recorded raw-view equality, yielding `SupportCompatible (sourceClosedView C).raw q`; the capstone never relies on accidental definitional equality. Source growth updates the certified source and its cache together; projected growth operates only on `ClosedView QuotNode` plus the erased occurrence witnesses carried by admissibility.

Uncertified aggregation and certified projection are distinct:

```lean
aggregateClosedData : (q : NodeId → QuotNode) → ClosedView NodeId → ClosedData QuotNode
projectClosed :
  (q : NodeId → QuotNode) →
  (C : ClosedView NodeId) → SupportCompatible C.raw q → ClosedView QuotNode
```

`aggregateClosedData` merely computes candidate normalized fields and cannot be used where a closed invariant is required. `projectClosed` constructs that invariant from the explicit support-compatibility witness.

### 12.1 Batch semantics

For each active edge output port, derivation combines:

- one support alternative from the incident node of every input port in that output port's conjunctive dependency mask; and
- the hyperedge's occurrence-certificate token.

Combination uses pairwise union followed by `Min⊆`. Because ranks strictly increase, `batchClose` computes the unique grounded support closure by a finite rank-ordered fold and then computes `liveView σ`.

### 12.2 Incremental semantics

`flashStep C e` receives both the prior closed state and the atomic event. It therefore knows the change roots before applying the event and can identify their dependency descendants. For structural or base-support insertion it retains unaffected closed families, resets affected derived families to their append-only base supports, and folds only the affected region in rank order. For token enablement or revocation it preserves the provenance closure and refreshes the affected `liveView`/warrant cache over the same region.

V0 proves:

```lean
flashStep C ê ≈ᶜ batchClose (applyRaw C.raw ê)
```

for every checked atomic event, where `≈ᶜ` is extensional equality of raw view, normalized support families, and live/warrant data. Revocation filters liveness, not immutable provenance; it never deletes a grounded alternative. Unsupported cycles cannot self-sustain because V0 derivations are rank increasing.

V0 also proves quotient/closure commutation:

```lean
projectClosed q (batchClose R) hsupport ≈ᶜ
  batchClose (projectRaw q R)
```

where `hsupport : SupportCompatible R q`. This theorem is proved by rank induction from base-support aggregation and rank-local support commutation. It is not a field of `AdmissibleQuotient`, and no `ClosedView` projection is constructible without the compatibility witness.

## 13. Capstone theorem

The final theorem is named:

```lean
theorem grow_dissolve_preserves_protected_queries
    (hq : AdmissibleQuotient Ωauth C.source q)
    (hE : AllowedTrace Ωauth q C E)
    (Q : ProtectedQuery QuotNode) :
    evalQuery q
        (sourceClosedView (growSource C hE)) Q =
      evalQuery id
        (growProjected
          (projectClosed q (sourceClosedView C)
            (closedSupportCompatible C hq))
          (projectTrace hq hE)) Q
```

The proof proceeds by induction over `E` using:

1. one-step event/quotient commutation;
2. Flash-versus-batch exactness;
3. quotient/closure commutation;
4. preservation of structural admissibility;
5. the query-specific preservation theorem for `Q`.

`projectTrace hq hE` is computed recursively and carries the evolving `ClosedViewEq` witness, so each mapped delta is rebased onto the correct actual projected pre-state. The theorem states preservation of declared protected answers along every finite source-certified, quotient-compatible trace. It does not state backward simulation of arbitrary quotient-only events, or equality of raw histories, node counts, identifiers, costs, or arbitrary semantic predicates.

## 14. Mandatory negative fixture

The fixture has raw nodes `a₁`, `a₂`, `b₁`, `b₂`, and `c`; dependencies only `a₁ → b₁` and `b₂ → c`; and quotient fibres `[a] = {a₁,a₂}`, `[b] = {b₁,b₂}`, `[c] = {c}`.

The quotient contains apparent steps `[a] → [b]` and `[b] → [c]`, hence an apparent path `[a] → [c]`, although the source contains no such path.

V0 must provide:

- an executable evaluation showing the raw and quotient reachability answers differ;
- a theorem showing local path lifting fails at `b₁` for the quotient step `[b] → [c]`;
- a theorem `spuriousPath_not_admissible` proving that no `AdmissibleQuotient` value can be constructed for this fixture.

This fixture is part of the qualification gate, not merely an example.

## 15. Module boundaries

All new Lean modules live under `qcklean/CLC/` and use namespace `CLC`.

| Module | Responsibility |
|---|---|
| `Verdict.lean` | Verdict order and decisive refinement |
| `Transport.lean` | Forms, certificate boundary, transport identity/composition |
| `Continuation.lean` | Continuation-safe equivalence, protected semantic quotient action, naturality |
| `Hypergraph.lean` | Certified port hypergraphs, raw/closed views, and paths |
| `Support.lean` | Support antichains, liveness, insertion, revocation |
| `Query.lean` | Protected query syntax and evaluation |
| `Quotient.lean` | Certified structural projection, view equivalence, local lifting, query preservation |
| `Flash.lean` | Raw/closed separation, batch closure, affected-region reclosure, exactness |
| `Grow.lean` | Atomic events, state-dependent projection, traces, capstone theorem |
| `Fixtures.lean` | Positive reference model and negative spurious-path fixture |
| `Audit.lean` | Axiom printout and forbidden-placeholder checks |

`qcklean/lakefile.lean` gains these modules as roots. Existing QCK source files are imported where useful but not modified.

## 16. Testing and qualification

Each module receives a compile-time interface test before its implementation. Every implementation task follows a red/green cycle: the missing declaration first causes the expected Lean failure, then the minimum proof makes it pass.

Qualification requires:

1. the full existing `qcklean` target remains green;
2. every new public theorem is referenced by an interface test;
3. exhaustive `#eval` checks cover all finite positive and negative fixtures;
4. the transport tests cover identity, two-step composition, strict preservation, UNKNOWN refinement, and a rejected non-pullback map;
5. hypergraph tests cover chain, diamond, split, recombination, many-to-many incidence, disconnected graphs, parallel edges, and two output ports coalescing to one quotient node without merging their masks;
6. support tests cover incomparable alternatives, redundant-superset normalization, revocation fallback, fresh-token activation, and forbidden resurrection;
7. quotient tests cover all four protected queries, an activation absorbed into an already-active fibre, rejection of cross-fibre conjunctive support mixing, and the spurious-path failure;
8. Flash tests compare every structural bundle, base-support insertion, token enablement, and revocation in the finite fixture against batch closure;
9. trace tests cover the empty trace, one event, mixed insertion/revocation, and a multi-event grow–dissolve run with state-dependent projected deltas;
10. source scans reject `sorry`, `admit`, `axiom`, unsafe declarations, and unapproved local constants in `qcklean/CLC/`;
11. `#print axioms` for the capstone contains only Lean/Mathlib foundations already allowed by the repository's QCK audit policy.

A dedicated GitHub Actions workflow pins the existing toolchain and Mathlib revision, builds the complete QCK target, builds CLC V0, executes the fixtures, runs the source audit, and prints the capstone theorem's axiom surface.

## 17. Acceptance criteria

CLC Nonlinear Lineage V0 is complete only when all of the following hold at one committed branch head:

- transport identity, composition, associativity, and decisive preservation are proved;
- continuation-safe equivalence is an equivalence and is stable under every verified forward transport;
- nonlinear hyperedges retain stable input/output ports and conjunctive dependency masks even when incident nodes coalesce;
- all four protected query constructors have separate preservation theorems;
- alternative supports survive selection and unrelated revocation;
- revocation never resurrects an identifier and never erases archived support data;
- finite Flash insertion and revocation are extensionally equal to batch closure;
- the grow–dissolve theorem is proved for arbitrary finite source-certified, quotient-compatible traces;
- the negative spurious-path quotient is rejected by failure of local path lifting;
- no CLC-owned placeholder or extra axiom remains;
- frozen QCK branches and theorem files remain unchanged.

## 18. Claim boundary

Passing V0 would establish a bounded mathematical mechanism:

> Under a declared finite event universe, stable port rules, structural path lifting, continuation-safe merge certificates, rank-local support commutation, and checked event compatibility, certified structural projection commutes with finite source-certified growth for the four declared protected queries.

It would not establish backward simulation of arbitrary quotient-only events, eternal intelligence, universal lossless compression, arbitrary future preservation, real-world causal completeness, or the full CLC V1 publication threshold. Those remain separate theorem programs.
