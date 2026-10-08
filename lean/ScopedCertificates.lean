import Std

/-!
R7: certificate dependency closure and scope authority.
Validity is an inductive LEAST fixed point of checked base claims plus mandatory
dependencies. A syntactic checker predicate is deliberately not assumed sound.
-/

universe u v w z

namespace ScopedCertificates

variable {Record : Type u}

/-- A record is eligible when externally checked and all dependencies are in W. -/
def Gamma (check : Record → Prop) (depends : Record → Record → Prop)
    (W : Record → Prop) (r : Record) : Prop :=
  check r ∧ ∀ p, depends r p → W p

/-- Inductively generated validity excludes unsupported dependency cycles. -/
inductive Valid (check : Record → Prop) (depends : Record → Record → Prop) :
    Record → Prop where
  | admit (r : Record) (hc : check r)
      (hdeps : ∀ p, depends r p → Valid check depends p) :
      Valid check depends r

/-- Validity is a fixed point of the exact one-step consequence operator. -/
theorem valid_fixed (check : Record → Prop) (depends : Record → Record → Prop)
    (r : Record) :
    Valid check depends r ↔ Gamma check depends (Valid check depends) r := by
  constructor
  · intro h
    cases h with
    | admit _ hc hd => exact ⟨hc, hd⟩
  · rintro ⟨hc, hd⟩
    exact Valid.admit r hc hd

/-- Valid is the least pre-fixed point; no ungrounded cycle is admitted. -/
theorem valid_least (check : Record → Prop) (depends : Record → Record → Prop)
    (W : Record → Prop)
    (hClosed : ∀ r, Gamma check depends W r → W r) :
    ∀ r, Valid check depends r → W r := by
  intro r h
  induction h with
  | admit r hc hd ih =>
    exact hClosed r ⟨hc, by intro p hp; exact ih p hp⟩

theorem valid_checked (check : Record → Prop) (depends : Record → Record → Prop)
    {r : Record} (h : Valid check depends r) : check r := by
  cases h with
  | admit _ hc _ => exact hc

theorem valid_dependency (check : Record → Prop) (depends : Record → Record → Prop)
    {r p : Record} (h : Valid check depends r) (hp : depends r p) :
    Valid check depends p := by
  cases h with
  | admit _ _ hd => exact hd p hp

/-- Dependencies may be arbitrarily many links away from the record. -/
inductive Reaches (depends : Record → Record → Prop) :
    Record → Record → Prop where
  | direct {r p} (h : depends r p) : Reaches depends r p
  | next {r p q} (h : depends r p) (tail : Reaches depends p q) :
      Reaches depends r q

theorem reaches_valid (check : Record → Prop) (depends : Record → Record → Prop)
    {r p : Record} (path : Reaches depends r p) :
    Valid check depends r → Valid check depends p := by
  intro hv
  induction path with
  | direct hp =>
    exact valid_dependency check depends hv hp
  | next hp tail ih =>
    exact ih (valid_dependency check depends hv hp)

/-- REVOKE invalidates the checker premise for one selected record. -/
def revoke (check : Record → Prop) (revoked r : Record) : Prop :=
  check r ∧ r ≠ revoked

/-- The revoked record cannot remain warranted after reclosure. -/
theorem revoke_self (check : Record → Prop) (depends : Record → Record → Prop)
    (r : Record) : ¬ Valid (revoke check r) depends r := by
  intro hv
  have hc := valid_checked (revoke check r) depends hv
  exact hc.2 rfl

/-- Every transitive mandatory dependent is withdrawn after the revocation.
    No claim is made about operational execution or external-checker soundness. -/
theorem revoke_recloses (check : Record → Prop) (depends : Record → Record → Prop)
    (revoked r : Record) (path : Reaches depends r revoked) :
    ¬ Valid (revoke check revoked) depends r := by
  intro hv
  exact revoke_self check depends revoked
    (reaches_valid (revoke check revoked) depends path hv)

/-- Shrinking the checked record set can only shrink the inductive validity set. -/
theorem check_shrink (checkNew checkOld : Record → Prop)
    (depends : Record → Record → Prop)
    (hSub : ∀ r, checkNew r → checkOld r) :
    ∀ r, Valid checkNew depends r → Valid checkOld depends r := by
  intro r hv
  induction hv with
  | admit r hc hd ih =>
    exact Valid.admit r (hSub r hc) (by intro p hp; exact ih p hp)

/-- The two disjoint residual components are derived, not independent truth. -/
def Err {X : Type v} (E separated : X → X → Prop) (x y : X) : Prop :=
  E x y ∧ separated x y

def Open {X : Type v} (E separated merged : X → X → Prop)
    (x y : X) : Prop :=
  E x y ∧ ¬ separated x y ∧ ¬ merged x y

theorem err_open_disjoint {X : Type v}
    (E separated merged : X → X → Prop) (x y : X) :
    ¬ (Err E separated x y ∧ Open E separated merged x y) := by
  rintro ⟨herr, hopen⟩
  exact hopen.2.1 herr.2

/-- A scope declares admitted continuations and a monotone extension contract. -/
structure ScopeAdmission (Scope : Type v) (M : Type w) where
  extendsScope : Scope → Scope → Prop
  allows : Scope → M → Prop
  monotone : ∀ {σ τ}, extendsScope σ τ → ∀ m, allows σ m → allows τ m

variable {Scope : Type v} {M : Type w} {X : Type z} {O : Type u}

/-- A merge certificate establishes agreement for all futures in its scope. -/
def MergeAt (S : ScopeAdmission Scope M) (act : M → X → X) (obs : X → O)
    (σ : Scope) (x y : X) : Prop :=
  ∀ m, S.allows σ m → obs (act m x) = obs (act m y)

/-- A separator identifies an admitted future with different observations. -/
def SeparateAt (S : ScopeAdmission Scope M) (act : M → X → X) (obs : X → O)
    (σ : Scope) (x y : X) : Prop :=
  ∃ m, S.allows σ m ∧ obs (act m x) ≠ obs (act m y)

/-- Larger-scope merge evidence is reusable at a smaller scope. -/
theorem merge_restrict (S : ScopeAdmission Scope M)
    (act : M → X → X) (obs : X → O)
    {σ τ : Scope} (hExt : S.extendsScope σ τ) {x y : X}
    (h : MergeAt S act obs τ x y) : MergeAt S act obs σ x y := by
  intro m hm
  exact h m (S.monotone hExt m hm)

/-- A witnessed separator remains a separator at every larger scope. -/
theorem separator_extend (S : ScopeAdmission Scope M)
    (act : M → X → X) (obs : X → O)
    {σ τ : Scope} (hExt : S.extendsScope σ τ) {x y : X}
    (h : SeparateAt S act obs σ x y) : SeparateAt S act obs τ x y := by
  rcases h with ⟨m, hm, hneq⟩
  exact ⟨m, S.monotone hExt m hm, hneq⟩

end ScopedCertificates
