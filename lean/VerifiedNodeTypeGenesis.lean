import ResidualInterfaceGenesis

universe u v w

namespace VerifiedNodeTypeGenesis

variable {X : Type u} {V : Type v} {Probe : Type w}

/-- A selector-only computation may return only a value already exposed by the old schema. -/
def SelectorOnly (exposed : X → List V) (f : X → V) : Prop :=
  ∀ x, f x ∈ exposed x

/-- A depth-independent expressivity witness: on some state, the verified target lies
outside every value the old selector schema can ever return. -/
def SelectorClosureObstruction (exposed : X → List V) (target : X → V) : Prop :=
  ∃ x, target x ∉ exposed x

/-- Once a target value lies outside the old exposed-value image, no amount of search
inside selector-only programs can produce an exact solution. -/
theorem selector_closure_obstruction_blocks_all_selector_search
    (exposed : X → List V) (target : X → V)
    (hobs : SelectorClosureObstruction exposed target) :
    ∀ f : X → V, SelectorOnly exposed f → ¬ (∀ x, f x = target x) := by
  intro f hf hexact
  rcases hobs with ⟨x, hout⟩
  have hmem := hf x
  rw [hexact x] at hmem
  exact hout hmem

/-- An exact newly admitted value-producing node necessarily escapes the old
selector-only closure whenever a selector closure obstruction exists. -/
theorem exact_new_node_escapes_old_selector_closure
    (exposed : X → List V) (target newNode : X → V)
    (hobs : SelectorClosureObstruction exposed target)
    (hnew : ∀ x, newNode x = target x) :
    ¬ SelectorOnly exposed newNode := by
  intro hselector
  rcases hobs with ⟨x, hout⟩
  have hmem := hselector x
  rw [hnew x] at hmem
  exact hout hmem

/-- Exact ablation: removing the new value-producing node returns the system to the
old selector closure, where the certified obstruction still blocks exactness. -/
theorem node_ablation_restores_old_impossibility
    (exposed : X → List V) (target : X → V)
    (hobs : SelectorClosureObstruction exposed target) :
    ∀ f : X → V, SelectorOnly exposed f → ∃ x, f x ≠ target x := by
  intro f hf
  rcases hobs with ⟨x, hout⟩
  refine ⟨x, ?_⟩
  intro heq
  have hmem := hf x
  rw [heq] at hmem
  exact hout hmem

/-- Residual-inferred basis sufficiency supplies the observational side of the new-node
construction: every verified target disagreement is exposed by at least one retained
input coordinate. -/
theorem sufficient_inputs_hit_every_verified_residual
    (observe : Probe → X → V) (target : X → V) (B : List Probe)
    (hB : ResidualInterfaceGenesis.BasisSufficient observe target B) :
    ResidualInterfaceGenesis.HitsAllResiduals observe target B :=
  (ResidualInterfaceGenesis.sufficient_iff_hits_all_residuals observe target B).mp hB

/-- Conversely, if the residual-selected inputs hit every verified disagreement, they
are sufficient to define a deterministic value-producing local law on their joint view. -/
theorem residual_selected_inputs_are_sufficient
    (observe : Probe → X → V) (target : X → V) (B : List Probe)
    (hB : ResidualInterfaceGenesis.HitsAllResiduals observe target B) :
    ResidualInterfaceGenesis.BasisSufficient observe target B :=
  (ResidualInterfaceGenesis.sufficient_iff_hits_all_residuals observe target B).mpr hB

end VerifiedNodeTypeGenesis
