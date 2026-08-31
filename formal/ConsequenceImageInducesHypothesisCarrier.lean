namespace ConsequenceImageInducesHypothesisCarrier

/-- A raw hypothesis world is used only to expose verifier consequences.  The
    retained operational carrier below will not retain this hidden domain. -/
structure HypothesisWorld (β : Type) where
  Hyp : Type
  verdict : Hyp → β

/-- The consequence image exposed by a world. -/
def ObservableImage {β : Type} (W : HypothesisWorld β) : β → Prop :=
  fun b => ∃ h : W.Hyp, W.verdict h = b

/-- A hypothesis carrier generated solely from an observable consequence image.
    Its elements are exactly verifier outcomes that have actually been realized. -/
def InducedCarrier {β : Type} (P : β → Prop) :=
  {b : β // P b}

/-- Every raw hypothesis maps canonically into the consequence-induced carrier. -/
def induce {β : Type} (W : HypothesisWorld β) (h : W.Hyp) :
    InducedCarrier (ObservableImage W) :=
  ⟨W.verdict h, ⟨h, rfl⟩⟩

/-- The verifier outcome is recovered from the induced carrier with no access to
    the hidden raw hypothesis domain. -/
def inducedVerdict {β : Type} {P : β → Prop} : InducedCarrier P → β :=
  fun q => q.1

theorem induced_carrier_is_sufficient_for_verifier {β : Type}
    (W : HypothesisWorld β) (h : W.Hyp) :
    inducedVerdict (induce W h) = W.verdict h := by
  rfl

/-- Every realized consequence has a preimage: no verifier-visible outcome is
    lost when the hidden raw carrier is replaced by the induced carrier. -/
theorem induce_is_surjective {β : Type} (W : HypothesisWorld β) :
    ∀ q : InducedCarrier (ObservableImage W), ∃ h : W.Hyp, induce W h = q := by
  intro q
  rcases q.2 with ⟨h, hh⟩
  refine ⟨h, ?_⟩
  apply Subtype.ext
  exact hh

/-- Consequently, the retained carrier depends only on the consequence image:
    extensionally equal images induce the same carrier type. -/
theorem same_image_same_induced_carrier {β : Type} {P Q : β → Prop}
    (h : P = Q) : InducedCarrier P = InducedCarrier Q := by
  cases h
  rfl

/-- Old world: two hidden hypotheses, but both have the same consequence. -/
def oldWorld : HypothesisWorld Bool where
  Hyp := Bool
  verdict := fun _ => false

/-- New world: the richer consequence distinguishes the same two raw hypotheses. -/
def refinedWorld : HypothesisWorld Bool where
  Hyp := Bool
  verdict := fun h => h

/-- The old consequence-generated carrier has no two distinct elements. -/
theorem old_induced_carrier_has_no_distinct_points :
    ¬ ∃ a b : InducedCarrier (ObservableImage oldWorld), a ≠ b := by
  rintro ⟨a, b, hab⟩
  apply hab
  apply Subtype.ext
  rcases a.2 with ⟨ha, hha⟩
  rcases b.2 with ⟨hb, hhb⟩
  calc
    a.1 = false := hha.symm
    _ = b.1 := hhb

/-- The refined consequence-generated carrier genuinely contains two distinct
    operational hypotheses. -/
theorem refined_induced_carrier_has_distinct_points :
    ∃ a b : InducedCarrier (ObservableImage refinedWorld), a ≠ b := by
  let a : InducedCarrier (ObservableImage refinedWorld) :=
    ⟨false, ⟨false, rfl⟩⟩
  let b : InducedCarrier (ObservableImage refinedWorld) :=
    ⟨true, ⟨true, rfl⟩⟩
  refine ⟨a, b, ?_⟩
  intro h
  have hv : false = true := congrArg Subtype.val h
  cases hv

/-- Developmental carrier genesis: the retained hypothesis domain can be formed
    from consequence alone, and richer consequence can generate a strictly more
    discriminating carrier without reconstructing hidden raw hypothesis syntax. -/
theorem consequence_generates_and_refines_hypothesis_carrier :
    (¬ ∃ a b : InducedCarrier (ObservableImage oldWorld), a ≠ b) ∧
    (∃ a b : InducedCarrier (ObservableImage refinedWorld), a ≠ b) := by
  exact ⟨old_induced_carrier_has_no_distinct_points,
    refined_induced_carrier_has_distinct_points⟩

#check induced_carrier_is_sufficient_for_verifier
#check induce_is_surjective
#check same_image_same_induced_carrier
#check old_induced_carrier_has_no_distinct_points
#check refined_induced_carrier_has_distinct_points
#check consequence_generates_and_refines_hypothesis_carrier

end ConsequenceImageInducesHypothesisCarrier
