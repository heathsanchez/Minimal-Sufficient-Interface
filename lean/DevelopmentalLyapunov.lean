import Std
import DevelopmentalCategory

universe u v w z

namespace DevelopmentalLyapunov

open TypedBehaviouralCongruence
open DevelopmentalCategory

variable (C : SmallCategory)
variable (A : Action C)
variable (Obs : C.Obj → Type z)
variable (observe : ∀ X, A.State X → Obs X)

/-- Enumerate ordered pairs from an explicit finite carrier. -/
def pairs {α : Type u} (U : List α) : List (α × α) :=
  U.flatMap (fun x => U.map (fun y => (x, y)))

/-- Membership in the ordered-pair enumeration is exactly componentwise
    membership in the underlying carrier. -/
theorem mem_pairs_iff {α : Type u} (U : List α) (x y : α) :
    (x, y) ∈ pairs U ↔ x ∈ U ∧ y ∈ U := by
  simp [pairs]

/-- Count the elements of a list accepted by a Boolean predicate. -/
def countTrue {α : Type u} (p : α → Bool) : List α → Nat
  | [] => 0
  | x :: xs =>
      match p x with
      | true => Nat.succ (countTrue p xs)
      | false => countTrue p xs

/-- Pointwise enlargement of a Boolean predicate cannot decrease its count. -/
theorem countTrue_mono {α : Type u} {p q : α → Bool}
    (h : ∀ x, p x = true → q x = true) :
    ∀ xs, countTrue p xs ≤ countTrue q xs := by
  intro xs
  induction xs with
  | nil =>
      exact Nat.le_refl 0
  | cons a xs ih =>
      cases hp : p a with
      | false =>
          cases hq : q a with
          | false =>
              simpa [countTrue, hp, hq] using ih
          | true =>
              simp [countTrue, hp, hq]
              exact Nat.le_succ_of_le ih
      | true =>
          have hqt : q a = true := h a hp
          simp [countTrue, hp, hqt]
          simpa [countTrue, hp, hqt] using ih

/-- If q contains p pointwise and is true at one listed witness where p is
    false, then q has strictly larger count. -/
theorem countTrue_lt_of_witness {α : Type u} {p q : α → Bool}
    (h : ∀ x, p x = true → q x = true)
    {w : α} :
    ∀ xs, w ∈ xs → p w = false → q w = true →
      countTrue p xs < countTrue q xs := by
  intro xs
  induction xs with
  | nil =>
      intro hw hpw hqw
      simp at hw
  | cons a xs ih =>
      intro hw hpw hqw
      have hm := List.mem_cons.mp hw
      cases hm with
      | inl hwa =>
          subst a
          have hmono := countTrue_mono h xs
          simp [countTrue, hpw, hqw]
          exact Nat.lt_succ_of_le hmono
      | inr htail =>
          have ihlt := ih htail hpw hqw
          cases hpa : p a with
          | false =>
              cases hqa : q a with
              | false =>
                  simpa [countTrue, hpa, hqa] using ihlt
              | true =>
                  simp [countTrue, hpa, hqa]
                  exact Nat.lt_trans ihlt (Nat.lt_succ_self _)
          | true =>
              have hqat : q a = true := h a hpa
              simp [countTrue, hpa, hqat]
              simpa [countTrue, hpa, hqat] using ihlt

/-- Count zero means no listed element satisfies the predicate. -/
theorem countTrue_eq_zero_iff {α : Type u} (p : α → Bool) :
    ∀ xs, countTrue p xs = 0 ↔ ∀ x ∈ xs, p x = false := by
  intro xs
  induction xs with
  | nil =>
      simp [countTrue]
  | cons a xs ih =>
      cases hpa : p a <;> simp [countTrue, hpa, ih]

/-- Full contextual behavioural equivalence always implies stage-relative
    behavioural equivalence. -/
theorem full_implies_stage
    (S : Stage C) {X : C.Obj} {x y : A.State X}
    (h : BehEq C A Obs observe X x y) :
    BehEqAt C A Obs observe S X x y := by
  intro Y f hf
  exact h Y f

/-- A finite executable behavioural view of one developmental stage.  The
    Boolean tests are required to be exact reflections of the semantic
    relations proved in the categorical layer. -/
structure FiniteView (S : Stage C) (X : C.Obj) where
  states : List (A.State X)
  stageEq : A.State X → A.State X → Bool
  fullEq : A.State X → A.State X → Bool
  stageEq_spec : ∀ x y,
    stageEq x y = true ↔ BehEqAt C A Obs observe S X x y
  fullEq_spec : ∀ x y,
    fullEq x y = true ↔ BehEq C A Obs observe X x y

/-- A pair is a hidden consequential residual exactly when the current stage
    still merges it but the full protected future does not. -/
def hidden {X : C.Obj}
    (stageEq fullEq : A.State X → A.State X → Bool)
    (p : A.State X × A.State X) : Bool :=
  stageEq p.1 p.2 && !(fullEq p.1 p.2)

/-- Developmental Lyapunov potential: number of still-hidden consequential
    distinctions on the declared finite carrier. -/
def potential {S : Stage C} {X : C.Obj}
    (V : FiniteView C A Obs observe S X) : Nat :=
  countTrue (hidden C A V.stageEq V.fullEq) (pairs V.states)

/-- Under stage extension, exact hidden-residual predicates are pointwise
    monotone: a residual hidden later was already hidden earlier. -/
theorem hidden_mono
    {S T : Stage C} (hST : Extends C S T)
    {X : C.Obj}
    (VS : FiniteView C A Obs observe S X)
    (VT : FiniteView C A Obs observe T X)
    (hsameFull : ∀ x y, VS.fullEq x y = VT.fullEq x y)
    {p : A.State X × A.State X}
    (h : hidden C A VT.stageEq VT.fullEq p = true) :
    hidden C A VS.stageEq VS.fullEq p = true := by
  simp [hidden] at h ⊢
  have hT : BehEqAt C A Obs observe T X p.1 p.2 :=
    (VT.stageEq_spec p.1 p.2).mp h.1
  have hS : BehEqAt C A Obs observe S X p.1 p.2 :=
    extension_refines C A Obs observe hST X p.1 p.2 hT
  have hs : VS.stageEq p.1 p.2 = true :=
    (VS.stageEq_spec p.1 p.2).mpr hS
  have hf : VS.fullEq p.1 p.2 = false := by
    have htf : VT.fullEq p.1 p.2 = false := h.2
    rw [hsameFull p.1 p.2]
    exact htf
  exact ⟨hs, hf⟩

/-- Lyapunov monotonicity.  The two views must enumerate the same finite
    carrier and use the same exact full-future relation. -/
theorem potential_nonincreasing
    {S T : Stage C} (hST : Extends C S T)
    {X : C.Obj}
    (VS : FiniteView C A Obs observe S X)
    (VT : FiniteView C A Obs observe T X)
    (hstates : VS.states = VT.states)
    (hsameFull : ∀ x y, VS.fullEq x y = VT.fullEq x y) :
    potential C A Obs observe VT ≤ potential C A Obs observe VS := by
  unfold potential
  rw [← hstates]
  exact countTrue_mono
    (fun p hp => hidden_mono C A Obs observe hST VS VT hsameFull hp)
    (pairs VS.states)

/-- A verified separator makes the potential drop strictly whenever its
    separated pair occurs in the declared finite carrier. -/
theorem new_separator_strictly_decreases
    {S T : Stage C} (hST : Extends C S T)
    {X Y : C.Obj}
    (VS : FiniteView C A Obs observe S X)
    (VT : FiniteView C A Obs observe T X)
    (hstates : VS.states = VT.states)
    (hsameFull : ∀ x y, VS.fullEq x y = VT.fullEq x y)
    {x y : A.State X}
    (hx : x ∈ VS.states) (hy : y ∈ VS.states)
    (f : C.Hom X Y)
    (hold : BehEqAt C A Obs observe S X x y)
    (hnew : T.allow f)
    (hsep : observe Y (A.map f x) ≠ observe Y (A.map f y)) :
    potential C A Obs observe VT < potential C A Obs observe VS := by
  have hpair : (x, y) ∈ pairs VS.states := by
    simp [pairs, hx, hy]
  have hStrue : VS.stageEq x y = true :=
    (VS.stageEq_spec x y).mpr hold
  have hfullFalse : VS.fullEq x y = false := by
    cases hfull : VS.fullEq x y with
    | false => rfl
    | true =>
        have hb : BehEq C A Obs observe X x y :=
          (VS.fullEq_spec x y).mp hfull
        exact False.elim (hsep (hb Y f))
  have hTfalse : VT.stageEq x y = false := by
    cases ht : VT.stageEq x y with
    | false => rfl
    | true =>
        have hb : BehEqAt C A Obs observe T X x y :=
          (VT.stageEq_spec x y).mp ht
        exact False.elim (hsep (hb Y f hnew))
  have hSf : hidden C A VS.stageEq VS.fullEq (x, y) = true := by
    simp [hidden, hStrue, hfullFalse]
  have hTf : hidden C A VT.stageEq VT.fullEq (x, y) = false := by
    simp [hidden, hTfalse]
  unfold potential
  rw [← hstates]
  exact countTrue_lt_of_witness
    (fun p hp => hidden_mono C A Obs observe hST VS VT hsameFull hp)
    (pairs VS.states) hpair hTf hSf

/-- Zero potential on a covered finite view is exact completion: the current
    behavioural identity agrees with the full protected-future identity on
    every enumerated pair. -/
theorem potential_eq_zero_iff_complete
    {S : Stage C} {X : C.Obj}
    (V : FiniteView C A Obs observe S X) :
    potential C A Obs observe V = 0 ↔
      ∀ x ∈ V.states, ∀ y ∈ V.states,
        (BehEqAt C A Obs observe S X x y ↔
          BehEq C A Obs observe X x y) := by
  unfold potential
  rw [countTrue_eq_zero_iff]
  constructor
  · intro h x hx y hy
    constructor
    · intro hstage
      have hs : V.stageEq x y = true := (V.stageEq_spec x y).mpr hstage
      have hp : (x, y) ∈ pairs V.states := by simp [pairs, hx, hy]
      have hhidden := h (x, y) hp
      have hf : V.fullEq x y = true := by
        cases hfull : V.fullEq x y with
        | true => rfl
        | false =>
            have : hidden C A V.stageEq V.fullEq (x, y) = true := by
              simp [hidden, hs, hfull]
            rw [this] at hhidden
            contradiction
      exact (V.fullEq_spec x y).mp hf
    · exact full_implies_stage C A Obs observe S
  · intro hexact p hp
    have hpairs : p.1 ∈ V.states ∧ p.2 ∈ V.states := by
      exact (mem_pairs_iff V.states p.1 p.2).mp hp
    rcases hpairs with ⟨hx, hy⟩
    cases hs : V.stageEq p.1 p.2 with
    | false =>
        simp [hidden, hs]
    | true =>
        have hstage : BehEqAt C A Obs observe S X p.1 p.2 :=
          (V.stageEq_spec p.1 p.2).mp hs
        have hfull : BehEq C A Obs observe X p.1 p.2 :=
          (hexact p.1 hx p.2 hy).mp hstage
        have hf : V.fullEq p.1 p.2 = true :=
          (V.fullEq_spec p.1 p.2).mpr hfull
        simp [hidden, hs, hf]

/-- The strict developmental relation induced by the potential. -/
def StrictDevelopment {X : C.Obj}
    (U : List (A.State X))
    (fullEq : A.State X → A.State X → Bool)
    (T S : A.State X → A.State X → Bool) : Prop :=
  countTrue (hidden C A T fullEq) (pairs U) <
    countTrue (hidden C A S fullEq) (pairs U)

/-- Strict potential descent is well-founded: an infinite chain of strict
    certified decreases on a fixed finite carrier is impossible. -/
theorem strictDevelopment_wellFounded
    {X : C.Obj}
    (U : List (A.State X))
    (fullEq : A.State X → A.State X → Bool) :
    WellFounded
      (StrictDevelopment C A U fullEq) := by
  unfold StrictDevelopment
  exact InvImage.wf
    (fun stageEq : A.State X → A.State X → Bool =>
      countTrue (hidden C A stageEq fullEq) (pairs U))
    Nat.lt_wfRel.wf

end DevelopmentalLyapunov
