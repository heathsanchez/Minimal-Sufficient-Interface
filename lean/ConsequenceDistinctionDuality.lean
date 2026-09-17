import Std

namespace ConsequenceDistinctionDuality

universe u v

abbrev Rel (X : Type u) := X → X → Prop
abbrev Family (A : Type v) := A → Prop

def RelLe {X : Type u} (E F : Rel X) : Prop :=
  ∀ ⦃x y⦄, E x y → F x y

def FamLe {A : Type v} (C D : Family A) : Prop :=
  ∀ ⦃a⦄, C a → D a

/-- `Phi` sends a family of protected consequences to their common kernel. -/
def Phi {X : Type u} {A : Type v}
    (kernel : A → Rel X) (C : Family A) : Rel X :=
  fun x y => ∀ ⦃a⦄, C a → kernel a x y

/-- `Psi` sends a representation to every declared consequence that descends through it. -/
def Psi {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) : Family A :=
  fun a => RelLe E (kernel a)

/-- The consequence/distinction polarity: a family descends through a representation
iff that representation refines the family's common kernel. -/
theorem galois {X : Type u} {A : Type v}
    (kernel : A → Rel X) (C : Family A) (E : Rel X) :
    FamLe C (Psi kernel E) ↔ RelLe E (Phi kernel C) := by
  constructor
  · intro h x y hxy a ha
    exact h ha hxy
  · intro h a ha x y hxy
    exact h hxy ha

/-- More protected consequences can only refine the common-kernel relation. -/
theorem phi_antitone {X : Type u} {A : Type v}
    (kernel : A → Rel X) {C D : Family A} (hCD : FamLe C D) :
    RelLe (Phi kernel D) (Phi kernel C) := by
  intro x y hxy a ha
  exact hxy (hCD ha)

/-- A coarser representation supports no more descending consequences. -/
theorem psi_antitone {X : Type u} {A : Type v}
    (kernel : A → Rel X) {E F : Rel X} (hEF : RelLe E F) :
    FamLe (Psi kernel F) (Psi kernel E) := by
  intro a ha x y hxy
  exact ha (hEF hxy)

def CloseConsequences {X : Type u} {A : Type v}
    (kernel : A → Rel X) (C : Family A) : Family A :=
  Psi kernel (Phi kernel C)

def CloseRepresentation {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) : Rel X :=
  Phi kernel (Psi kernel E)

def FamEq {A : Type v} (C D : Family A) : Prop :=
  FamLe C D ∧ FamLe D C

def RelEq {X : Type u} (E F : Rel X) : Prop :=
  RelLe E F ∧ RelLe F E

/-- Every protected consequence belongs to its consequential closure. -/
theorem consequence_closure_extensive {X : Type u} {A : Type v}
    (kernel : A → Rel X) (C : Family A) :
    FamLe C (CloseConsequences kernel C) := by
  intro a ha x y hxy
  exact hxy ha

/-- Closing a representation forgets only unsupported distinctions, so it is coarser. -/
theorem representation_closure_extensive {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) :
    RelLe E (CloseRepresentation kernel E) := by
  intro x y hxy a ha
  exact ha hxy

/-- Consequential closure is idempotent. -/
theorem consequence_closure_idempotent {X : Type u} {A : Type v}
    (kernel : A → Rel X) (C : Family A) :
    FamEq
      (CloseConsequences kernel (CloseConsequences kernel C))
      (CloseConsequences kernel C) := by
  constructor
  · intro a ha x y hxy
    apply ha
    intro b hb
    exact hb hxy
  · exact consequence_closure_extensive kernel (CloseConsequences kernel C)

/-- Representation closure is idempotent. -/
theorem representation_closure_idempotent {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) :
    RelEq
      (CloseRepresentation kernel (CloseRepresentation kernel E))
      (CloseRepresentation kernel E) := by
  constructor
  · intro x y hxy a ha
    apply hxy
    intro u v huv
    exact huv ha
  · exact representation_closure_extensive kernel (CloseRepresentation kernel E)

/-- A residual is exactly a witness that a consequence fails to descend. -/
def Residual {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (d : A) : Prop :=
  ∃ x y, E x y ∧ ¬ kernel d x y

/-- Residual existence is equivalent to failure of membership in `Psi`. -/
theorem residual_iff_not_descends {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (d : A) :
    Residual kernel E d ↔ ¬ Psi kernel E d := by
  constructor
  · intro hres hdesc
    rcases hres with ⟨x, y, hE, hnot⟩
    exact hnot (hdesc hE)
  · intro hnot
    classical
    exact Classical.byContradiction (fun hnores =>
      hnot (fun hE =>
        Classical.byContradiction (fun hk =>
          hnores ⟨_, _, hE, hk⟩)))

/-- Semantic least repair: retain the old distinctions and add exactly the new kernel. -/
def Repair {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (d : A) : Rel X :=
  fun x y => E x y ∧ kernel d x y

theorem repair_refines_old {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (d : A) :
    RelLe (Repair kernel E d) E := by
  intro x y h
  exact h.1

theorem repair_supports_consequence {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (d : A) :
    Psi kernel (Repair kernel E d) d := by
  intro x y h
  exact h.2

/-- Any refinement of `E` through which `d` descends is finer than the repair. -/
theorem repair_is_coarsest {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E R : Rel X) (d : A)
    (hOld : RelLe R E) (hD : Psi kernel R d) :
    RelLe R (Repair kernel E d) := by
  intro x y hR
  exact ⟨hOld hR, hD hR⟩

/-- A genuine residual makes the least repair a strict refinement. -/
theorem residual_forces_strict_repair {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (d : A)
    (hres : Residual kernel E d) :
    RelLe (Repair kernel E d) E ∧ ¬ RelLe E (Repair kernel E d) := by
  constructor
  · exact repair_refines_old kernel E d
  · intro hBack
    rcases hres with ⟨x, y, hE, hnot⟩
    exact hnot (hBack hE).2

/-- Ordinary function equality is one concrete source of consequence kernels. -/
def ObservationKernel {X : Type u} {Y : Type v} (c : X → Y) : Rel X :=
  fun x y => c x = c y

/-- Representation failure: the desired consequence itself does not descend. -/
def RepresentationFailure {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (d : A) : Prop :=
  ¬ Psi kernel E d

/-- Capability failure: the consequence is representable but outside bounded reachable closure. -/
def CapabilityFailure {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (Reachable : Family A) (d : A) : Prop :=
  Psi kernel E d ∧ ¬ Reachable d

/-- Search failure: the consequence is reachable but the search has not found it. -/
def SearchFailure {A : Type v}
    (Reachable Found : Family A) (d : A) : Prop :=
  Reachable d ∧ ¬ Found d

/-- Solved means the consequence has been found. -/
def Solved {A : Type v} (Found : Family A) (d : A) : Prop :=
  Found d

/-- Under the core invariant `Reachable ⊆ Psi(E)`, representation failure excludes reachability. -/
theorem representation_failure_excludes_reachable {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (Reachable : Family A) (d : A)
    (hReachableSound : FamLe Reachable (Psi kernel E))
    (hRep : RepresentationFailure kernel E d) :
    ¬ Reachable d := by
  intro hReach
  exact hRep (hReachableSound hReach)

/-- Capability failure and search failure are disjoint. -/
theorem capability_failure_excludes_search {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X) (Reachable Found : Family A) (d : A)
    (hCap : CapabilityFailure kernel E Reachable d) :
    ¬ SearchFailure Reachable Found d := by
  intro hSearch
  exact hCap.2 hSearch.1

/-- Search failure and solved are disjoint. -/
theorem search_failure_excludes_solved {A : Type v}
    (Reachable Found : Family A) (d : A)
    (hSearch : SearchFailure Reachable Found d) :
    ¬ Solved Found d := by
  exact hSearch.2

/-- With sound reachability/found invariants, every desired consequence is in the intended
diagnostic hierarchy: representation, capability, search, or solved. -/
theorem diagnostic_complete {X : Type u} {A : Type v}
    (kernel : A → Rel X) (E : Rel X)
    (Reachable Found : Family A) (d : A) :
    RepresentationFailure kernel E d ∨
      CapabilityFailure kernel E Reachable d ∨
      SearchFailure Reachable Found d ∨
      Solved Found d := by
  classical
  by_cases hDesc : Psi kernel E d
  · by_cases hReach : Reachable d
    · by_cases hFound : Found d
      · exact Or.inr (Or.inr (Or.inr hFound))
      · exact Or.inr (Or.inr (Or.inl ⟨hReach, hFound⟩))
    · exact Or.inr (Or.inl ⟨hDesc, hReach⟩)
  · exact Or.inl hDesc

/-- Found soundness makes a solved consequence reachable. -/
theorem solved_is_reachable {A : Type v}
    (Reachable Found : Family A) (d : A)
    (hFoundSound : FamLe Found Reachable)
    (hSolved : Solved Found d) :
    Reachable d :=
  hFoundSound hSolved

end ConsequenceDistinctionDuality
