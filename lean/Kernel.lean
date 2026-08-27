import Std

universe u v w

/-- The abstract extensional refinement kernel: an idempotent commutative semigroup. -/
structure MeetKernel (L : Type u) where
  meet : L → L → L
  idem : ∀ a, meet a a = a
  comm : ∀ a b, meet a b = meet b a
  assoc : ∀ a b c, meet (meet a b) c = meet a (meet b c)

namespace MeetKernel

variable {L : Type u} (K : MeetKernel L)

/-- The refinement order induced by meet. -/
def Le (a b : L) : Prop := K.meet a b = a

/-- Repeating the same verified constraint is redundant. -/
theorem duplicate (E A : L) :
    K.meet (K.meet E A) A = K.meet E A := by
  calc
    K.meet (K.meet E A) A = K.meet E (K.meet A A) := K.assoc E A A
    _ = K.meet E A := by rw [K.idem A]

/-- Accumulation order does not matter. -/
theorem order_independent (E A B : L) :
    K.meet (K.meet E A) B = K.meet (K.meet E B) A := by
  calc
    K.meet (K.meet E A) B = K.meet E (K.meet A B) := K.assoc E A B
    _ = K.meet E (K.meet B A) := by rw [K.comm A B]
    _ = K.meet (K.meet E B) A := by rw [K.assoc E B A]

/-- Grouping/batching of accumulated constraints does not matter. -/
theorem batching (E A B : L) :
    K.meet (K.meet E A) B = K.meet E (K.meet A B) :=
  K.assoc E A B

/-- The induced refinement order is reflexive. -/
theorem le_refl (a : L) : K.Le a a := by
  exact K.idem a

/-- Every update refines (or leaves unchanged) the current state. -/
theorem update_refines (E A : L) : K.Le (K.meet E A) E := by
  unfold Le
  calc
    K.meet (K.meet E A) E = K.meet E (K.meet A E) := K.assoc E A E
    _ = K.meet E (K.meet E A) := by rw [K.comm A E]
    _ = K.meet (K.meet E E) A := by rw [K.assoc E E A]
    _ = K.meet E A := by rw [K.idem E]

/-- The induced refinement order is transitive. -/
theorem le_trans {a b c : L} (hab : K.Le a b) (hbc : K.Le b c) : K.Le a c := by
  unfold Le at hab hbc ⊢
  calc
    K.meet a c = K.meet (K.meet a b) c := by rw [hab]
    _ = K.meet a (K.meet b c) := K.assoc a b c
    _ = K.meet a b := by rw [hbc]
    _ = a := hab

/-- The induced refinement order is antisymmetric. -/
theorem le_antisymm {a b : L} (hab : K.Le a b) (hba : K.Le b a) : a = b := by
  unfold Le at hab hba
  calc
    a = K.meet a b := hab.symm
    _ = K.meet b a := K.comm a b
    _ = b := hba

/-- A meet update cannot perform a genuine retraction/coarsening. If an update
    `E' = E ∧ A` is also at least as coarse as `E`, then it changed nothing.
    Retraction therefore requires provenance/recomputation above this kernel. -/
theorem update_cannot_coarsen {E A E' : L}
    (hupdate : E' = K.meet E A)
    (hcoarse : K.Le E E') : E' = E := by
  have href : K.Le E' E := by
    rw [hupdate]
    exact K.update_refines E A
  exact K.le_antisymm href hcoarse

end MeetKernel

/-- Concrete protected-continuation semantics, without requiring finite sets. -/
def EquivalentOn {X : Type u} {C : Type v} {O : Type w}
    (P : X → C → O) (B : List C) (x y : X) : Prop :=
  ∀ c, c ∈ B → P x c = P y c

namespace EquivalentOn

variable {X : Type u} {C : Type v} {O : Type w}
variable (P : X → C → O)

/-- Empty evidence identifies every pair. -/
theorem nil (x y : X) : EquivalentOn P [] x y := by
  intro c hc
  simp at hc

/-- Adding one continuation is exactly conjunction with its kernel. -/
theorem cons (c : C) (B : List C) (x y : X) :
    EquivalentOn P (c :: B) x y ↔
      P x c = P y c ∧ EquivalentOn P B x y := by
  constructor
  · intro h
    constructor
    · exact h c (by simp)
    · intro d hd
      exact h d (by simp [hd])
  · intro h d hd
    rcases h with ⟨hc, hB⟩
    simp at hd
    rcases hd with rfl | hd
    · exact hc
    · exact hB d hd

/-- Observational sameness is reflexive. -/
theorem refl (B : List C) (x : X) : EquivalentOn P B x x := by
  intro c hc
  rfl

/-- Observational sameness is symmetric. -/
theorem symm (B : List C) {x y : X} (h : EquivalentOn P B x y) :
    EquivalentOn P B y x := by
  intro c hc
  exact (h c hc).symm

/-- Observational sameness is transitive. -/
theorem trans (B : List C) {x y z : X}
    (hxy : EquivalentOn P B x y) (hyz : EquivalentOn P B y z) :
    EquivalentOn P B x z := by
  intro c hc
  exact (hxy c hc).trans (hyz c hc)

/-- Removing protected continuations can only coarsen observational identity.
    This is the provenance-side dual of monotone meet refinement. -/
theorem antitone_basis {B T : List C}
    (hBT : ∀ c, c ∈ B → c ∈ T) {x y : X}
    (hT : EquivalentOn P T x y) : EquivalentOn P B x y := by
  intro c hc
  exact hT c (hBT c hc)

end EquivalentOn
