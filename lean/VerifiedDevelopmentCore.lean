import BehaviouralCongruence
import ScopedCertificates

/-!
R7.1: single-state Lean-first explanation for Daniel.
Uses only the pinned monoid action and scoped-certificate kernel.
The typed/categorical theorems remain in R7.
No axioms, sorry, Mathlib, games, or automata.
-/

universe u v w z q t

namespace VerifiedDevelopmentCore

open ScopedCertificates

variable {M : Type u} {X : Type v} {O : Type w}

/-- Only admitted futures determine behavioural identity. -/
structure Stage (A : ActionMonoid M X) where
  allow : M → Prop
  one_allow : allow A.one
  mul_allow : ∀ g f, allow g → allow f → allow (A.mul g f)

/-- Two states are equivalent if each admitted future has equal observations. -/
def BehEqAt (A : ActionMonoid M X) (S : Stage A)
    (obs : X → O) (x y : X) : Prop :=
  ∀ m, S.allow m → obs (A.act m x) = obs (A.act m y)

theorem behEqAt_refl (A : ActionMonoid M X) (S : Stage A)
    (obs : X → O) (x : X) : BehEqAt A S obs x x := by
  intro m hm
  rfl

/-- Once equal, two states remain equal after an admitted action. -/
theorem behEqAt_invariant (A : ActionMonoid M X) (S : Stage A)
    (obs : X → O) {x y : X}
    (h : BehEqAt A S obs x y) (g : M) (hg : S.allow g) :
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

/-- A relation is stage-invariant when every admitted action respects it. -/
def InvariantAt (A : ActionMonoid M X) (S : Stage A)
    (E : X → X → Prop) : Prop :=
  ∀ g, S.allow g → ∀ x y, E x y → E (A.act g x) (A.act g y)

/-- Behavioural equality contains every invariant, observation-compatible relation. -/
theorem behEqAt_greatest (A : ActionMonoid M X) (S : Stage A)
    (obs : X → O) (E : X → X → Prop)
    (hInv : InvariantAt A S E)
    (hObs : ∀ x y, E x y → obs x = obs y) :
    ∀ x y, E x y → BehEqAt A S obs x y := by
  intro x y hxy m hm
  exact hObs _ _ (hInv m hm x y hxy)

/-- Canonical repair: keep E, but protect a new observation after each future. -/
def Refine {D : Type t} (A : ActionMonoid M X) (S : Stage A)
    (E : X → X → Prop) (d : X → D) (x y : X) : Prop :=
  E x y ∧ ∀ m, S.allow m → d (A.act m x) = d (A.act m y)

/-- Every invariant relation preserving d is included in the canonical repair. -/
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

/-- A witnessed distinction necessarily splits any class that contained the pair. -/
theorem separator_forces_split {D : Type t}
    (A : ActionMonoid M X) (S : Stage A)
    (E : X → X → Prop) (d : X → D)
    {x y : X} (hOld : E x y)
    (m : M) (hm : S.allow m)
    (hsep : d (A.act m x) ≠ d (A.act m y)) :
    E x y ∧ ¬ Refine A S E d x y := by
  refine ⟨hOld, ?_⟩
  intro hRef
  exact hsep (hRef.2 m hm)

/-- The record's claim: a merge or an explicit separating observation. -/
inductive Claim (X : Type v) where
  | merge : X → X → Claim X
  | separate : X → X → Claim X

/-- Checker semantics are an EXPLICIT assumption, never derived from check=true. -/
structure CertBank (A : ActionMonoid M X) (Record : Type q)
    (Scope : Type z) (O : Type w) where
  admitted : ScopeAdmission Scope M
  obs : X → O
  claim : Record → Claim X
  scope : Record → Scope
  check : Record → Prop
  depends : Record → Record → Prop
  checker_sound : ∀ r, check r →
    match claim r with
    | .merge x y => MergeAt admitted A.act obs (scope r) x y
    | .separate x y => SeparateAt admitted A.act obs (scope r) x y

/-- A merge is warranted only by a valid record scoped at least as broadly. -/
def CertifiedMerge {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    (σ : Scope) (x y : X) : Prop :=
  ∃ r, Valid B.check B.depends r ∧
    B.claim r = .merge x y ∧ B.admitted.scopeLE σ (B.scope r)

/-- A separator is warranted only by a valid record available at this scope. -/
def CertifiedSeparator {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    (σ : Scope) (x y : X) : Prop :=
  ∃ r, Valid B.check B.depends r ∧
    B.claim r = .separate x y ∧ B.admitted.scopeLE (B.scope r) σ

/-- Recover the meaning of a certificate, using its DECLARED soundness premise. -/
theorem certifiedMerge_sound {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    {σ : Scope} {x y : X}
    (h : CertifiedMerge A B σ x y) :
    MergeAt B.admitted A.act B.obs σ x y := by
  rcases h with ⟨r, hv, hc, hs⟩
  have hcheck := valid_checked B.check B.depends hv
  have hsem := B.checker_sound r hcheck
  rw [hc] at hsem
  exact merge_restrict B.admitted A.act B.obs hs hsem

theorem certifiedSeparator_sound {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    {σ : Scope} {x y : X}
    (h : CertifiedSeparator A B σ x y) :
    SeparateAt B.admitted A.act B.obs σ x y := by
  rcases h with ⟨r, hv, hc, hs⟩
  have hcheck := valid_checked B.check B.depends hv
  have hsem := B.checker_sound r hcheck
  rw [hc] at hsem
  exact separator_extend B.admitted A.act B.obs hs hsem

/-- Sound checker evidence cannot simultaneously merge and split the same pair. -/
theorem no_conflicting_certificates {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    {σ : Scope} {x y : X}
    (hm : CertifiedMerge A B σ x y)
    (hs : CertifiedSeparator A B σ x y) : False := by
  have hm' := certifiedMerge_sound A B hm
  rcases certifiedSeparator_sound A B hs with ⟨m, hmScope, hneq⟩
  exact hneq (hm' m hmScope)

/-- The residual is derived from E and current verified evidence. -/
def ErrorResidual {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    (E : X → X → Prop) (σ : Scope) (x y : X) : Prop :=
  E x y ∧ CertifiedSeparator A B σ x y

def OpenResidual {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    (E : X → X → Prop) (σ : Scope) (x y : X) : Prop :=
  E x y ∧ ¬ CertifiedSeparator A B σ x y ∧
    ¬ CertifiedMerge A B σ x y

/-- Crucial connection: a certified error forces a canonical refinement split. -/
theorem certified_error_forces_split {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (S : Stage A)
    (B : CertBank A Record Scope O) (E : X → X → Prop)
    {σ : Scope} {x y : X}
    (hScope : ∀ m, B.admitted.allows σ m → S.allow m)
    (h : ErrorResidual A B E σ x y) :
    E x y ∧ ¬ Refine A S E B.obs x y := by
  rcases certifiedSeparator_sound A B h.2 with ⟨m, hm, hneq⟩
  exact separator_forces_split A S E B.obs h.1 m (hScope m hm) hneq

/-- Revocation retracts each dependent record; independent alternate
    certificates, if any, may still warrant the same semantic claim. -/
theorem dependent_record_retracted {Record : Type q} {Scope : Type z}
    (A : ActionMonoid M X) (B : CertBank A Record Scope O)
    (r revoked : Record) (path : Reaches B.depends r revoked) :
    ¬ Valid (revoke B.check revoked) B.depends r :=
  revoke_recloses B.check B.depends revoked r path

end VerifiedDevelopmentCore
