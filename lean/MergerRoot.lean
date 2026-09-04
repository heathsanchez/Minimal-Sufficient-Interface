import Std

/-!
# Generic finite-functional-graph theorem: merger forces root.

For every finite type `S` and total function `f : S → S`,

    (∃ y, 1 < |{x : S | f x = y}|)  →  (∃ z, |{x : S | f x = z}| = 0).

Proof mechanism: the indegree-count identity `Σ_y |f⁻¹(y)| = |S|`. If every
vertex had indegree ≥ 1 and one vertex had indegree > 1, the sum would exceed
`|S|`, a contradiction.
-/

namespace MergerRoot

open Finset

/-- Indegree-count identity: summing the fiber cardinalities over all outputs
    recovers the domain cardinality. This is the standard fiber-partition
    double-count. -/
theorem sum_fiber_card {α : Type} [Fintype α] [DecidableEq α] (f : α → α) :
    (Finset.univ.sum (fun y : α => (Finset.univ.filter (fun x : α => f x = y)).card)) =
      Fintype.card α := by
  classical
  rw [← Finset.card_univ]
  exact Finset.card_eq_sum_card_fiberwise
    (s := (Finset.univ : Finset α)) (f := f) (t := (Finset.univ : Finset α))
    (fun _ _ => Finset.mem_univ _)

/-- Main theorem: a total map with a merger (some vertex indegree > 1) has a
    root (some vertex indegree 0). -/
theorem merger_forces_root {α : Type} [Fintype α] [DecidableEq α] (f : α → α) :
    (∃ y : α, 1 < (Finset.univ.filter (fun x : α => f x = y)).card) →
    (∃ z : α, (Finset.univ.filter (fun x : α => f x = z)).card = 0) := by
  classical
  intro ⟨y, hy⟩
  by_contra h
  have hpos : ∀ z : α, 0 < (Finset.univ.filter (fun x : α => f x = z)).card := by
    intro z
    by_contra hz
    exact h ⟨z, by omega⟩
  have hsum : (Finset.univ.sum (fun z : α => (Finset.univ.filter (fun x : α => f x = z)).card)) =
      Fintype.card α := sum_fiber_card f
  -- lower bound: fiber(y) ≥ 2, all others ≥ 1, so the sum ≥ |α| + 1
  have hsum_ge : Fintype.card α + 1 ≤
      (Finset.univ.sum (fun z : α => (Finset.univ.filter (fun x : α => f x = z)).card)) := by
    calc
      Fintype.card α + 1
          = 2 + (Fintype.card α - 1) := by omega
      _ ≤ (Finset.univ.filter (fun x : α => f x = y)).card +
            ((Finset.univ : Finset α).erase y).sum
              (fun z : α => (Finset.univ.filter (fun x : α => f x = z)).card) := by
            refine Nat.add_le_add ?_ ?_
            · exact (Nat.lt_of_one_lt hy).le
            · have hmem : y ∈ (Finset.univ : Finset α) := Finset.mem_univ y
              have : ((Finset.univ : Finset α).erase y).card = Fintype.card α - 1 := by
                rw [Finset.card_erase_of_mem hmem, Finset.card_univ]
              calc
                Fintype.card α - 1 = ((Finset.univ : Finset α).erase y).card := by omega
                _ ≤ ((Finset.univ : Finset α).erase y).sum
                      (fun z : α => (Finset.univ.filter (fun x : α => f x = z)).card) := by
                      refine Finset.le_sum_of_subadditive ?_ ?_ ?_
                      · intro a b c hab hbc
                        exact Nat.le_trans hab hbc
                      · intro z hz
                        exact (hpos z).le
                      · intro z hz
                        exact Nat.zero_le _
      _ = (Finset.univ.sum (fun z : α => (Finset.univ.filter (fun x : α => f x = z)).card)) := by
            rw [← Finset.sum_erase_add _ _ (Finset.mem_univ y)]
  omega

end MergerRoot
