import Std
import ConstitutionalFailedFactorization

namespace ConstitutionalRealizationAndRecursion

open ConstitutionalFailedFactorization

abbrev Constitution := Bool × Bool

def authority (p : Constitution) : Bool := p.1

def audit (p : Constitution) : Bool := p.2

def xorRealizer (p : Constitution) : Bool := Bool.xor p.1 p.2

def directInterface (p : Constitution) : Bool × Bool := (authority p, audit p)

def xorInterface (p : Constitution) : Bool × Bool := (authority p, xorRealizer p)

/-- The finite census witness has two different concrete interfaces with the
    same kernel.  The proof is exhaustive over the four constitutions. -/
theorem direct_and_xor_realize_same_quotient :
    KernelEq directInterface = KernelEq xorInterface := by
  funext x y
  apply propext
  cases x with
  | mk xa xb =>
    cases y with
    | mk ya yb =>
      cases xa <;> cases xb <;> cases ya <;> cases yb <;>
        simp [KernelEq, directInterface, xorInterface, authority, audit, xorRealizer]

/-- The two realizations are not the same concrete interface. -/
theorem realizations_are_distinct : directInterface ≠ xorInterface := by
  intro h
  have hpair := congrFun h (true, true)
  simp [directInterface, xorInterface, authority, audit, xorRealizer] at hpair

/-- In the direct realization the protected audit decision is literally the
    added coordinate. -/
theorem audit_is_direct_coordinate :
    ∀ p : Constitution, audit p = (directInterface p).2 := by
  intro p
  rfl

/-- In the XOR realization the future XOR decision is literally the added
    coordinate. -/
theorem xor_is_xor_coordinate :
    ∀ p : Constitution, xorRealizer p = (xorInterface p).2 := by
  intro p
  rfl

/-- The audit decision is not a deterministic post-processing of the old
    authority interface.  This is a concrete failed-factorization witness. -/
theorem audit_not_from_authority :
    ¬ ∃ g : Bool → Bool, ∀ p : Constitution, audit p = g (authority p) := by
  apply failed_factorization authority audit (p₁ := (false, false)) (p₂ := (false, true))
  · rfl
  · decide

/-- Likewise the future XOR decision is not a deterministic post-processing
    of the old authority interface. -/
theorem xor_not_from_authority :
    ¬ ∃ g : Bool → Bool, ∀ p : Constitution, xorRealizer p = g (authority p) := by
  apply failed_factorization authority xorRealizer (p₁ := (false, false)) (p₂ := (false, true))
  · rfl
  · decide

/-- Therefore the abstract quotient required by the protected audit decision
    can be realized by at least two distinct concrete interfaces. -/
theorem finite_realization_multiplicity :
    directInterface ≠ xorInterface ∧
    KernelEq directInterface = KernelEq xorInterface := by
  exact ⟨realizations_are_distinct, direct_and_xor_realize_same_quotient⟩

/-! ## Higher-order D-of-D recursion -/

def StrictRefines {P : Type} (R S : P → P → Prop) : Prop :=
  Refines R S ∧ ¬ Refines S R

/-- Strict refinement is asymmetric.  Hence a monotone meet-only
    constitutional update cannot immediately cycle. -/
theorem strictRefines_asymm {P : Type} {R S : P → P → Prop}
    (h : StrictRefines R S) : ¬ StrictRefines S R := by
  intro hrev
  exact h.2 hrev.1

/-- Strict refinement is transitive. -/
theorem strictRefines_trans {P : Type} {R S T : P → P → Prop}
    (hRS : StrictRefines R S) (hST : StrictRefines S T) :
    StrictRefines R T := by
  constructor
  · intro x y hxy
    exact hST.1 (hRS.1 hxy)
  · intro hTR
    apply hST.2
    intro x y hxy
    exact hRS.1 (hTR hxy)

/-- A strict monotone constitutional-refinement chain cannot return to an
    earlier representation. -/
theorem strict_refinement_no_cycle {P : Type} {R S : P → P → Prop}
    (hRS : StrictRefines R S) : ¬ Refines S R := by
  exact hRS.2

/-! ## General fixed-point laws for canonical constitutional repair -/

/-- Add one decision kernel to an already constructed relation. -/
def AddDecision {P : Type} {A : Type} (R : P → P → Prop) (D : P → A) :
    P → P → Prop :=
  fun x y => R x y ∧ D x = D y

/-- Replaying any already protected decision after canonical repair is
    idempotent: it cannot refine the representation again. -/
theorem canonical_repair_idempotent
    {P : Type} {E : Type} {Q : Type} {A : Q → Type}
    (I : P → E) (D : (q : Q) → P → A q) (q : Q) :
    AddDecision (ConstitutionalRefinement I D) (D q) =
      ConstitutionalRefinement I D := by
  funext x y
  apply propext
  constructor
  · intro h
    exact h.1
  · intro h
    exact ⟨h, h.2 q⟩

/-- More generally, replaying any subfamily of the already protected decisions
    is idempotent after canonical repair. -/
theorem canonical_repair_subfamily_idempotent
    {P : Type} {E : Type} {Q : Type} {A : Q → Type}
    (I : P → E) (D : (q : Q) → P → A q) (S : Q → Prop) :
    (fun x y => ConstitutionalRefinement I D x y ∧
      ∀ q, S q → D q x = D q y) =
      ConstitutionalRefinement I D := by
  funext x y
  apply propext
  constructor
  · intro h
    exact h.1
  · intro h
    exact ⟨h, fun q _ => h.2 q⟩

/-- If a candidate higher-order decision is already determined on every class
    of the canonical repair, adding it cannot cause another refinement. -/
theorem determined_new_decision_is_fixed_point
    {P : Type} {E : Type} {Q : Type} {A : Q → Type} {B : Type}
    (I : P → E) (D : (q : Q) → P → A q) (Dstar : P → B)
    (hdet : Refines (ConstitutionalRefinement I D) (KernelEq Dstar)) :
    AddDecision (ConstitutionalRefinement I D) Dstar =
      ConstitutionalRefinement I D := by
  funext x y
  apply propext
  constructor
  · intro h
    exact h.1
  · intro h
    exact ⟨h, hdet h⟩

/-- Conversely, failure of a new higher-order decision to be determined by the
    repaired representation has an explicit residual pair: two constitutions
    still identified by the repair but separated by the new decision. -/
theorem new_decision_insufficiency_has_residual
    {P : Type} {E : Type} {Q : Type} {A : Q → Type} {B : Type}
    (I : P → E) (D : (q : Q) → P → A q) (Dstar : P → B)
    (hnew : ¬ Refines (ConstitutionalRefinement I D) (KernelEq Dstar)) :
    ∃ x y, ConstitutionalRefinement I D x y ∧ Dstar x ≠ Dstar y := by
  classical
  apply Classical.byContradiction
  intro hn
  apply hnew
  intro x y hxy
  apply Classical.byContradiction
  intro hneq
  apply hn
  exact ⟨x, y, hxy, hneq⟩

/-- A genuine residual for a new higher-order decision forces strict further
    refinement when that decision is adjoined. -/
theorem new_residual_forces_strict_refinement
    {P : Type} {E : Type} {Q : Type} {A : Q → Type} {B : Type}
    (I : P → E) (D : (q : Q) → P → A q) (Dstar : P → B)
    {x y : P}
    (hrepair : ConstitutionalRefinement I D x y)
    (hstar : Dstar x ≠ Dstar y) :
    StrictRefines
      (AddDecision (ConstitutionalRefinement I D) Dstar)
      (ConstitutionalRefinement I D) := by
  constructor
  · intro a b h
    exact h.1
  · intro hback
    have hadded := hback hrepair
    exact hstar hadded.2

/-- Exact characterization: adjoining a new higher-order decision strictly
    refines the canonical repair iff that decision contributes a distinction
    absent from the repaired interface. -/
theorem strict_further_refinement_iff_new_distinction
    {P : Type} {E : Type} {Q : Type} {A : Q → Type} {B : Type}
    (I : P → E) (D : (q : Q) → P → A q) (Dstar : P → B) :
    StrictRefines
      (AddDecision (ConstitutionalRefinement I D) Dstar)
      (ConstitutionalRefinement I D) ↔
    ∃ x y, ConstitutionalRefinement I D x y ∧ Dstar x ≠ Dstar y := by
  constructor
  · intro hstrict
    classical
    apply Classical.byContradiction
    intro hn
    apply hstrict.2
    intro x y hxy
    refine ⟨hxy, ?_⟩
    apply Classical.byContradiction
    intro hneq
    apply hn
    exact ⟨x, y, hxy, hneq⟩
  · intro hex
    rcases hex with ⟨x, y, hxy, hneq⟩
    exact new_residual_forces_strict_refinement I D Dstar hxy hneq

/-- A three-level finite hierarchy.  Level 0 observes only authority.  Level 1
    adds the protected audit decision.  Level 2 asks whether another protected
    decision (XOR) forces a further quotient refinement. -/
def E0 : Constitution → Constitution → Prop := KernelEq authority

def E1 : Constitution → Constitution → Prop :=
  fun x y => authority x = authority y ∧ audit x = audit y

def E2 : Constitution → Constitution → Prop :=
  fun x y => E1 x y ∧ xorRealizer x = xorRealizer y

/-- The first higher-order protection forces a strict refinement. -/
theorem level1_strictly_refines_level0 : StrictRefines E1 E0 := by
  constructor
  · intro x y h
    exact h.1
  · intro h
    have bad := h (x := (false, false)) (y := (false, true)) rfl
    exact Bool.noConfusion bad.2

/-- Once authority and audit are retained, XOR adds no new quotient
    distinction: the hierarchy has reached a fixed point at the representation
    level for this protected family. -/
theorem level2_is_fixed_point : E2 = E1 := by
  funext x y
  apply propext
  constructor
  · intro h
    exact h.1
  · intro h
    refine ⟨h, ?_⟩
    cases x with
    | mk xa xb =>
      cases y with
      | mk ya yb =>
        simp [E1, authority, audit] at h
        rcases h with ⟨rfl, rfl⟩
        rfl

/-- Concrete finite D-of-D certificate for this hierarchy: a strict first
    refinement is followed by a representation-level fixed point; no return
    to the coarser representation is compatible with monotone refinement. -/
theorem finite_higher_order_recursion_certificate :
    StrictRefines E1 E0 ∧ E2 = E1 ∧ ¬ Refines E0 E1 := by
  exact ⟨level1_strictly_refines_level0, level2_is_fixed_point,
    level1_strictly_refines_level0.2⟩

end ConstitutionalRealizationAndRecursion
