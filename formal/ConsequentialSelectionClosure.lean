import ConsequenceSelectedDevelopmentalDiscovery

universe z

namespace ConsequentialSelectionClosure

open VerifiedConsequenceGenesis
open TypedBehaviouralCongruence
open ConsequenceSelectedDevelopmentalDiscovery
open MultiCandidateDevelopmentalSearch
open GeneratedCandidateDevelopmentalSearch

/-- Generic soundness of consequential selection over an arbitrary finite pool:
    anything selected is genuinely a member of the supplied pool and actually
    separates the compared states.  No primitive identity can enter through
    the theorem statement. -/
theorem selected_separator_is_member_and_separates
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (x y : A.State X)
    (pool : List (C.Hom X Y)) (selected : C.Hom X Y)
    (hsel : selectFirstSeparator C A Obs observe x y pool = some selected) :
    selected ∈ pool ∧ observe Y (A.map selected x) ≠ observe Y (A.map selected y) := by
  classical
  induction pool with
  | nil =>
      simp [selectFirstSeparator] at hsel
  | cons h rest ih =>
      by_cases hsep : observe Y (A.map h x) ≠ observe Y (A.map h y)
      · simp [selectFirstSeparator, hsep] at hsel
        subst selected
        exact ⟨by simp, hsep⟩
      · simp [selectFirstSeparator, hsep] at hsel
        have hrs := ih hsel
        exact ⟨by simp [hrs.1], hrs.2⟩

/-- Completeness/null law for the selector.  It returns no primitive exactly
    when every primitive in the finite pool is consequentially silent on the
    currently collapsed pair. -/
theorem no_selection_iff_all_silent
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (x y : A.State X)
    (pool : List (C.Hom X Y)) :
    selectFirstSeparator C A Obs observe x y pool = none ↔
      ∀ h ∈ pool, observe Y (A.map h x) = observe Y (A.map h y) := by
  classical
  induction pool with
  | nil => simp [selectFirstSeparator]
  | cons h rest ih =>
      by_cases hsep : observe Y (A.map h x) ≠ observe Y (A.map h y)
      · simp [selectFirstSeparator, hsep]
      · have heq : observe Y (A.map h x) = observe Y (A.map h y) := by
          exact Classical.byContradiction (fun hne => hsep hne)
        simp [selectFirstSeparator, hsep, heq, ih]

/-- Positive generic controller law: whenever consequential evidence selects a
    primitive, the controller promotes exactly that selected primitive and
    regenerates/searches the grammar. -/
theorem selected_controller_is_exactly_selected_promotion
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (x y : A.State X)
    (L : Lang (C.Hom X Y))
    (verify : Expr (C.Hom X Y) → Prop)
    (budget : Nat) (pool : List (C.Hom X Y)) (selected : C.Hom X Y)
    (hsel : selectFirstSeparator C A Obs observe x y pool = some selected) :
    selectedPromotionSearch C A Obs observe x y L verify budget pool =
      boundedSearch (Promote L selected) verify budget
        (generateDepthOne (Promote L selected) pool) := by
  simp [selectedPromotionSearch, hsel]

/-- Negative developmental law.  If the entire anonymous pool is
    consequentially silent, the developmental controller performs no promotion
    at all: its result is definitionally the same cold generated search. -/
theorem absent_consequential_separation_no_structure_is_generated
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (x y : A.State X)
    (L : Lang (C.Hom X Y))
    (verify : Expr (C.Hom X Y) → Prop)
    (budget : Nat) (pool : List (C.Hom X Y))
    (hallSilent : ∀ h ∈ pool, observe Y (A.map h x) = observe Y (A.map h y)) :
    selectedPromotionSearch C A Obs observe x y L verify budget pool =
      boundedSearch L verify budget (generateDepthOne L pool) := by
  have hnone : selectFirstSeparator C A Obs observe x y pool = none :=
    (no_selection_iff_all_silent C A Obs observe x y pool).2 hallSilent
  simp [selectedPromotionSearch, hnone]

end ConsequentialSelectionClosure

#check ConsequentialSelectionClosure.selected_separator_is_member_and_separates
#check ConsequentialSelectionClosure.no_selection_iff_all_silent
#check ConsequentialSelectionClosure.selected_controller_is_exactly_selected_promotion
#check ConsequentialSelectionClosure.absent_consequential_separation_no_structure_is_generated
