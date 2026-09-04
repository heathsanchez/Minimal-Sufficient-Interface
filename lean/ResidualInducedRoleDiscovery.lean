import Std
import ConstitutionalRealizationAndRecursion
import GenuinePolicyReflexivity

/-! # Strong D₂ — residual-induced role discovery (genesis without pre-naming)

  Weak D₂ (`ForcedKindGenesis.lean`) proved residual-DIRECTED kind admission:
  the residual carried `kind := policy`, so the criterion just admitted the kind
  already named in the input.

  This file removes that field.  The residual carries NO kind.  It is only the
  behavioural obstruction:

    P0 and P1 are observationally indistinguishable under the level-0 family B0
    (every b ∈ B0 collapses them), yet a verified continuation c separates them.

  From this alone we derive the strong theorem: EVERY resolving extension must
  contain a separator OUTSIDE B0 — the residual forces a new observational
  capability without naming it.  `selectsCapability` is then shown to be ONE
  minimal realization, not data passed into the genesis operation.

  This is genesis that forces the ROLE (a separator), not the SYNTAX (the name
  "Policy"): failure forces constraints on the repair, not its realization.
-/

namespace ResidualInducedRoleDiscovery

open ConstitutionalRealizationAndRecursion
open ConstitutionalFailedFactorization
open GenuinePolicyReflexivity

abbrev Obj := Policy Car
abbrev Obs := Obj → Bool
abbrev Family := Obs → Prop

/- The "does P select capability on ρ?" observation. -/
def selectsCapability (P : Obj) : Bool :=
  match P ρ with
  | .capability => true
  | .representation => false

/- The level-0 observational family: observations that evaluate a controller only
   at EXPRESSIBLE residuals (post-processed).  They cannot see the repair action
   on the inexpressible residual ρ. -/
def B0 (b : Obs) : Prop :=
  ∃ r : Residual Car, Expressible I r ∧ ∃ f : RepairAction → Bool, b = fun P => f (P r)

def Collapses (B : Family) : Prop := ∀ b, B b → b P0 = b (P1 I)

def Resolves (B : Family) : Prop := ∃ b, B b ∧ b P0 ≠ b (P1 I)

/- The external verified continuation: does P select capability on ρ? -/
def c : Obs := selectsCapability

/- The two policies agree on every expressible residual. -/
theorem policies_agree_when_expressible (r : Residual Car) (hexp : Expressible I r) :
    P0 r = P1 I r := by
  simp [P0, P1, hexp]

/- B0 collapses P0 and P1. -/
theorem collapses_B0 : Collapses B0 := by
  intro b hb
  rcases hb with ⟨r, hexp, f, hb⟩
  rw [hb]
  exact congrArg f (policies_agree_when_expressible r hexp)

/- The verified continuation c separates them. -/
theorem c_separates : c P0 ≠ c (P1 I) := by
  unfold c
  change selectsCapability P0 ≠ selectsCapability (P1 I)
  have hP1 : P1 I ρ = RepairAction.capability := by
    unfold P1
    exact if_neg rho_inexpressible
  simp [selectsCapability, P0, hP1]

/- The residual: B0 collapses the pair, yet c separates it. -/
theorem residual : Collapses B0 ∧ c P0 ≠ c (P1 I) :=
  ⟨collapses_B0, c_separates⟩

/- No level-0 resolution exists. -/
theorem no_resolution_in_B0 : ¬ Resolves B0 := by
  intro hres
  rcases hres with ⟨b, hB0, hsep⟩
  exact hsep (collapses_B0 b hB0)

/- STRONG D₂: every resolving extension must contain a separator OUTSIDE B0.
   The forced role (a new observational capability) is derived, not named. -/
theorem every_resolution_needs_new_separator (B1 : Family) :
    Resolves B1 → ∃ b, B1 b ∧ ¬ B0 b ∧ b P0 ≠ b (P1 I) := by
  intro hres
  rcases hres with ⟨b, hB1, hsep⟩
  refine ⟨b, hB1, ?_, hsep⟩
  intro hB0
  exact hsep (collapses_B0 b hB0)

/- Minimality: any separator b makes B0 ∪ {b} resolve.  The residual forces the
   CONSTRAINT (separate P0,P1), not one specific realization — a version space. -/
theorem minimal_extension_resolves (b : Obs) (hsep : b P0 ≠ b (P1 I)) :
    Resolves (fun x => B0 x ∨ x = b) := by
  exact ⟨b, Or.inr rfl, hsep⟩

/- selectsCapability is one minimal realization of the forced role. -/
theorem selectsCapability_is_minimal_realization :
    Resolves (fun x => B0 x ∨ x = selectsCapability) :=
  minimal_extension_resolves selectsCapability c_separates

end ResidualInducedRoleDiscovery
