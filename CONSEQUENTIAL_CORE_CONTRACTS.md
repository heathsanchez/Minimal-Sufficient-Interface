# Consequential Core Contracts

This note is a pre-refactor constraint. The shared kernel must preserve the semantic distinctions already present in the experiments rather than erase them behind a generic `update(state)` interface.

## Shared state

The compatibility audit shows that the smallest honest common state is provisionally

\[
S=(E,H,C,D),
\]

where:

- `E` is an optional active observational equivalence / representation kernel;
- `H` is an explicit operational version space of representable kernels;
- `C` is the executable interaction / constructor language;
- `D` is an optional developmental policy controlling acquisition from `C`.

`E`, `C`, and `D` are not identified. A representation refinement changes which states are identified. A language extension changes which future distinctions/consequences are executable. A developmental-policy change changes how the next interaction is selected. `H` is required because some failures are closure-level non-realizability claims with no single privileged current representation.

## Core contracts

### Representation

```text
Representation[X] := EquivalenceRelation[X]
```

It must be reflexive, symmetric, transitive, and operationally extensional. A Boolean column enters the core only through its kernel. Refinement means relation inclusion:

```text
refines(E_new,E_old) := E_new subseteq E_old
```

so lawful refinement cannot merge states already separated by protected evidence.

### Residual

Residual is a tagged sum, because the existing experiments genuinely contain two distinct failure types:

```text
Residual[X] :=
    | PairResidual(
        left, right,
        E(left,right),
        certified consequence distinguishes left/right)
    | ClosureResidual(
        required_kernel,
        realized_version_space H,
        complete closure certificate,
        required_kernel notin H)
```

The Difference Test and recursive-compounding test use `PairResidual`. Meta-becoming naturally uses `ClosureResidual`: its failure is that no kernel realizable by the current language equals the required target kernel. Forcing that through one arbitrarily selected current `E` would be semantically dishonest.

### Closure

```text
ClosureCertificate := (interactions, complete, resource_regime)
```

A non-reachability claim is licensed only relative to an explicit closure and resource regime. `ClosureResidual` additionally requires `complete=True`.

### Repair

Repair is also a tagged sum:

```text
Repair[X] :=
    | RefineRepresentation(new_E)
    | ReplaceVersionSpace(new_H)
    | ExtendLanguage(delta_C)
    | UpdatePolicy(new_D)
    | Coupled(...)
```

A repair is lawful only when it is conservative, resolves the motivating residual, attaches to that residual, and is verifier-licensed.

Meaningful non-repairs therefore exist:

- a merge that erases a licensed distinction;
- a duplicate/inert language extension;
- an unchanged policy presented as development;
- an incomplete-closure claim presented as non-realizability;
- a new operator that does not resolve the motivating failure;
- an unverified or unattached state mutation.

This is why the interface is not vacuous despite covering multiple update types.

### compile / ablate

```text
compile : (S, CertifiedRepair) -> (S', ProvenanceToken)
ablate  : (S', ProvenanceToken) -> S_counterfactual
```

Compilation preserves the repair tag. Exact ablation is only allowed against the precise post-state stored in provenance, so it cannot silently erase unrelated later changes.

## Compatibility audit against unchanged experiments

### `tests/test_difference_test.py`

- `E`: explicit partition / equivalence relation;
- residual: pair currently merged but protected consequence separates;
- closure: `action_closure(g)`;
- repair: `RefineRepresentation`;
- compilation: old observation + generated separator induces the new quotient.

**Fits directly.**

### `tests/test_golden_law_meta_becoming.py`

- representations: kernels of executable columns;
- `H`: kernels realizable by the current base language;
- residual: required target kernel absent from `H` under complete tested closure;
- repair: retained behavioural class of binary operator;
- compilation: `ExtendLanguage` with a target-domain realizer;
- ablation: remove the learned class and restore base-language failure.

**Fits as language development, not representation refinement.**

### `tests/test_recursive_developmental_compounding.py`

- `E`: relation induced by currently chosen queries;
- residual: first differently labelled pair still merged by `E`;
- `C`: fixed target query language;
- repair: retained query-selection policy;
- compilation: `UpdatePolicy`;
- ablation: remove that policy while keeping `C` unchanged.

**Fits only if `D` remains a distinct state component.** Treating this as `ExtendLanguage` would erase the exact second-order content the experiment is meant to test.

## Refactor-or-redesign decision

The contracts survive, but the audit changes the original refactor plan in a substantive way. The common machine is not simply `(E,C)`. It is `(E,H,C,D)` with tagged residuals and tagged repairs.

The next question is now precise rather than rhetorical:

```text
Does there exist a verified compilation map D -> C_extension
that preserves target behaviour and exact ablation?
```

Until that is proved, policy development and language development remain distinct constructors in the common calculus.

## Single-chain acceptance criteria

A future single-chain experiment counts as one formal machine only if:

1. all representations use the same `EquivalenceRelation` type;
2. residuals use the shared tagged residual type rather than bespoke error notions;
3. closure claims use the same `ClosureCertificate` interface;
4. repairs use the shared tagged repair constructors;
5. compilation always produces the same `DevelopmentState` type;
6. ablation is provenance-exact;
7. domain transfer changes only domain adapters, not core contracts;
8. second-order development changes `D` explicitly or passes through a separately verified `D -> C` compilation theorem.

If an experiment can only be made to fit by weakening one of its original claims, that is a redesign, not a refactor, and must be reported as such.
