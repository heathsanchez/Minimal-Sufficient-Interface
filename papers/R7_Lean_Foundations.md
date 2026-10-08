# R7 — Verified Development: Lean Foundations

*Daniel-facing Lean-first revision of* **Verified Development Under Consequential Constraints** (R6, 5 October 2026).

**Version:** candidate until its exact head passes a pinned Lean kernel CI run.
**Scope:** the foundations in R6 Sections 1–4 only. The rest of R6 is retained as a separate research synthesis, not smuggled into this proof.

## 1. States, actions, observations, and stages

The existing file [TypedBehaviouralCongruence.lean](../lean/TypedBehaviouralCongruence.lean) defines `SmallCategory` and `Action C`. Each object `X` carries a Lean type `A.State X`; each arrow `f : C.Hom X Y` gives a state transition `A.map f` respecting identities and composition.

The existing file [DevelopmentalCategory.lean](../lean/DevelopmentalCategory.lean) defines `Stage C` as an admitted class of typed arrows closed under identity and composition. A protected observation at each object is a function `observe X : A.State X → Obs X`.

These are the entire core assumptions: total deterministic typed actions, with an explicitly declared stage. Partial, adversarial, nondeterministic, stochastic and resource-sensitive actions remain outside this proof.

## 2. Behavioural equivalence and executable quotient

The existing `BehEqAt C A Obs observe S X x y` means that *every* `S`-admitted continuation starting at `X` gives equal protected observations.

Existing exact declarations:

- `behEqAt_refl`, `behEqAt_symm`, `behEqAt_trans`: it is an equivalence;
- `behEqAt_congruent`: every stage-admitted arrow respects equivalence;
- `stageSetoid`, `StageQuot`, `stageMap`, `stageMap_id`, `stageMap_comp`: the quotient executes admitted arrows and preserves composition;
- `extension_refines`: enlarging the admitted stage can only split old behavioural classes;
- `forgetGrowth`: map from the later, finer quotient back to the earlier, coarser quotient.

The simpler all-action monoid presentation and its greatest-invariant theorem remain in [BehaviouralCongruence.lean](../lean/BehaviouralCongruence.lean). No automata theory is required.

## 3. Residuals and canonical refinement

[CanonicalRefinement.lean](../lean/CanonicalRefinement.lean) introduces a *typed relation family* `E`, a new protected observation `d`, and

```lean
def RefS (S : Stage C) (E : Relation C A) : Relation C A :=
  fun X x y =>
    E X x y ∧
      ∀ (Y : C.Obj) (f : C.Hom X Y), S.allow f →
        d Y (A.map f x) = d Y (A.map f y)
```

The proposed new theorems `refS_sub`, `refS_compatible`, `refS_invariant`, `refS_greatest`, and `refS_equivalence` together say:

- refining cannot introduce a new merge;
- the new observation is protected at the identity;
- the refinement remains invariant under the admitted stage;
- it is the **greatest** stage-invariant subrelation of `E` compatible with `d`;
- if `E` is an equivalence, so is the refinement.

Crucially, `refS_greatest` assumes that the *candidate subrelation* is invariant. Without that premise, maximality would be false. This is a conditional theorem over a specified stage, not an automatic grammar-synthesis theorem.

The derived `Err` and `Open` predicates in [ScopedCertificates.lean](../lean/ScopedCertificates.lean) represent already-merged pairs with verified separators and unsettled pairs respectively. `err_open_disjoint` expresses the disjointness by construction. A pair with no found separator is *not* thereby proved equivalent.

## 4. Certificate scope, retraction and reclosure

[ScopedCertificates.lean](../lean/ScopedCertificates.lean) defines `Gamma check depends W`: a record is eligible exactly when its checker accepts and every mandatory dependency belongs to `W`.

`Valid check depends` is an **inductively generated** proof predicate, not a greatest/coinductive fixed point. The target theorems:

- `valid_fixed`: `Valid ↔ Gamma Valid`;
- `valid_least`: `Valid` is contained in every prefix-point closed under `Gamma`, excluding unsupported circular justification;
- `check_shrink`: removing checker authority cannot add valid records;
- `revoke_self`: revoked records become invalid;
- `revoke_recloses`: every record that transitively depends on a revoked record becomes invalid.

`ScopeAdmission` records admitted continuations and their growth. `merge_restrict` shows a merge certified at a larger scope survives when used at a smaller scope; `separator_extend` shows a witnessed separator survives scope growth. These statements do **not** assume proof-producing finite games.

### Explicit trust boundary

`check` is a **parameter**, not a verified implementation of the external checker. The theory proves consequences of checker acceptance, mandatory dependency, and scope-admission assumptions; it does not prove the soundness of an arbitrary checker, its provenance, or runtime re-execution. `Valid` is a logical least fixed point, not an executable termination algorithm for arbitrary infinite record sets.

## Evidence ledger

| Claim | Source | Authority |
| --- | --- | --- |
| Typed action, stage equivalence, quotient | Existing three Lean files | Pinned MSI commit `c57e30a013e529255fcdc70dc115dec616ebaced`, historic CI run 36343286374 |
| Greatest typed invariant canonical refinement | `lean/CanonicalRefinement.lean` | **CANDIDATE until new CI succeeds** |
| Derived residual predicates, certificate least closure, revocation, scope directions | `lean/ScopedCertificates.lean` | **CANDIDATE until new CI succeeds** |
| Myhill–Nerode, EF/pebble games, general language extension, probabilistic action | R6 Sections 2 and 5–17 | **Not part of R7** |

## Reproduce

Use the pinned `lean-toolchain` (Lean 4.24.0). The scoped [R7 GitHub Actions workflow](../.github/workflows/r7-lean-foundations.yml) compiles the three existing files plus both new files with `LEAN_PATH=lean` and requires no Mathlib or external solver. No theorem in R7 should contain `sorry` or added axioms.

**Promotion rule:** only change CANDIDATE to WARRANTED after a successful workflow at this branch's exact commit SHA. Preserve CI failures as explicit residuals rather than declaring the work completed from a draft.
