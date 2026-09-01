# Consequential Core Contract Audit

This document freezes the contracts before any shared-kernel refactor. The purpose is to avoid making "one formal machine" true by defining `Repair` so broadly that every update counts.

## 1. State and representation

A developmental state is

`S = (X, E, C, V, P)`

where:

- `X` is the current carrier/domain;
- `E` is an equivalence relation on `X`, the current operational representation;
- `C` is the executable capability language whose closure determines available interactions;
- `V` is the external certification relation;
- `P` is provenance for retained changes.

A representation update and a capability-language update are deliberately distinct types.

## 2. Residual

`Residual[S]` must contain a verifier-certified incompatibility between the current state and a required consequence. In the quotient case it has a witness pair `(x,y)` such that `E(x,y)` holds but the certified consequence separates them. In a capability-language failure it must additionally identify a certified target consequence/action that is not realizable in `Closure(C)` under the declared resource model.

A mere timeout, empty search result, or unverified mismatch is not a `Residual`.

## 3. Closure

`Closure : CapabilityLanguage -> ExecutableSet`

The closure contract must state the generating operations and the resource bound (if any). A representation failure claim is licensed only relative to a closure for which non-reachability is certified/exhaustive under that contract.

## 4. Repair: two constructors, one constrained sum type

`Repair` is **not** an unconstrained arbitrary state update. It is the disjoint union:

`Repair = RepresentationRepair | CapabilityRepair`

### RepresentationRepair

A `RepresentationRepair` is a strict refinement `E'` of `E` satisfying:

1. preservation: `E' subseteq E` (no merging across previously distinguished classes);
2. attachment: it separates the certified residual witness(es);
3. lawfulness: it is compatible with the protected dynamics/continuations;
4. minimality/version-space status is evaluated inside this constrained class.

It changes `E` directly and leaves `C` unchanged.

### CapabilityRepair

A `CapabilityRepair` is an executable generator/operator `delta` satisfying:

1. novelty: `delta` is not already realizable in the declared old closure (or is not available at the declared resource bound);
2. attachment: adding `delta` creates a route to resolve the certified residual or creates a protected observation whose induced kernel resolves it;
3. verification: the resulting consequence/action is externally certified;
4. non-vacuity: at least one possible language extension is excluded by these requirements.

It changes `C` directly. It may subsequently induce a representation refinement through newly available observations, but that induced refinement is a separate typed transition.

A candidate update that is neither a lawful refinement nor an attached executable capability extension is a non-Repair.

## 5. Compile

`compile : (S, Repair) -> S'`

Compile is type-sensitive:

- compiling a `RepresentationRepair` replaces `E` by `E'` while preserving the rest of the state except provenance;
- compiling a `CapabilityRepair` extends `C` by the certified operator/generator, recomputes the declared closure, and only then recomputes any representation induced by newly protected observations.

Compile may not silently translate one repair type into the other.

## 6. Ablate

`ablate : (S', ProvenanceId) -> S_without`

Ablation removes exactly the retained change identified by provenance and recomputes all downstream derived objects. A causal developmental claim requires the relevant capability/representation effect to disappear under this exact ancestor ablation, not under an unrelated cold baseline.

## 7. Version space and experiment

`VersionSpace(rho, S)` is the set of minimal lawful repairs of a fixed repair type satisfying the residual constraints. If multiple inequivalent minima remain, a discriminating experiment must be generated from a behavior/prediction on which at least two survivors disagree. No arbitrary tie-breaking counts as resolution of the version space.

## 8. Audit of existing tests without changing their code

### `tests/test_difference_test.py`

- Representation: explicit partition/equivalence relation: **direct fit**.
- Residual: pair currently merged but required to split: **direct fit** for representation residual.
- Closure: explicit finite action closure: **direct fit**.
- Repair: partition refinement: **direct `RepresentationRepair`**.
- Compile: currently implicit construction of a refined partition/compiled target: **partial fit; should be routed through shared compile**.
- Ablation: representation reset is conceptually available but not yet a shared provenance operation: **partial fit**.

### `tests/test_recursive_developmental_compounding.py`

- Representation: relation induced by chosen queries: **structural fit**; can be canonicalized as an equivalence relation.
- Residual: first future-distinct pair still merged by chosen queries: **direct fit**.
- Closure: the available query set and one-query budget define the executable frontier, but no shared closure object exists: **partial fit**.
- Repair: the learned fingerprint policy is **not** a `RepresentationRepair`. It changes query selection/developmental machinery and should be represented as a `CapabilityRepair` only if the old declared policy/capability closure excludes its behavior and attachment is stated explicitly.
- Compile: policy retention changes the next developmental episode rather than immediately refining the current quotient: **CapabilityRepair compile path required**.
- Ablation: exact retained-policy removal exists in the test semantics: **fits provenance ablation once typed**.

### `tests/test_golden_law_meta_becoming.py`

- Representation: `kernel(column)` is literally an equivalence relation: **direct representation bridge**, not a generalization-away.
- Residual: target kernel absent from the base language: **capability-language residual**, but certification/non-reachability must be represented explicitly by the shared closure contract.
- Closure: `base_language` and operator-generated columns provide a bounded executable language: **structural fit**.
- Repair: retained behavioural operator class is **not** a partition repair. It is a `CapabilityRepair`; after compilation, generated columns may induce new representation kernels.
- Compile: addition/promotion of the operator class changes future closure: **CapabilityRepair compile path required**.
- Ablation: removal restores the base generator and failure: **fits provenance ablation**.

## 9. Refactor decision

The three experiments do **not** honestly fit a single monomorphic `Repair = partition refinement` interface.

They do fit a non-vacuous two-constructor calculus:

`Residual -> (RepresentationRepair | CapabilityRepair) -> Compile -> derived Representation/Closure -> Verify -> Provenance`

This distinction is load-bearing. It preserves the conceptual separation between:

- learning/abstraction: changing what states are identified (`E`), and
- development: changing what interactions/operators can be generated (`C`).

The proposed shared kernel is therefore a redesign of state plumbing but **not** a collapse of these two update types.

## 10. Acceptance criterion for "one formal machine"

The eventual single-chain experiment may claim one formal machine only if every stage calls the same shared implementations for:

1. equivalence representation;
2. residual certification/witness extraction;
3. declared closure/non-reachability;
4. typed repair construction;
5. version-space handling;
6. compile;
7. exact provenance ablation;
8. quotient admissibility.

Domain adapters may supply observations/actions, but they may not reimplement these operations privately.
