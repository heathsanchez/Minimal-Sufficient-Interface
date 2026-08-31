namespace VerifierInducesBehavioralHypothesisSpace

universe u v

/-- The behavioral hypothesis ontology is not the whole function space C → Bool.
    It is exactly the image of raw candidates under the verifier profile map. -/
abbrev BehaviorClass (H : Type u) (C : Type v) (V : H → C → Bool) :=
  {p : C → Bool // ∃ h : H, p = V h}

/-- Every raw candidate has a canonical operational class. -/
def classOf {H : Type u} {C : Type v} (V : H → C → Bool) (h : H) :
    BehaviorClass H C V :=
  ⟨V h, ⟨h, rfl⟩⟩

/-- Equality in the induced ontology is exactly verifier-profile equality. -/
theorem class_eq_iff_profile_eq {H : Type u} {C : Type v}
    (V : H → C → Bool) (h₁ h₂ : H) :
    classOf V h₁ = classOf V h₂ ↔ V h₁ = V h₂ := by
  constructor
  · intro h
    exact congrArg Subtype.val h
  · intro h
    exact Subtype.ext h

/-- Every verifier distinction is necessarily retained by the induced ontology. -/
theorem verifier_distinction_forces_class_distinction {H : Type u} {C : Type v}
    (V : H → C → Bool) (h₁ h₂ : H) (c : C)
    (hdiff : V h₁ c ≠ V h₂ c) :
    classOf V h₁ ≠ classOf V h₂ := by
  intro hclass
  have hprofiles : V h₁ = V h₂ :=
    (class_eq_iff_profile_eq V h₁ h₂).mp hclass
  exact hdiff (congrFun hprofiles c)

/-- Conversely, verifier-indistinguishable raw candidates collapse to the same
    behavioral hypothesis. -/
theorem verifier_indistinguishable_candidates_collapse {H : Type u} {C : Type v}
    (V : H → C → Bool) (h₁ h₂ : H)
    (hsame : ∀ c, V h₁ c = V h₂ c) :
    classOf V h₁ = classOf V h₂ := by
  apply (class_eq_iff_profile_eq V h₁ h₂).mpr
  funext c
  exact hsame c

/-- A language now selects only verifier-induced behavioral classes. -/
structure InducedLanguage {H : Type u} {C : Type v} (V : H → C → Bool) where
  admits : BehaviorClass H C V → Prop

/-- Coverage residual names a raw candidate whose induced operational class is
    absent from the current language.  No arbitrary semantic function is supplied. -/
structure InducedCoverageResidual {H : Type u} {C : Type v}
    (V : H → C → Bool) (L : InducedLanguage V) where
  target : H
  uncovered : ¬ L.admits (classOf V target)

/-- Least completion at the induced behavioral level. -/
def complete {H : Type u} {C : Type v} {V : H → C → Bool}
    (L : InducedLanguage V) (target : BehaviorClass H C V) : InducedLanguage V where
  admits b := L.admits b ∨ b = target

theorem includeOld {H : Type u} {C : Type v} {V : H → C → Bool}
    (L : InducedLanguage V) (target b : BehaviorClass H C V)
    (hb : L.admits b) :
    (complete L target).admits b := by
  exact Or.inl hb

theorem induced_target_admitted {H : Type u} {C : Type v} {V : H → C → Bool}
    {L : InducedLanguage V} (r : InducedCoverageResidual V L) :
    (complete L (classOf V r.target)).admits (classOf V r.target) := by
  exact Or.inr rfl

theorem no_unrelated_class_added {H : Type u} {C : Type v} {V : H → C → Bool}
    (L : InducedLanguage V) (target b : BehaviorClass H C V)
    (hold : ¬ L.admits b) (hne : b ≠ target) :
    ¬ (complete L target).admits b := by
  intro hb
  rcases hb with hb | hb
  · exact hold hb
  · exact hne hb

theorem completion_least {H : Type u} {C : Type v} {V : H → C → Bool}
    (L M : InducedLanguage V) (target : BehaviorClass H C V)
    (hold : ∀ b, L.admits b → M.admits b)
    (htarget : M.admits target) :
    ∀ b, (complete L target).admits b → M.admits b := by
  intro b hb
  rcases hb with hb | hb
  · exact hold b hb
  · simpa [hb] using htarget

/-- Concrete raw candidates.  The ontology of behavior is not given separately;
    it is induced from these candidates by the verifier. -/
inductive RawCandidate where
  | constFalse
  | constTrue
  | negate
  deriving DecidableEq

open RawCandidate

def eval : RawCandidate → Bool → Bool
  | constFalse, _ => false
  | constTrue, _ => true
  | negate, b => !b

/-- Current language contains only the induced classes of the two constant raw
    candidates. -/
def currentLanguage : InducedLanguage eval where
  admits b := b = classOf eval constFalse ∨ b = classOf eval constTrue

theorem negate_differs_from_constFalse :
    classOf eval negate ≠ classOf eval constFalse := by
  apply verifier_distinction_forces_class_distinction eval negate constFalse false
  decide

theorem negate_differs_from_constTrue :
    classOf eval negate ≠ classOf eval constTrue := by
  apply verifier_distinction_forces_class_distinction eval negate constTrue true
  decide

theorem negate_class_uncovered :
    ¬ currentLanguage.admits (classOf eval negate) := by
  rintro (h | h)
  · exact negate_differs_from_constFalse h
  · exact negate_differs_from_constTrue h

def residual : InducedCoverageResidual eval currentLanguage where
  target := negate
  uncovered := negate_class_uncovered

/-- The main result removes the previously supplied full semantic behavior space.
    Hypotheses are operational classes generated from raw candidates by verifier
    consequence.  Empty coverage then forces the least extension by exactly the
    uncovered induced class.

    Remaining scaffold: the raw candidate carrier and verifier context family. -/
theorem verifier_induced_behavior_feeds_language_genesis :
    (¬ currentLanguage.admits (classOf eval residual.target)) ∧
    (complete currentLanguage (classOf eval residual.target)).admits
      (classOf eval residual.target) ∧
    (∀ b, currentLanguage.admits b →
      (complete currentLanguage (classOf eval residual.target)).admits b) ∧
    (∀ b,
      ¬ currentLanguage.admits b →
      b ≠ classOf eval residual.target →
      ¬ (complete currentLanguage (classOf eval residual.target)).admits b) := by
  refine ⟨residual.uncovered, induced_target_admitted residual, ?_, ?_⟩
  · intro b hb
    exact includeOld currentLanguage (classOf eval residual.target) b hb
  · intro b hold hne
    exact no_unrelated_class_added currentLanguage (classOf eval residual.target) b hold hne

#check class_eq_iff_profile_eq
#check verifier_distinction_forces_class_distinction
#check verifier_indistinguishable_candidates_collapse
#check induced_target_admitted
#check no_unrelated_class_added
#check completion_least
#check negate_class_uncovered
#check verifier_induced_behavior_feeds_language_genesis

end VerifierInducesBehavioralHypothesisSpace
