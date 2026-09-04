import Std
import ConstitutionalRealizationAndRecursion

/-! # Genuine Test 3A — policies as Residual → RepairAction functions

  SUPERSEDES `PolicyReflexivity.lean`, which only proved the polymorphic PROXY:
  two output relations relabelled as "policies".  Here a Policy is genuinely a
  function that selects a repair ACTION, and the two candidates differ on an
  inexpressible residual:

    P0(ρ) = representation
    P1(ρ) = representation  if Expressible(ρ)
            capability     otherwise

  The criterion that selects P1 is NOT defined as P1.  It is anchored in the
  already-proved `failed_factorization` / `postprocessing_cannot_split`:
  a representation repair (deterministic post-processing of the interface)
  cannot split a fibre the interface already collapses.  So on an inexpressible
  forced residual, representation repair is provably insufficient and capability
  repair is required.
-/

namespace GenuinePolicyReflexivity

open ConstitutionalRealizationAndRecursion
open ConstitutionalFailedFactorization

inductive RepairAction | representation | capability
  deriving DecidableEq, Repr

structure Residual (P : Type) where
  x : P
  y : P

abbrev Policy (P : Type) := Residual P → RepairAction

/-- Expressible: the interface already separates the residual pair. -/
abbrev Expressible {P E : Type} (I : P → E) (ρ : Residual P) : Prop :=
  I ρ.x ≠ I ρ.y

/-- P0: always representation repair. -/
def P0 {P : Type} : Policy P := fun _ => RepairAction.representation

/-- P1: representation iff expressible, else capability. -/
def P1 {P E : Type} [DecidableEq E] (I : P → E) : Policy P :=
  fun ρ => if Expressible I ρ then RepairAction.representation else RepairAction.capability

/- Concrete witness on the Bool × Bool constitution (imported). -/
abbrev Car := Constitution

def I : Car → Bool := authority

def ρ : Residual Car := ⟨(false, false), (false, true)⟩

/- ρ is inexpressible: the authority interface identifies its two points. -/
theorem rho_inexpressible : ¬ Expressible I ρ := by
  decide

/- ρ is forced: the audit decision separates its two points. -/
theorem rho_forced : audit ρ.x ≠ audit ρ.y := by
  decide

/- Semantics: capability repair = adjoining the forced decision (audit).
   Representation repair = any deterministic post-processing `g ∘ I` of the
   interface. -/

def capabilityRepair : Car → Car → Prop := AddDecision (KernelEq I) audit

def Identifies (R : Car → Car → Prop) (r : Residual Car) : Prop := R r.x r.y

/- No representation repair separates ρ: every post-processing of I still
   identifies the pair I collapses.  Concrete instantiation of
   `postprocessing_cannot_split`. -/
theorem representation_repairs_identify_rho (g : Bool → Bool) :
    Identifies (KernelEq (g ∘ I)) ρ := by
  unfold Identifies KernelEq
  exact congrArg g (by decide)

/- Capability repair separates ρ. -/
theorem capability_separates_rho : ¬ Identifies capabilityRepair ρ := by
  unfold Identifies capabilityRepair AddDecision
  intro h
  have haudit : audit ρ.x = audit ρ.y := h.2
  simp [audit, ρ] at haudit

/- The criterion: representation identifies ρ (insufficient, for EVERY
   post-processing), capability separates it (sufficient). -/
theorem criterion_prefers_capability_on_rho :
    (∀ g : Bool → Bool, Identifies (KernelEq (g ∘ I)) ρ) ∧
    ¬ Identifies capabilityRepair ρ := by
  exact ⟨representation_repairs_identify_rho, capability_separates_rho⟩

/- SameContinuationBefore: on expressible residuals the two policies agree. -/
theorem same_before (r : Residual Car) (hexp : Expressible I r) :
    P0 r = P1 I r := by
  simp [P0, P1, hexp]

/- DifferentRepairAfter: on the inexpressible forced residual they differ. -/
theorem different_after : P0 ρ ≠ P1 I ρ := by
  simp [P0, P1, rho_inexpressible]

/- GenericCriterionPrefers: P1 selects the sufficient action (capability) and
   P0 the insufficient one (representation), grounded in
   postprocessing_cannot_split — NOT obtained by unfolding P1 into the
   criterion. -/
theorem generic_prefers :
    P1 I ρ = RepairAction.capability ∧
    ¬ Identifies capabilityRepair ρ ∧
    P0 ρ = RepairAction.representation ∧
    (∀ g : Bool → Bool, Identifies (KernelEq (g ∘ I)) ρ) := by
  constructor
  · unfold P1
    exact if_neg rho_inexpressible
  constructor
  · exact capability_separates_rho
  constructor
  · rfl
  · exact representation_repairs_identify_rho

end GenuinePolicyReflexivity
