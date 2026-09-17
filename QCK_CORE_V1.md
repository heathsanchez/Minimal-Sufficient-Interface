# QCK.Core v1 — Frozen Semantic Kernel

Status: **FROZEN**

This file records the qualified v1 semantic boundary for QCK.Core. New coordinate, rank, reserve, optionality, and API work must depend on this core rather than modify its mathematical contract.

## Frozen object

- Branch: `qck-core-v1`
- Semantic source file: `qcklean/QCKCore.lean`
- Semantic source commit: `2a429bde0bed5ea3494b2886adda06039d59c892`
- Semantic source blob: `b9b1921c49c9947a02009be124286cfe3c723cb4`
- Qualification commit before this manifest: `01cfe6a32f13e172d14b4c0603e5a4ca0610e5ff`
- Qualification run: `35279029367`
- Lean: `v4.35.0-rc2`
- Mathlib: `44ba35c6daa9d69aff8fed9fff9bbde17ded774d`

## Canonical semantic object

For a field `𝕜`, source space `V`, observation space `Y`, shared action alphabet `A`, generator family `S`, and observation map `C`:

```
N_C = ⋂ w : List A, ker (C.comp (wordMap S w))
Canonical S C = V ⧸ N_C
```

The quotient identifies exactly those source differences that no admitted finite continuation can expose.

## Qualified theorem surface

The frozen interface includes:

- `wordMap`, `wordMap_append`
- `contextNullspace`, `mem_contextNullspace_iff`
- `contextNullspace_invariant`
- `Canonical`, `canonicalMap`
- `reducedAction`, `reducedAction_canonicalMap`
- `reducedObservation`, `reducedObservation_canonicalMap`
- `canonicalMap_wordMap`
- `allWordSubstitution`
- `Sufficient`
- `ker_le_contextNullspace`
- `canonicalFactor`, `canonicalFactor_rangeRestrict`
- `canonicalFactor_surjective`
- `Certificate`, `Certificate.comp`
- `KernelStable`
- `descendedOperation`, `descendedOperation_intertwines`
- `operation_descends_iff`
- `operation_defect_witness`

The universal-property headline is:

```
Sufficient S C q  →  ker q ≤ contextNullspace S C
```

and therefore every sufficient realized linear representation factors surjectively onto the canonical quotient.

For a surjective representation `q`, a proposed source operation descends uniquely exactly when:

```
Aop (ker q) ⊆ ker q
```

Failure yields an erased source difference exposed by the proposed operation.

## Qualification authority

Run `35279029367` passed all of the following:

1. pinned Lean/Mathlib environment setup;
2. rejection of `sorry`, `admit`, local `axiom`/`constant`, and `unsafe` in QCK-owned Lean sources;
3. `lake build QCK`;
4. the full `QCKCoreTest.lean` interface check;
5. direct compilation of every QCK-owned Lean source;
6. theorem axiom-surface reporting.

The reported dependencies of the headline theorems are only Lean's standard:

```
propext
Classical.choice
Quot.sound
```

No QCK-local axiom declaration is admitted by the qualification gate.

## Claim boundary

QCK.Core v1 proves a universal property among linear representations under the declared fixed action/observation contract. It does **not** claim:

- nonlinear or universal operational minimality;
- autonomous contract selection;
- approximate/noisy equivalence;
- optimal runtime or implementation cost;
- probability, PSD, Hilbert-space, quantum, or physical structure;
- coordinate/rank optimality beyond what follows later from finite-dimensional linear algebra.

## Next layer: QCK.FiniteLinear

The semantic core is closed. The next module may derive executable finite-dimensional consequences from it, without changing Core:

- dual observation closure and annihilator equality;
- finite matrix presentation `O`;
- rank/dimension consequences;
- coordinate operation defect `δ_A`;
- snapshot reserve;
- maintained reserve and greatest invariant safely-forgettable subspace;
- block dynamics;
- fixed-vocabulary submodularity;
- the `U,V` negative counterexample showing that capability-driven vocabulary growth need not have diminishing representational cost.

Dependency direction is fixed:

```
QCK.Core → QCK.FiniteLinear → QCK.API
```

QCK determines what substitution is mathematically warranted. Developmental policy remains outside the algebra.
