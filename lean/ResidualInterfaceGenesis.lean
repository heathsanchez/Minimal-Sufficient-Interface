import Std

universe u v w z

namespace ResidualInterfaceGenesis

variable {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}

-- Primitive observation supplied by the current measurement language.
variable (observe : Probe → X → V)

-- Protected consequence whose verified disagreements generate residuals.
variable (target : X → Y)

/-- A basis is sufficient exactly when equality on all selected probes forces
    equality of the protected consequence. -/
def BasisSufficient (B : List Probe) : Prop :=
  ∀ x y : X,
    (∀ p, p ∈ B → observe p x = observe p y) →
    target x = target y

/-- A basis hits every protected residual when every target disagreement is
    exposed by at least one selected primitive probe. -/
def HitsAllResiduals (B : List Probe) : Prop :=
  ∀ x y : X,
    target x ≠ target y →
    ∃ p, p ∈ B ∧ observe p x ≠ observe p y

/-- Residual geometry exactly characterizes interface sufficiency. This is the
    formal version of the residual-hypergraph hitting-set criterion used by the
    endogenous interface-shape experiment. -/
theorem sufficient_iff_hits_all_residuals (B : List Probe) :
    BasisSufficient observe target B ↔ HitsAllResiduals observe target B := by
  constructor
  · intro hs x y hxy
    apply Classical.byContradiction
    intro hnone
    apply hxy
    apply hs x y
    intro p hp
    apply Classical.byContradiction
    intro hneq
    exact hnone ⟨p, hp, hneq⟩
  · intro hh x y hobs
    apply Classical.byContradiction
    intro htarget
    rcases hh x y htarget with ⟨p, hp, hneq⟩
    exact hneq (hobs p hp)

/-- Any basis that is sufficient must intersect the residual disagreement of
    every protected-conflicting pair. -/
theorem sufficient_basis_exposes_each_residual
    (B : List Probe)
    (hs : BasisSufficient observe target B)
    {x y : X} (hxy : target x ≠ target y) :
    ∃ p, p ∈ B ∧ observe p x ≠ observe p y := by
  exact (sufficient_iff_hits_all_residuals observe target B).1 hs x y hxy

/-- Conversely, a residual-hitting basis is already a lawful interface for the
    protected consequence; no hidden stronger condition is needed. -/
theorem residual_hitting_basis_is_sufficient
    (B : List Probe)
    (hh : HitsAllResiduals observe target B) :
    BasisSufficient observe target B := by
  exact (sufficient_iff_hits_all_residuals observe target B).2 hh

/-- If a verified target disagreement cannot be separated by any currently
    available primitive probe, then no interface assembled solely from those
    probes can be sufficient. This is a certified observation/measurement
    obstruction rather than a search failure. -/
theorem unobservable_residual_blocks_every_basis
    (Available : List Probe)
    {x y : X}
    (hxy : target x ≠ target y)
    (hblind : ∀ p, p ∈ Available → observe p x = observe p y) :
    ∀ B : List Probe,
      (∀ p, p ∈ B → p ∈ Available) →
      ¬ BasisSufficient observe target B := by
  intro B hsub hs
  have hsame : target x = target y := hs x y (by
    intro p hp
    exact hblind p (hsub p hp))
  exact hxy hsame

/-- Inclusion-minimality of a residual-hitting basis is therefore a direct
    notion of minimal justified interface shape: every retained probe is needed
    to keep hitting the protected residual family. -/
def InclusionMinimalHittingBasis (B : List Probe) : Prop :=
  HitsAllResiduals observe target B ∧
  ∀ B' : List Probe,
    (∀ p, p ∈ B' → p ∈ B) →
    HitsAllResiduals observe target B' →
    (∀ p, p ∈ B → p ∈ B')

/-- A minimal residual-hitting basis is a sufficient protected interface. -/
theorem minimal_hitting_basis_is_sufficient
    (B : List Probe)
    (hmin : InclusionMinimalHittingBasis observe target B) :
    BasisSufficient observe target B := by
  exact residual_hitting_basis_is_sufficient observe target B hmin.1

end ResidualInterfaceGenesis
