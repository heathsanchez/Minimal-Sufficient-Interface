import Std
import Kernel
import MinimalRepair

universe u v

namespace ResidualMorphismClass

open MeetKernel
open MinimalRepair

variable {L : Type u} {F : Type v}
variable (K : MeetKernel L)

/-- `effect f` is the behavioural distinction induced by a concrete candidate
    morphism/program `f`.  MSI identifies concrete candidates by the repaired
    interface they induce, not by source syntax. -/
def RepairEffect (effect : F → L) (E : L) (f : F) : L :=
  K.meet E (effect f)

/-- Two concrete candidates are the same developmental morphism class exactly
    when they induce the same repaired behavioural interface. -/
def BehRepairEq (effect : F → L) (E : L) (f g : F) : Prop :=
  RepairEffect K effect E f = RepairEffect K effect E g

/-- A verifier licenses a concrete candidate for constraint `R` when its
    induced repaired interface is exactly the canonical MSI repair `E ∧ R`.
    This definition deliberately permits many concrete realizers. -/
def Licensed (effect : F → L) (E R : L) (f : F) : Prop :=
  RepairEffect K effect E f = K.meet E R

/-- Any two verifier-licensed concrete realizers collapse to one behavioural
    morphism class.  No syntactic uniqueness is required or claimed. -/
theorem licensed_candidates_same_class
    (effect : F → L) (E R : L) {f g : F}
    (hf : Licensed K effect E R f)
    (hg : Licensed K effect E R g) :
    BehRepairEq K effect E f g := by
  unfold BehRepairEq RepairEffect Licensed at *
  exact hf.trans hg.symm

/-- Every licensed concrete candidate realizes the unique least-change repair
    of the old interface by the verifier constraint. -/
theorem licensed_realizes_unique_minimal_repair
    (effect : F → L) (E R : L) {f : F}
    (hf : Licensed K effect E R f) :
    K.Le (RepairEffect K effect E f) E ∧
    K.Le (RepairEffect K effect E f) R ∧
    ∀ x, K.Le x E → K.Le x R → K.Le x (RepairEffect K effect E f) := by
  rw [hf]
  exact minimal_justified_repair K E R

/-- Hence the developmental object selected by a residual/constraint is not a
    privileged program but the equivalence class of all concrete realizers of
    the unique minimal behavioural repair. -/
theorem licensed_class_is_unique
    (effect : F → L) (E R : L) {f : F}
    (hf : Licensed K effect E R f)
    (m : L)
    (hmE : K.Le m E) (hmR : K.Le m R)
    (hmGreatest : ∀ x, K.Le x E → K.Le x R → K.Le x m) :
    m = RepairEffect K effect E f := by
  rw [hf]
  exact meet_unique_minimal_repair K hmE hmR hmGreatest

end ResidualMorphismClass
