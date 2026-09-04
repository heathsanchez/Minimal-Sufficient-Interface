import Std
import ConstitutionalRealizationAndRecursion
import GenuinePolicyReflexivity

/-! # Test 3B — forced Kind genesis (D₂ vs D₁)

  Hostile construction: level 0 (`K0`) admits ONLY the state kind.  `Policy` is
  deliberately NOT a level-0 kind, there is NO encoding of policies into states,
  and there is NO "extend-with-policy" constructor.

  The residual is the policy distinction `dPolicy = (P0, P1)` — a verified
  consequential difference between repair behaviours (from Test 3A: P0 selects
  the inadequate representation action, P1 the adequate capability action).

  Claims formalized here:

  1. TYPE BARRIER: `dPolicy` is not expressible at level 0 (`Policy ∉ K0`), so
     no level-0 observation (a `Car → Bool`) can even be applied to it.

  2. The genesis criterion is GENERIC — `GenesisExtension d := K0 ∪ {d.kind}`
     admits whatever kind the residual names, with no policy-specific rule.
     This is the D₂ candidate: the ordinary residual/genesis law, not an
     external "add Policy" instruction.

  3. D₂: the generic criterion, applied to `dPolicy`, yields the minimal
     extension `K1 = K0 ∪ {policy}` — uniquely minimal in this two-kind world.
-/

namespace ForcedKindGenesis

open ConstitutionalRealizationAndRecursion
open ConstitutionalFailedFactorization
open GenuinePolicyReflexivity

/- Kinds: state and policy. -/
inductive Kind | state | policy
  deriving DecidableEq, Repr, Inhabited

/- Level 0 admits ONLY the state kind.  Policy is absent. -/
def K0 (k : Kind) : Prop := k = Kind.state

/- Level 1 admits both state and policy. -/
def K1 (k : Kind) : Prop := k = Kind.state ∨ k = Kind.policy

/- The carrier type associated to each kind. -/
def CarrierOf : Kind → Type
  | .state  => Car
  | .policy => Policy Car

/- An observation at kind k. -/
def Observation (k : Kind) : Type := CarrierOf k → Bool

/- A distinction: two objects of the same kind. -/
structure Distinction where
  kind : Kind
  x : CarrierOf kind
  y : CarrierOf kind

/- Expressible at level L: the kind is admissible and some observation at that
   kind separates the pair. -/
def ExpressibleAt (L : Kind → Prop) (d : Distinction) : Prop :=
  L d.kind ∧ ∃ obs : Observation d.kind, obs d.x ≠ obs d.y

/- Δ extends K0: every K0-admissible kind stays admissible. -/
def Extends (Δ K0 : Kind → Prop) : Prop := ∀ k, K0 k → Δ k

/- The policy distinction: P0 vs P1 on the residual. -/
def dPolicy : Distinction := ⟨Kind.policy, P0, P1 I⟩

/- (1) TYPE BARRIER: the policy distinction is inexpressible at level 0. -/
theorem policy_inexpressible_at_K0 : ¬ ExpressibleAt K0 dPolicy := by
  intro h
  have hk : K0 dPolicy.kind := h.1
  unfold K0 dPolicy at hk
  exact Kind.noConfusion hk

/- K1 extends K0. -/
theorem K1_extends_K0 : Extends K1 K0 := by
  intro k hk
  unfold K0 at hk
  rw [hk]
  unfold K1
  exact Or.inl rfl

/- (2) K1 expresses the policy distinction (the observation "does P select
   capability on ρ?" separates P0 from P1). -/
def selectsCapability (P : Policy Car) : Bool :=
  match P ρ with
  | .capability => true
  | .representation => false

theorem K1_expresses_policy : ExpressibleAt K1 dPolicy := by
  constructor
  · unfold K1; exact Or.inr rfl
  · refine ⟨selectsCapability, ?_⟩
    change selectsCapability P0 ≠ selectsCapability (P1 I)
    have hP1 : P1 I ρ = RepairAction.capability := by
      unfold P1
      exact if_neg rho_inexpressible
    simp [selectsCapability, P0, hP1]

/- (3) The GENERIC genesis criterion: given any distinction d, admit its kind.
   Defined uniformly over all distinctions — NOT policy-specific. -/
def GenesisExtension (d : Distinction) : Kind → Prop :=
  fun k => K0 k ∨ k = d.kind

/- The generic criterion, applied to the policy distinction, IS K1. -/
theorem generic_genesis_yields_K1 : GenesisExtension dPolicy = K1 := by
  funext k
  unfold GenesisExtension K0 K1 dPolicy
  rfl

/- Δ is the LEAST extension of K0 expressing d. -/
def LeastExtension (K0 : Kind → Prop) (d : Distinction) (Δ : Kind → Prop) : Prop :=
  Extends Δ K0 ∧ ExpressibleAt Δ d ∧
  ∀ Δ', Extends Δ' K0 → ExpressibleAt Δ' d → ∀ k, Δ k → Δ' k

/- (4) D₂: the generic criterion yields the uniquely minimal extension.  In this
   two-kind world, K1 is the least extension of K0 expressing the policy
   distinction — forced by the residual, not by an external constructor. -/
theorem policy_residual_forces_minimal_extension :
    ¬ ExpressibleAt K0 dPolicy ∧ LeastExtension K0 dPolicy K1 := by
  constructor
  · exact policy_inexpressible_at_K0
  · constructor
    · exact K1_extends_K0
    constructor
    · exact K1_expresses_policy
    · intro Δ' hext hexpr k hk
      unfold K1 at hk
      rcases hk with hstate | hpolicy
      · rw [hstate]
        exact hext Kind.state rfl
      · rw [hpolicy]
        exact hexpr.1

end ForcedKindGenesis
