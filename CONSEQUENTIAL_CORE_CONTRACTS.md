# Consequential Core Contracts

This note constrains the executable calculus. The shared kernel must preserve the semantic distinctions already present in the experiments rather than erase them behind a generic `update(state)` interface.

## Shared state

The smallest honest common state found by the compatibility audit is

\[
S=(E,H,C,D),
\]

where:

- `E` is an optional active observational equivalence / representation kernel;
- `H` is a live residual-relative version space of representation hypotheses;
- `C` is the executable interaction / constructor language;
- `D` is an optional developmental policy controlling bounded acquisition from `C`.

`E`, `H`, `C`, and `D` are not interchangeable. A representation refinement changes which states are identified. A version-space update changes which structural hypotheses remain live. A language extension changes which future constructions are executable. A developmental-policy change changes what a bounded future acquisition episode reaches.

## Representation

```text
Representation[X] := EquivalenceRelation[X]
```

It is reflexive, symmetric and transitive. Boolean or finite-valued observations enter the core only through their kernels. Refinement is relation inclusion:

```text
refines(E_new,E_old) := E_new subseteq E_old
```

so a lawful refinement cannot merge states already separated by protected evidence.

## Residual

Residual is a tagged sum because the experiments contain genuinely different certified failure objects:

```text
Residual[X] :=
    | PairResidual(
        left, right,
        current E identifies them,
        protected consequence distinguishes them)

    | ClosureResidual(
        required_kernel,
        realized_kernels,
        complete ClosureCertificate bound to an exact C snapshot,
        required_kernel absent from realized_kernels)

    | AcquisitionResidual(
        task,
        exact C snapshot,
        exact D snapshot,
        budget,
        certified cold failure)
```

`PairResidual` is first-order failed identification. `ClosureResidual` is complete current-language non-realizability. `AcquisitionResidual` is second-order: the current developmental policy cannot acquire a successful next move under a declared budget, even though changing `D` may alter that future acquisition without immediately changing `E` or `C`.

This distinction was forced by the compatibility audit. Treating recursive policy development as a pair residual would be semantically false because changing `D` alone does not immediately split the motivating pair.

## Closure

```text
ClosureCertificate := (
    interactions,
    complete,
    resource_regime,
    exact_language_snapshot
)
```

A non-reachability claim is licensed only relative to an explicit closure and resource regime. A stale closure certificate cannot be replayed after the language changes.

`H` is not overloaded to mean language closure: it remains the live hypothesis/version space. The kernels realizable by `C` belong to a closure certificate/residual, not to `H` by definition.

## Repair

```text
Repair[X] :=
    | RefineRepresentation(new_E)
    | ReplaceVersionSpace(new_H)
    | ExtendLanguage(delta_C)
    | UpdatePolicy(new_D)
    | Coupled(...)
```

A repair is lawful only if it is conservative, resolves the correctly typed motivating residual, attaches to it, and is verifier-licensed.

Meaningful non-repairs include:

- a merge that erases a licensed distinction;
- a duplicate/inert language extension;
- an unchanged policy presented as development;
- an incomplete closure presented as a non-realizability certificate;
- a stale residual from an earlier `C` or `D` snapshot;
- an update that does not resolve the failure type it claims to repair;
- an unverified or unattached state mutation.

Thus the common interface is not made true by defining every mutation as a repair.

## compile / ablate

```text
compile : (S, CertifiedRepair) -> (S', ProvenanceToken)
ablate  : (S', ProvenanceToken) -> S_counterfactual
```

Compilation preserves the repair tag. Exact ablation is accepted only against the precise post-state stored in provenance, preventing an ancestor ablation from silently deleting unrelated later development.

## Compatibility audit

### Difference Test

- state object: explicit equivalence relation;
- residual: `PairResidual`;
- closure: finite action closure;
- repair: representation refinement, optionally coupled with collapse of `H` after a discriminating experiment.

**Direct fit.**

### Golden-law meta-becoming

- representations: kernels of executable columns;
- failure: required target kernel absent from kernels realizable by the current base language;
- residual: `ClosureResidual`;
- repair: `ExtendLanguage` with the retained behavioural operator class;
- ablation: remove that language contribution and restore base-language failure.

**Language development, not representation refinement.**

### Recursive developmental compounding

- `C`: fixed target query language;
- cold episode fails within the matched one-query budget;
- residual: `AcquisitionResidual` tied to exact `C`, `D`, and budget;
- repair: `UpdatePolicy`;
- warm policy changes which query is acquired next;
- exact ablation restores cold acquisition behaviour without changing `C`.

**Second-order development.** It must remain distinct from `ExtendLanguage` unless a separate verified compilation map `D -> C_extension` is established.

## Parametric cardinality family

The cardinality test is deliberately elementary:

\[
X_n=\mathbb Z_n\times\{0,1\},\qquad g(i,b)=(i+1\bmod n,b).
\]

The implementation now checks `n=2..16`, verifies `|<g>|=n`, and verifies that the unchanged residual-orbit constructor recovers the fixed hidden coordinate up to complement. This tests carrier-size independence only. It is **not** evidence of robustness to structural variation: the hidden coordinate and its dynamical role are fixed by construction.

## Single-chain acceptance criteria

A single-chain experiment counts as one formal machine only if:

1. all representations use `EquivalenceRelation`;
2. all failures use the shared tagged residual type;
3. closure claims use `ClosureCertificate` with exact state snapshots;
4. repairs use shared tagged repair constructors;
5. every stage returns `DevelopmentState`;
6. ablation is provenance-exact;
7. `H`, `C`, and `D` are not silently conflated;
8. second-order change uses `AcquisitionResidual` or a separately verified compilation theorem;
9. domain adapters may change across transfer tests, but the core contracts may not.

The current single-chain test is intended to instantiate this path in one state machine:

```text
PairResidual
  -> forked H
  -> discriminating experiment
  -> coupled E/H refinement
  -> newly quotient-admissible operator
  -> ClosureResidual
  -> ExtendLanguage
  -> exact language ablation
  -> AcquisitionResidual
  -> UpdatePolicy
  -> changed next bounded acquisition
  -> exact policy ablation
```

If an existing experiment can only be made to fit by weakening its original claim, that is a redesign rather than a refactor and must be reported as such.
