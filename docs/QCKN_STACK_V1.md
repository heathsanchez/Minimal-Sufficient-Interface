# QCKN Stack v1 — Consolidated Architecture

## Purpose

QCKN is the unified developmental stack for consequence-governed substitution:

> detect what blocks useful consequence flow, preserve what matters, remove or restructure the obstruction, certify the change, compile the lesson, and reuse it.

This document is the architectural source of truth while QCK v1 is being formalized.

## Constitutional layers

### 1. MSI — sufficiency principle

MSI defines when distinctions may be forgotten: two source states are equivalent exactly when no protected continuation can distinguish them.

This layer owns the notion of consequential sufficiency. It does not own search policy, domain heuristics, or implementation strategy.

### 2. QCK Core — certified substitution

`qcklean/QCKCore.lean` is the frozen semantic kernel.

It owns:
- contextual nullspaces;
- canonical quotients;
- induced actions and observations;
- all-word substitution;
- the universal/coarsest sufficient representation;
- certificate composition;
- kernel-stable operation descent;
- separating witnesses when descent fails.

No finite-dimensional coordinates, optimization policy, domain-specific assumptions, or RealityGraph metadata belong here.

### 3. QCK FiniteLinear — executable and quantitative consequences

`qcklean/QCKFiniteLinear.lean` is the canonical finite-dimensional realization layer.

It owns:
- finite contextual closure in the dual;
- annihilator/coannihilator characterization;
- basis-free executable finite presentation;
- rank minimality;
- operation-defect diagnostics;
- snapshot optionality;
- maintained optionality;
- reserve dimensions;
- reserve attainment and recovery/update constructions;
- fixed-vocabulary submodularity and negative controls.

All previously parallel FiniteLinear development is to be reconciled here. Do not create a second semantic optionality implementation.

### 4. QCK API — typed epistemic outcomes

The API layer will expose stable result types such as:
- `CertifiedSubstitution`;
- `NewContextDefect`;
- `ReserveRequired`;
- `RecoveryUnavailable`;
- `ImplementationMismatch`;
- `CertificateInvalid`;
- `OutOfScope`;
- `Unknown`.

This is the boundary between formal semantics and developmental control.

## Developmental layers

### 5. MDA — intervention policy

MDA receives typed residuals from QCK/authority and chooses the smallest warranted intervention under prospective cost.

Canonical intervention vocabulary:
- `SPLIT`
- `MERGE`
- `EXPAND`
- `REVOKE`
- `CONSTRUCT`
- `VERIFY`
- `RESTRUCTURE`
- `COMPILE`

MDA does not redefine semantic sufficiency.

### 6. RealityGraph — live consequence graph

RealityGraph records the current developmental topology.

Canonical node classes:
- representation;
- capability;
- certificate;
- obstruction;
- context;
- experiment;
- implementation;
- reserve;
- benchmark.

Canonical edge classes:
- `certifies`;
- `depends-on`;
- `invalidates`;
- `exposes`;
- `substitutes-for`;
- `requires`;
- `recovers`;
- `compiled-from`;
- `improves`.

### 7. .mg — compiled developmental present

An `.mg` artifact carries only what has earned the right to survive restart:
- declared contract;
- promoted representation/procedure;
- certificate;
- dependencies;
- reserve requirements;
- cost profile;
- provenance pointer.

The intended property is: verified lessons should be reusable without replaying their full discovery cost.

### 8. MathGraph / authority — promotion gate

Every candidate becomes reusable only after an independent consequence check.

The verifier varies by domain, but the protocol is shared:
1. propose;
2. evaluate protected consequences;
3. emit proof/counterexample/measurement;
4. promote or reject;
5. compile the result into RealityGraph/.mg.

Examples of authorities include Lean, finite exhaustive checks, benchmark equivalence, numerical tests, simulation, physical experiment, or other domain verifiers.

## Domain adapters

Lean kernel, SAIR, ARC, robotics, GPU kernels, Collatz, and scientific experiments are adapters rather than separate developmental architectures.

Each adapter should expose the smallest practical common interface:

- `observe`
- `propose`
- `verify`
- `cost`
- `counterexample`
- `promote`

Domain-specific logic stays below this interface. Representation development, promotion, graph retention, and reuse stay shared.

## State discipline

Every layer distinguishes:

1. **ACTIVE** — required for present consequence-preserving operation.
2. **RESERVE** — not required now, but retained to preserve declared future optionality.
3. **PROVENANCE** — evidence explaining why a substitution or intervention is warranted.

Provenance is not recoverability. A certificate that deletion was safe does not reconstruct deleted state.

## Universal QCKN loop

```text
observe
→ classify residual
→ retrieve compiled capabilities
→ generate minimum intervention
→ verify
→ compare consequences and cost
→ promote or reject
→ compile proof/counterexample
→ re-minimize representation
→ repeat
```

The compounding invariant is:

> do not pay twice for a verified lesson, and do not retain a distinction after it has ceased to have protected consequences unless it is justified as reserve.

## Consolidation rules

1. `QCKCore.lean` remains frozen unless a genuine semantic obstruction forces a constitutional change.
2. There is one authoritative FiniteLinear line: `qck-unified-v1` during qualification.
3. Parallel definitions are aliases or migrations, not new competing semantics.
4. Every RED should become a typed residual or reusable separator when possible.
5. Every promoted capability must record its contract, verifier evidence, dependencies, and prospective cost effect.
6. Every hot-path structure is periodically challenged by ablation: if no protected consequence changes, merge/delete it.
7. New domains integrate through adapters rather than recreating the stack.
8. Formalization and consolidation proceed together: when a theorem fixes a canonical concept, surrounding code and terminology converge on that concept.

## Current formalization path

The bounded QCK v1 completion path is:

1. freeze Core;
2. finite contextual closure;
3. basis-free finite presentation;
4. rank minimality and operation defect;
5. snapshot optionality, lower bound, and attainment;
6. maintained optionality and maintained reserve dimension;
7. recovery/update maps and block form;
8. fixed-context submodularity;
9. U/V capability-generated non-submodularity counterexample;
10. typed QCK API;
11. whole-stack no-placeholder and axiom audit;
12. freeze QCK v1 and migrate downstream users to the consolidated interfaces.

The intended result is one stack whose normal operation is:

> find the obstruction → preserve the essential → remove/restructure the blockage → certify → retain the lesson → flow faster next time.
