import KernelPurificationCycle4

namespace KernelPurificationCycle5

open KernelPurificationCycle3
open KernelPurificationCycle4

universe u v

/-- A verifier-visible support defect carries only the current and required
    support bits plus the certificate that they disagree.  No repair polarity
    is supplied as a tag. -/
structure SupportDefect where
  current : Bool
  required : Bool
  mismatch : current ≠ required

/-- The two repair directions are predicates derived from the mismatch, not
    constructors of a supplied failure-mode menu. -/
def RequiresRemoval (d : SupportDefect) : Prop :=
  d.current = true ∧ d.required = false

def RequiresGeneration (d : SupportDefect) : Prop :=
  d.current = false ∧ d.required = true

/-- A Boolean support mismatch determines its own repair direction. -/
theorem mismatch_determines_polarity (d : SupportDefect) :
    RequiresRemoval d ∨ RequiresGeneration d := by
  cases hc : d.current <;> cases hr : d.required
  · exact False.elim (d.mismatch (by simp [hc, hr]))
  · exact Or.inr ⟨hc, hr⟩
  · exact Or.inl ⟨hc, hr⟩
  · exact False.elim (d.mismatch (by simp [hc, hr]))

/-- The two derived directions are mutually exclusive. -/
theorem polarity_is_unique (d : SupportDefect) :
    ¬ (RequiresRemoval d ∧ RequiresGeneration d) := by
  intro h
  have htf : true = false := h.1.1.symm.trans h.2.1
  exact Bool.noConfusion htf

/-- At the support level, repair is simply normalization to verified required
    support.  The concrete meet/free constructions are realizations of the two
    possible signs of this same mismatch. -/
def normalizeSupport (d : SupportDefect) : Bool :=
  d.required

theorem normalization_satisfies_verified_requirement (d : SupportDefect) :
    normalizeSupport d = d.required := rfl

theorem normalization_is_strict (d : SupportDefect) :
    normalizeSupport d ≠ d.current := by
  intro h
  exact d.mismatch h.symm

/-- A negative defect is realized by the constraining meet polarity without any
    separately supplied `negative` tag. -/
def canonicalRemovalDefect : SupportDefect where
  current := true
  required := false
  mismatch := by decide

theorem removal_direction_is_inferred :
    RequiresRemoval canonicalRemovalDefect := by
  exact ⟨rfl, rfl⟩

theorem inferred_removal_matches_meet_repair :
    normalizeSupport canonicalRemovalDefect = boolMeet.meet true false := by
  rfl

/-- A positive defect is generated canonically from an actually absent old
    inhabitant together with a verified generator. -/
def deficitFromAbsentRequired
    {I : Type u} {Old : I → Type v} {Gen : I → Prop} {i : I}
    (_hold : ¬ Nonempty (Old i)) (_hgen : Gen i) : SupportDefect where
  current := false
  required := true
  mismatch := by decide

theorem deficit_direction_is_inferred
    {I : Type u} {Old : I → Type v} {Gen : I → Prop} {i : I}
    (hold : ¬ Nonempty (Old i)) (hgen : Gen i) :
    RequiresGeneration (deficitFromAbsentRequired hold hgen) := by
  exact ⟨rfl, rfl⟩

/-- The inferred positive direction is realized by the generic Cycle-3 free
    adjunction: a certified required generator makes the previously absent
    index inhabited. -/
theorem inferred_generation_matches_free_adjoin
    {I : Type u} {Old : I → Type v} {Gen : I → Prop} {i : I}
    (hold : ¬ Nonempty (Old i)) (hgen : Gen i) :
    (¬ Nonempty (Old i)) ∧ Nonempty (FreeAdjoin Old Gen i) := by
  exact ⟨hold, ⟨FreeAdjoin.forced hgen⟩⟩

/-- Exact ablation on the positive side: if there is neither retained old
    structure nor a certified generator, the free completion remains empty. -/
theorem no_support_no_generation
    {I : Type u} {Old : I → Type v} {i : I}
    (hold : ¬ Nonempty (Old i)) :
    ¬ Nonempty (FreeAdjoin Old (fun _ => False) i) := by
  intro h
  rcases h with ⟨z⟩
  cases z with
  | old x => exact hold ⟨x⟩
  | forced g => exact g

/-- Cycle-5 decision: once a verifier exposes current-vs-required support, the
    sign of the mismatch itself determines whether repair must constrain or
    generate.  The semantic labels `extensional`, `identity`, `composition`,
    `negative`, and `positive` are not needed to choose the direction. -/
theorem verifier_mismatch_selects_repair_direction :
    (∀ d : SupportDefect,
      RequiresRemoval d ∨ RequiresGeneration d) ∧
    RequiresRemoval canonicalRemovalDefect ∧
    (∀ (I : Type) (Old : I → Type) (Gen : I → Prop) (i : I),
      (¬ Nonempty (Old i)) → Gen i →
      Nonempty (FreeAdjoin Old Gen i)) := by
  constructor
  · exact mismatch_determines_polarity
  constructor
  · exact removal_direction_is_inferred
  · intro I Old Gen i hold hgen
    exact (inferred_generation_matches_free_adjoin hold hgen).2

#check mismatch_determines_polarity
#check polarity_is_unique
#check normalization_is_strict
#check inferred_removal_matches_meet_repair
#check inferred_generation_matches_free_adjoin
#check no_support_no_generation
#check verifier_mismatch_selects_repair_direction

end KernelPurificationCycle5
