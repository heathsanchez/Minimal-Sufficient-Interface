---
title: 'Verified Development: A Lean-First Foundation'
subtitle: 'States, actions, observations, residuals, refinement, and scoped certificates — R7.2'
author: 'Metalogic Labs · research discussion draft'
date: '9 October 2026'
fontsize: 10pt
geometry: margin=20mm
mainfont: DejaVu Serif
monofont: DejaVu Sans Mono
colorlinks: true
linkcolor: blue
linestretch: 1.05
---

## Abstract

This note presents one small formal core of *verified development*, deliberately separated from the wider programme in R6. The question is simple: **when can two states be treated as the same, and what exactly forces that identification to be revised?** An action changes a state, an observation records what must be preserved, and a declared stage identifies the actions whose outcomes matter. We define behavioural equivalence by the observations of those actions. A newly protected observation induces a canonical refinement. Finally, a checked, scoped certificate can establish a separator, classify an error residual, and force the relevant split.

The development is stated in Lean 4, using existing verified monoid-action and certificate foundations. **No finite-model games, Myhill–Nerode argument, or general grammar-invention claim is needed here.** The central integration and both an identity-only and non-identity example are checked by Lean 4.24.0, at the pinned commit and workflow listed below.

## 1. States, actions, and what is observed

We begin with **one state type `X`**, one action type `M`, and one observation function. The existing Lean type `ActionMonoid M X` defines the identity action, action composition, and their laws:

```lean
structure ActionMonoid (M : Type u) (X : Type v) where
  one : M
  mul : M → M → M
  act : M → X → X
  one_mul : ∀ a, mul one a = a
  mul_one : ∀ a, mul a one = a
  mul_assoc : ∀ a b c, mul (mul a b) c = mul a (mul b c)
  one_act : ∀ x, act one x = x
  mul_act : ∀ a b x, act (mul a b) x = act a (act b x)
```

This is a total deterministic action, not a probability distribution or a nondeterministic transition system. A *stage* names which actions' outcomes we undertake to preserve. It contains the identity and is closed under composition:

```lean
structure Stage (A : ActionMonoid M X) where
  allow : M → Prop
  one_allow : allow A.one
  mul_allow : ∀ g f, allow g → allow f → allow (A.mul g f)
```

An observation `obs : X → O` is the concrete value protected at a state. **The admissible stage is not the same thing as the actions an implementation happens to execute.** If we prune execution, we have not thereby proved that the omitted actions are irrelevant to the preservation contract.

## 2. Behavioural equivalence

Two states are equivalent *at the current stage* exactly when no allowed continuation gives different protected observations:

```lean
def BehEqAt (A : ActionMonoid M X) (S : Stage A)
    (obs : X → O) (x y : X) : Prop :=
  ∀ m, S.allow m → obs (A.act m x) = obs (A.act m y)
```

Reflexivity is immediate. The important structural fact is invariance: applying a protected action cannot invalidate an established equivalence. Here is the complete new Lean proof:

```lean
theorem behEqAt_invariant (A : ActionMonoid M X)
    (S : Stage A) (obs : X → O) {x y : X}
    (h : BehEqAt A S obs x y)
    (g : M) (hg : S.allow g) :
    BehEqAt A S obs (A.act g x) (A.act g y) := by
  intro m hm
  have hcomp := h (A.mul m g) (S.mul_allow m g hm hg)
  calc
    obs (A.act m (A.act g x)) =
        obs (A.act (A.mul m g) x) :=
          congrArg obs (A.mul_act m g x).symm
    _ = obs (A.act (A.mul m g) y) := hcomp
    _ = obs (A.act m (A.act g y)) :=
          congrArg obs (A.mul_act m g y)
```

The theorem `behEqAt_greatest` also proves the universal characterisation: **every stage-invariant relation compatible with the local observation is contained in `BehEqAt`**. The existing `BehaviouralCongruence.lean` separately constructs a quotient and proves that identity and composition descend to it (`descend_one`, `descend_mul`). For the stage-relative quotient and the later typed case, the already checked `DevelopmentalCategory.lean` provides `stageMap`, `stageMap_id`, and `stageMap_comp`.

We therefore do not assume a finite state space, a finite quotient, or an algorithm for computing this relation.

## 3. Refinement from a newly protected observation

Suppose `E` is the equivalence used by the current representation, and a new observation `d : X → D` becomes protected. We must not split pairs arbitrarily; the distinction is imposed by what the new observation can see **after every admitted action**.

```lean
def Refine {D : Type t} (A : ActionMonoid M X) (S : Stage A)
    (E : X → X → Prop) (d : X → D)
    (x y : X) : Prop :=
  E x y ∧
    ∀ m, S.allow m → d (A.act m x) = d (A.act m y)
```

`refine_greatest` proves that every stage-invariant subrelation of `E` respecting `d` is contained in this repair. The proof is short enough to show in full:

```lean
theorem refine_greatest {D : Type t}
    (A : ActionMonoid M X) (S : Stage A)
    (E R : X → X → Prop) (d : X → D)
    (hInv : InvariantAt A S R)
    (hSub : ∀ x y, R x y → E x y)
    (hD : ∀ x y, R x y → d x = d y) :
    ∀ x y, R x y → Refine A S E d x y := by
  intro x y hxy
  refine ⟨hSub x y hxy, ?_⟩
  intro m hm
  exact hD _ _ (hInv m hm x y hxy)
```

When `E` is itself stage-invariant, the repair also remains stage-invariant; that separate premise is necessary to call the repair the greatest *stage-invariant* compatible subrelation.

The full theorem and its hypotheses are in `lean/VerifiedDevelopmentCore.lean`. R7's previously verified `CanonicalRefinement.lean` also proves the typed analogue, including preservation of equivalence and stage-invariance when `E` is already stage-invariant.

A *separator* is an admitted action `m` for which the newly protected observations differ. The exact consequence is:

```lean
theorem separator_forces_split {D : Type t} (A : ActionMonoid M X)
    (S : Stage A) (E : X → X → Prop) (d : X → D)
    {x y : X} (hOld : E x y)
    (m : M) (hm : S.allow m)
    (hsep : d (A.act m x) ≠ d (A.act m y)) :
    E x y ∧ ¬ Refine A S E d x y := by
  refine ⟨hOld, ?_⟩
  intro hRef
  exact hsep (hRef.2 m hm)
```

This expresses a **required split**, not the discovery of a new syntax or a universally minimal implementation.

## 4. Scoped certificates, dependencies, and residuals

A claim is either a proposed merge or a witnessed separation. Each record has a claim, a scope, a checker result, and mandatory dependencies. The structure below makes those ingredients explicit:

```lean
inductive Claim (X : Type v) where
  | merge : X → X → Claim X
  | separate : X → X → Claim X

structure CertBank (A : ActionMonoid M X)
    (Record : Type q) (Scope : Type z) (O : Type w) where
  admitted : ScopeAdmission Scope M
  obs : X → O
  claim : Record → Claim X
  scope : Record → Scope
  check : Record → Prop
  depends : Record → Record → Prop
  checker_sound : ∀ r, check r →
    match claim r with
    | .merge x y =>
        MergeAt admitted A.act obs (scope r) x y
    | .separate x y =>
        SeparateAt admitted A.act obs (scope r) x y
```

**`checker_sound` is a premise of the structure.** Merely accepting a record does not magically prove its content: the instance must justify that checker acceptance implies the stated semantics. The `ScopeAdmission` relation records which actions belong to each scope and how admission grows. Its field `scopeLE σ τ` means **scope σ is included in scope τ** (σ ≤ τ), not that σ extends τ. This makes the variance of certificate authority unambiguous.

```lean
structure ScopeAdmission (Scope : Type v) (M : Type w) where
  scopeLE : Scope → Scope → Prop
  allows : Scope → M → Prop
  monotone : ∀ {σ τ}, scopeLE σ τ →
    ∀ m, allows σ m → allows τ m
```


A checked record is not sufficient if it relies on an unsupported dependency. The existing `ScopedCertificates.lean` uses the inductively generated predicate:

```lean
inductive Valid (check : Record → Prop)
    (depends : Record → Record → Prop) : Record → Prop where
  | admit (r : Record) (hc : check r)
      (hdeps : ∀ p, depends r p → Valid check depends p) :
      Valid check depends r
```

Its theorems `valid_fixed` and `valid_least` establish the **least** justification closure. Unsupported dependency cycles have no finite proof. `revoke_recloses` establishes that revoking a record retracts all records transitively dependent on it. Importantly, revoking *one certificate* does not prove that its claim becomes unknown if an independently valid alternative certificate exists.

A certificate of equality at a larger scope remains usable at a smaller scope; a certified separator at a smaller scope remains usable at a larger scope. The new integrated definitions enforce these directions. A merge record can be reused at σ only if `scopeLE σ (scope r)`; a separator record can be reused at σ only if `scopeLE (scope r) σ`:

```lean
def CertifiedMerge (A : ActionMonoid M X)
    (B : CertBank A Record Scope O)
    (σ : Scope) (x y : X) : Prop :=
  ∃ r, Valid B.check B.depends r ∧
    B.claim r = .merge x y ∧
    B.admitted.scopeLE σ (B.scope r)

def CertifiedSeparator (A : ActionMonoid M X)
    (B : CertBank A Record Scope O)
    (σ : Scope) (x y : X) : Prop :=
  ∃ r, Valid B.check B.depends r ∧
    B.claim r = .separate x y ∧
    B.admitted.scopeLE (B.scope r) σ
```

Consequently `certifiedMerge_sound` and `certifiedSeparator_sound` extract the corresponding semantic statements from **valid records with justified checker soundness**. `no_conflicting_certificates` proves a merge and separator cannot both be warranted for the same pair at the same scope.

The residual is *derived from the current relation and valid evidence*, rather than being another oracle:

```lean
def ErrorResidual (A : ActionMonoid M X)
    (B : CertBank A Record Scope O)
    (E : X → X → Prop)
    (σ : Scope) (x y : X) : Prop :=
  E x y ∧ CertifiedSeparator A B σ x y

def OpenResidual (A : ActionMonoid M X)
    (B : CertBank A Record Scope O)
    (E : X → X → Prop)
    (σ : Scope) (x y : X) : Prop :=
  E x y ∧ ¬ CertifiedSeparator A B σ x y ∧
    ¬ CertifiedMerge A B σ x y
```

**`OpenResidual` means no admitted certificate currently settles the pair. It is not a third semantic outcome, and it is not automatically decidable or enumerable for arbitrary types.**

## 5. The missing bridge is now an actual theorem

The previous R7 verified both refinement and certificate maintenance separately. R7.2 adds their direct connection. A certified separator establishes an error residual, and *if the certificate's scope is included in the stage being protected*, that residual forces a split:

```lean
theorem certified_error_forces_split
    (A : ActionMonoid M X) (S : Stage A)
    (B : CertBank A Record Scope O)
    (E : X → X → Prop)
    {σ : Scope} {x y : X}
    (hScope : ∀ m, B.admitted.allows σ m → S.allow m)
    (h : ErrorResidual A B E σ x y) :
    E x y ∧ ¬ Refine A S E B.obs x y := by
  rcases certifiedSeparator_sound A B h.2 with
    ⟨m, hm, hneq⟩
  exact separator_forces_split A S E B.obs h.1 m
    (hScope m hm) hneq
```

This is the precise point at which **checked evidence** entails a **change to the representation**. The `hScope` premise is essential: a separator outside the protected stage is not a licence to change the current stage-relative quotient.

## 6. One complete Lean-checked illustration

The file `lean/VerifiedDevelopmentExample.lean` fixes `X = Bool × Bool`. The first example has only the identity action (`M = Unit`). It isolates the certificate-to-refinement chain, but is deliberately degenerate: it cannot exercise non-identity action composition or a nontrivial scope-to-stage bridge. Consider two states:

```lean
def p : Bool × Bool := (true, false)
def q : Bool × Bool := (true, true)
def oldObs (x : Bool × Bool) : Bool := x.1
def newObs (x : Bool × Bool) : Bool := x.2
```

The old observation sees only the first coordinate, so `p` and `q` agree (`old_futures_agree`). A small `CertBank` carries a checked separator claiming they differ on `newObs`. In this toy instance, the checker's semantic soundness is **proved concretely** from `false ≠ true`; it is not assumed from an unverified external program. There are no dependencies, so the record is valid. The remaining Lean proofs are:

```lean
theorem toy_separator_certified :
    CertifiedSeparator toyAction toyBank () p q := by
  exact ⟨(), toy_record_valid, rfl, trivial⟩

theorem toy_error_residual :
    ErrorResidual toyAction toyBank oldRelation () p q := by
  exact ⟨old_states_merged, toy_separator_certified⟩

theorem toy_certified_split :
    oldRelation p q ∧
      ¬ Refine toyAction toyStage oldRelation newObs p q := by
  exact certified_error_forces_split toyAction toyStage
    toyBank oldRelation
    (by intro m hm; trivial) toy_error_residual
```

Thus one complete, finite, directly checkable chain is available:

**states → old observation → merge → checked scoped separator → error residual → required refinement split.**

This example demonstrates the composition of the definitions. It makes **no** claim about nontrivial search, grammar invention, or an unrestricted adequacy theorem.

### 6.1. A second test with an actual continuation

We therefore add a separate `Bool` action monoid. Its identity is `false`; `true` copies a hidden first bit to the observed second bit. Composition is Boolean OR. In particular, the revealing action is **non-identity**.

```lean
def revealAction : ActionMonoid Bool (Bool × Bool) where
  one := false
  mul := fun a b => a || b
  act := fun m x => if m then (x.1, x.1) else x
  one_mul := by intro a; cases a <;> rfl
  mul_one := by intro a; cases a <;> rfl
  mul_assoc := by intro a b c; cases a <;> cases b <;> cases c <;> rfl
  one_act := by intro x; rfl
  mul_act := by
    intro a b x
    rcases x with ⟨first, second⟩
    cases a <;> cases b <;> cases first <;> cases second <;> rfl
```

The states `before = (false,false)` and `after = (true,false)` initially have equal observable second coordinates. The original protected stage admits only `false`, so they are behaviourally equivalent there. The new scope admits `true`; its concrete checker soundness proves the separating witness. Crucially, `scope_not_in_original_stage` proves the bridge to the old stage is **false**, while `nontrivial_certified_split` proves the new full stage requires a split.

```lean
theorem identity_does_not_separate :
    visible (revealAction.act false before) =
      visible (revealAction.act false after) := by
  rfl

theorem actual_action_separates :
    visible (revealAction.act true before) ≠
      visible (revealAction.act true after) := by
  decide

theorem nontrivial_certified_split :
    visibleEq before after ∧
      ¬ Refine revealAction expandedStage
          visibleEq visible before after := by
  apply certified_error_forces_split revealAction expandedStage
    revealBank visibleEq
  · intro m hm
    trivial
  · exact reveal_error
```

This second example exercises the action law, actual continuation separation and the **necessary distinction** between a certificate's scope and the protected stage. Both examples are direct Lean tests, not a claim of automatic observation invention.

## 7. Verification, boundaries, and next discussion

The exact R7.2 source is in the [verified-development foundation branch](https://github.com/heathsanchez/Minimal-Sufficient-Interface/tree/verified-development-lean-foundations-v1). It reuses the earlier pinned files `BehaviouralCongruence.lean`, `ScopedCertificates.lean`, `TypedBehaviouralCongruence.lean`, `DevelopmentalCategory.lean`, and `CanonicalRefinement.lean`. The new files are [`VerifiedDevelopmentCore.lean`](https://github.com/heathsanchez/Minimal-Sufficient-Interface/blob/verified-development-lean-foundations-v1/lean/VerifiedDevelopmentCore.lean) and [`VerifiedDevelopmentExample.lean`](https://github.com/heathsanchez/Minimal-Sufficient-Interface/blob/verified-development-lean-foundations-v1/lean/VerifiedDevelopmentExample.lean). **Pinned new Lean authority:** [source commit `aa42b38fd2ec395370ce31ce1c1cc051f2b61373`](https://github.com/heathsanchez/Minimal-Sufficient-Interface/commit/aa42b38fd2ec395370ce31ce1c1cc051f2b61373) and [successful verification run 37846112492](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/37846112492), using Lean **4.24.0**. The [dedicated verified-development workflow](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/workflows/verified-development-lean-foundations.yml) compiles the elementary core, both examples, the scoped-certificate code and the previously checked typed extension. The predecessor [R7.1 exact-head qualification](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/37845384769) passed at `210b31e8cc8403bd005f9cf11fe11c01c1bff29b`. The current commit changes only manuscript wording; verify the new head as well before distributing this revision.

What is established **within these assumptions**: deterministic action semantics; a greatest observationally compatible stage-invariant relation; certified separation and its scope-direction rules; dependency reclosure; and the theorem connecting certified residuals to refinement. The complete executable finite example also checks.

What is **not** established: correctness of any arbitrary external checker; implementable termination for arbitrary infinite certificate sets; probabilistic, partial or nondeterministic actions; finite-index quotients; automated discovery of new observables; or existence of a unique lowest-cost language extension. Those questions belong to later work, not to this note.

**Question for mathematical review.** Is this minimal deterministic action/certificate structure the right foundational object? In particular, does the explicit `checker_sound` and scope-to-stage inclusion premise distinguish *semantic truth* from *available evidence* well enough? `MergeAt` is antitone and `SeparateAt` is monotone under scope inclusion. This suggests a potential presheaf/copresheaf formulation (as scope-indexed proposition-valued assignments), but no such categorical formulation is claimed here.

---

*Research lineage:* R6 (5 October 2026) is retained unchanged as the broad synthesis. R7 established the Lean refinements and dependency-maintenance theorems. R7.2 isolates their elementary explanation and adds the checked, certificate-to-residual-to-refinement bridge. Myhill–Nerode, finite-model games and categorical generalisations are deliberately deferred from the presentation.