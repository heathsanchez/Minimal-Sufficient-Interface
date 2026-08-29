import ResidualInterfaceGenesis

universe u v w z

namespace VerifiedNewProbeGenesis

open ResidualInterfaceGenesis

variable {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}

/-- A verified witness that the current primitive observation language is blind
    to a protected residual, while one derived probe exposes that residual. -/
structure DerivedProbeWitness
    (observe : Probe → X → V) (target : X → Y)
    (Available : List Probe) (q : Probe) (x y : X) : Prop where
  residual : target x ≠ target y
  oldBlind : ∀ p, p ∈ Available → observe p x = observe p y
  newSeparates : observe q x ≠ observe q y

/-- Before the derived probe is admitted, no basis assembled solely from the
    old primitive observation language can be sufficient. -/
theorem old_language_obstructed
    (observe : Probe → X → V) (target : X → Y)
    (Available : List Probe) (q : Probe) (x y : X)
    (h : DerivedProbeWitness observe target Available q x y) :
    ∀ B : List Probe,
      (∀ p, p ∈ B → p ∈ Available) →
      ¬ BasisSufficient observe target B := by
  exact unobservable_residual_blocks_every_basis
    observe target Available h.residual h.oldBlind

/-- If the newly generated probe separates every protected residual, then the
    singleton interface containing that probe is sufficient. This is the
    verifier-licensed success condition used by the residual-probe experiment. -/
theorem generated_probe_hitting_all_residuals_is_sufficient
    (observe : Probe → X → V) (target : X → Y) (q : Probe)
    (hall : ∀ x y : X, target x ≠ target y → observe q x ≠ observe q y) :
    BasisSufficient observe target [q] := by
  apply residual_hitting_basis_is_sufficient observe target [q]
  intro x y hxy
  exact ⟨q, by simp, hall x y hxy⟩

/-- Necessity of the new observation: if a protected residual is invisible to
    every old primitive probe but visible to q, then every sufficient basis
    built from q plus the old language must contain q. The residual geometry
    therefore forces this observation in any one-probe repair. -/
theorem new_probe_forced_into_every_sufficient_extension
    (observe : Probe → X → V) (target : X → Y)
    (Available : List Probe) (q : Probe) (x y : X)
    (h : DerivedProbeWitness observe target Available q x y)
    (B : List Probe)
    (hsub : ∀ p, p ∈ B → p ∈ q :: Available)
    (hs : BasisSufficient observe target B) :
    q ∈ B := by
  apply Classical.byContradiction
  intro hq
  have hOld : ∀ p, p ∈ B → p ∈ Available := by
    intro p hp
    have hm := hsub p hp
    simp only [List.mem_cons] at hm
    cases hm with
    | inl hpq =>
        subst p
        exact False.elim (hq hp)
    | inr hav =>
        exact hav
  have hblocked := old_language_obstructed
    observe target Available q x y h B hOld
  exact hblocked hs

/-- Exact ancestral ablation: removing q from the one-probe extension restores
    the certified old-language obstruction for every basis over Available. -/
theorem probe_ablation_restores_obstruction
    (observe : Probe → X → V) (target : X → Y)
    (Available : List Probe) (q : Probe) (x y : X)
    (h : DerivedProbeWitness observe target Available q x y) :
    ∀ B : List Probe,
      (∀ p, p ∈ B → p ∈ Available) →
      ¬ BasisSufficient observe target B := by
  exact old_language_obstructed observe target Available q x y h

/-- A full verified residual-driven observation genesis step packages the three
    causal facts needed for a lawful OBSERVE/EXTEND move: old obstruction,
    warm sufficiency, and necessity of the admitted probe among one-probe
    extensions of the old observation language. -/
theorem verified_new_probe_genesis
    (observe : Probe → X → V) (target : X → Y)
    (Available : List Probe) (q : Probe) (x y : X)
    (h : DerivedProbeWitness observe target Available q x y)
    (hall : ∀ a b : X, target a ≠ target b → observe q a ≠ observe q b) :
    (¬ BasisSufficient observe target Available) ∧
    BasisSufficient observe target [q] ∧
    (∀ B : List Probe,
      (∀ p, p ∈ B → p ∈ q :: Available) →
      BasisSufficient observe target B →
      q ∈ B) := by
  constructor
  · have hblocked := old_language_obstructed
      observe target Available q x y h Available (by
        intro p hp
        exact hp)
    exact hblocked
  constructor
  · exact generated_probe_hitting_all_residuals_is_sufficient
      observe target q hall
  · intro B hsub hs
    exact new_probe_forced_into_every_sufficient_extension
      observe target Available q x y h B hsub hs

end VerifiedNewProbeGenesis
