import LemmaSynthesis.AdequacyTester

/-! A reusable proof rule for the existing adequacy tester. A concrete
    certificate need only establish a pointwise factorization, rather than
    normalize the quadratic list of all possible witness pairs. -/
namespace ConsequenceFactorization

theorem no_witnesses_of_factor
    {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) (g : β → γ)
    (h : ∀ x ∈ xs, F x = g (Q x)) :
    AdequacyTester.adequacyWitnesses xs Q F = [] := by
  apply List.eq_nil_iff_forall_not_mem.mpr
  intro p hp
  have hv := AdequacyTester.search_correct hp
  have hm := (List.mem_filter.mp hp).1
  rcases List.mem_flatMap.mp hm with ⟨a, ha, hm'⟩
  rcases List.mem_map.mp hm' with ⟨b, hb, hab⟩
  subst p
  apply hv.2
  calc
    F a = g (Q a) := h a ha
    _ = g (Q b) := congrArg g hv.1
    _ = F b := (h b hb).symm

end ConsequenceFactorization
