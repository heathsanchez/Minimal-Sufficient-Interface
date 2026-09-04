import Std
import ConstitutionalRealizationAndRecursion

/-! # Genuine Test 3A — HARDENED: policy-independent criterion + ablation

  Policy is a function `Residual → RepairAction`, not an output relation.

  This hardened version closes two remaining loopholes:

  1. Representation-inadequacy is quantified over ARBITRARY post-processing
     codomains `g : Bool → E'` (not just `Bool → Bool`), so no fixed-codomain
     assumption survives into 3B.

  2. The selecting criterion is factored into policy-independent layers:
     `Adequate D ρ a` (does action `a`'s repair separate the forced
     distinction?), `PreferredAction` (the adequate action), and
     `PolicyFits D P ρ := PreferredAction D ρ (P ρ)`.  None of these mentions
     P0 or P1, so the discrimination is not "true by construction".

  The four theorems below: (1) generalized representation-inadequacy,
  (2) adequacy criterion, (3) generic discrimination P1 vs P0, (4) ablation —
  when the forced distinction disappears, so does the preference.
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

abbrev Expressible {P E : Type} (I : P → E) (ρ : Residual P) : Prop :=
  I ρ.x ≠ I ρ.y

def P0 {P : Type} : Policy P := fun _ => RepairAction.representation

def P1 {P E : Type} [DecidableEq E] (I : P → E) : Policy P :=
  fun ρ => if Expressible I ρ then RepairAction.representation else RepairAction.capability

/- Concrete witness on the Bool × Bool constitution. -/
abbrev Car := Constitution

def I : Car → Bool := authority

def ρ : Residual Car := ⟨(false, false), (false, true)⟩

theorem rho_inexpressible : ¬ Expressible I ρ := by
  decide

theorem rho_forced : audit ρ.x ≠ audit ρ.y := by
  decide

def Identifies (R : Car → Car → Prop) (r : Residual Car) : Prop := R r.x r.y

/- (1) GENERALIZED representation-inadequacy: for ANY codomain E', no
   post-processing `g : Bool → E'` of the interface separates the collapsed
   residual.  Direct instantiation of `postprocessing_cannot_split`. -/
theorem representation_repairs_identify_rho {E' : Type} (g : Bool → E') :
    Identifies (KernelEq (g ∘ I)) ρ := by
  unfold Identifies
  exact (postprocessing_cannot_split I g) (by simp [KernelEq, I, authority, ρ])

/- Capability repair, parametrized by the forced decision D. -/
def capabilityRepairWith (D : Car → Bool) : Car → Car → Prop :=
  AddDecision (KernelEq I) D

/- The repair relation each action produces, given forced decision D. -/
def actionRepairWith (D : Car → Bool) : RepairAction → Car → Car → Prop
  | .representation => KernelEq I
  | .capability     => capabilityRepairWith D

/- (2) Policy-independent adequacy: action `a` is adequate for ρ iff its repair
   separates ρ's forced distinction.  No mention of P0/P1. -/
def Adequate (D : Car → Bool) (ρ : Residual Car) (a : RepairAction) : Prop :=
  ¬ Identifies (actionRepairWith D a) ρ

/- The criterion: prefer the adequate action (for a two-action world adequacy
   already determines the preference; the layer is kept explicit so the
   criterion never references a policy). -/
def PreferredAction (D : Car → Bool) (ρ : Residual Car) (a : RepairAction) : Prop :=
  Adequate D ρ a

/- A policy fits a residual iff its chosen action is preferred. -/
def PolicyFits (D : Car → Bool) (P : Policy Car) (ρ : Residual Car) : Prop :=
  PreferredAction D ρ (P ρ)

/- Capability repair (with the real forced decision audit) separates ρ. -/
theorem capability_separates_rho : ¬ Identifies (capabilityRepairWith audit) ρ := by
  unfold Identifies capabilityRepairWith AddDecision
  intro h
  have haudit : audit ρ.x = audit ρ.y := h.2
  simp [audit, ρ] at haudit

/- Capability is adequate for ρ; representation is not. -/
theorem capability_adequate : Adequate audit ρ .capability := by
  unfold Adequate actionRepairWith
  exact capability_separates_rho

theorem representation_inadequate : ¬ Adequate audit ρ .representation := by
  intro h
  unfold Adequate actionRepairWith at h
  apply h
  unfold Identifies KernelEq
  decide

/- (3) Generic policy discrimination: P1 fits and P0 does not, proved by the
   policy-independent criterion with no reference to P1 inside it. -/
theorem policy_discrimination :
    PolicyFits audit (P1 I) ρ ∧ ¬ PolicyFits audit P0 ρ := by
  constructor
  · have hP1 : P1 I ρ = RepairAction.capability := by
      unfold P1
      exact if_neg rho_inexpressible
    unfold PolicyFits PreferredAction
    rw [hP1]
    exact capability_adequate
  · intro h
    have hP0 : P0 ρ = RepairAction.representation := rfl
    unfold PolicyFits PreferredAction at h
    rw [hP0] at h
    exact representation_inadequate h

/- (4) Ablation: with a trivial (non-distinguishing) forced decision, capability
   is no longer adequate, so the preference for P1 disappears. -/
def trivialDecision : Car → Bool := fun _ => true

theorem capability_inadequate_without_distinction :
    ¬ Adequate trivialDecision ρ .capability := by
  intro h
  unfold Adequate actionRepairWith at h
  apply h
  unfold Identifies capabilityRepairWith AddDecision
  constructor
  · unfold KernelEq
    decide
  · rfl

theorem ablation :
    (PolicyFits audit (P1 I) ρ ∧ ¬ PolicyFits audit P0 ρ) ∧
    ¬ PolicyFits trivialDecision (P1 I) ρ := by
  constructor
  · exact policy_discrimination
  · intro h
    have hP1 : P1 I ρ = RepairAction.capability := by
      unfold P1
      exact if_neg rho_inexpressible
    unfold PolicyFits PreferredAction at h
    rw [hP1] at h
    exact capability_inadequate_without_distinction h

/- The two policies genuinely differ on the inexpressible residual. -/
theorem different_after : P0 ρ ≠ P1 I ρ := by
  simp [P0, P1, rho_inexpressible]

end GenuinePolicyReflexivity
