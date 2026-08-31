import MinimalBipartiteConsequenceInterface
import TerminalVerdictPolarityBoundary

namespace GroundedMinimalInterfaceBottom

open MinimalBipartiteConsequenceInterface
open TerminalVerdictPolarityBoundary

/-- A grounded consequence world separates the operational interaction table
    from the semantic orientation of its terminal result carrier. -/
structure GroundedInteraction (I O : Type) where
  table : Interaction I O Verdict
  accepted : Verdict

/-- A concrete consequence table whose operational content is held fixed while
    semantic polarity varies. -/
def baseTable : Interaction Unit Unit Verdict where
  eval := fun _ _ => Verdict.left

/-- Two worlds with exactly the same full consequence interaction and therefore
    exactly the same induced minimal row/column interface, but opposite meanings
    for terminal acceptance. -/
def groundedLeft : GroundedInteraction Unit Unit :=
  ⟨baseTable, Verdict.left⟩

def groundedRight : GroundedInteraction Unit Unit :=
  ⟨baseTable, Verdict.right⟩

theorem same_full_consequence_table :
    groundedLeft.table = groundedRight.table := by
  rfl

theorem opposite_semantic_orientation :
    groundedLeft.accepted ≠ groundedRight.accepted := by
  intro h
  cases h

/-- The generated operational row carrier cannot distinguish the two worlds,
    because their entire consequence table is literally the same. -/
theorem same_generated_row_interface :
    RowCarrier groundedLeft.table = RowCarrier groundedRight.table := by
  rfl

/-- Likewise for the generated operational outcome carrier. -/
theorem same_generated_col_interface :
    ColCarrier groundedLeft.table = ColCarrier groundedRight.table := by
  rfl

/-- Even a selector given the complete ungrounded consequence table cannot infer
    terminal semantic polarity correctly in both worlds.  The obstruction is not
    loss introduced by quotienting: the full tables themselves are identical. -/
theorem no_table_only_semantic_orientation :
    ¬ ∃ select : Interaction Unit Unit Verdict → Verdict,
      select groundedLeft.table = groundedLeft.accepted ∧
      select groundedRight.table = groundedRight.accepted := by
  rintro ⟨select, hleft, hright⟩
  have hsame : select groundedLeft.table = select groundedRight.table := by
    rw [same_full_consequence_table]
  apply opposite_semantic_orientation
  calc
    groundedLeft.accepted = select groundedLeft.table := hleft.symm
    _ = select groundedRight.table := hsame
    _ = groundedRight.accepted := hright

/-- Once the verifier supplies one asymmetric semantic grounding, orientation is
    immediately recoverable. -/
def groundedObservation {I O : Type} (W : GroundedInteraction I O) :
    GroundedObservation :=
  ⟨W.accepted⟩

theorem grounding_recovers_orientation {I O : Type}
    (W : GroundedInteraction I O) :
    selectGrounded (groundedObservation W) = W.accepted := by
  rfl

/-- Above that irreducible grounding, consequence itself induces a sufficient
    minimal operational interface: raw context/outcome labels can be discarded
    in favour of realized row/column profiles. -/
theorem consequence_generates_interface_above_grounding {I O : Type}
    (W : GroundedInteraction I O) :
    (∀ i o, rowEval (induceRow W.table i) o = W.table.eval i o) ∧
    (∀ i o, colEval (induceCol W.table o) i = W.table.eval i o) ∧
    (∀ r : RowCarrier W.table, ∃ i : I, induceRow W.table i = r) ∧
    (∀ c : ColCarrier W.table, ∃ o : O, induceCol W.table o = c) := by
  exact bipartite_consequence_induces_minimal_operational_interface W.table

/-- Bottom-up capstone.  The full consequence table generates the complete
    operational interface, but the semantic orientation of the terminal carrier
    is not determined even by that full table.  A verifier-visible asymmetric
    grounding is therefore the irreducible seed in this witness; everything
    above it is consequence-generated up to observational equivalence. -/
theorem grounded_asymmetry_is_bottom_of_minimal_interface :
    same_full_consequence_table ∧
    same_generated_row_interface ∧
    same_generated_col_interface ∧
    (¬ ∃ select : Interaction Unit Unit Verdict → Verdict,
      select groundedLeft.table = groundedLeft.accepted ∧
      select groundedRight.table = groundedRight.accepted) ∧
    (∀ I O : Type, ∀ W : GroundedInteraction I O,
      selectGrounded (groundedObservation W) = W.accepted) := by
  exact ⟨same_full_consequence_table,
    same_generated_row_interface,
    same_generated_col_interface,
    no_table_only_semantic_orientation,
    fun _ _ W => grounding_recovers_orientation W⟩

#check same_full_consequence_table
#check opposite_semantic_orientation
#check same_generated_row_interface
#check same_generated_col_interface
#check no_table_only_semantic_orientation
#check grounding_recovers_orientation
#check consequence_generates_interface_above_grounding
#check grounded_asymmetry_is_bottom_of_minimal_interface

end GroundedMinimalInterfaceBottom
