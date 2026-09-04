import Mathlib

/-!
# Generic finite-functional-graph theorem: merger forces root.

For every finite type `S` and total function `f : S → S`,

    (∃ y, 1 < |{x : S | f x = y}|)  →  (∃ z, |{x : S | f x = z}| = 0).

Proof: the indegree-count identity `Σ_y |f⁻¹(y)| = |S|`. If every vertex had
indegree ≥ 1 and one vertex had indegree > 1, the sum would exceed `|S|`.
-/

namespace MergerRoot

open Finset

/-- Indegree-count identity: summing the fiber cardinalities over all outputs
    recovers the domain cardinality (fiber-partition double-count). -/
theorem sum_fiber_card {α : Type} [Fintype α] [DecidableEq α] (f : α → α) :
    (Finset.univ.sum (fun y : α => (Finset.univ.filter (fun x : α => f x = y)).card)) =
      Fintype.card α := by
  classical
  rw [← Finset.card_univ]
  exact Finset.card_eq_sum_card_fiberwise
    (s := (Finset.univ : Finset α)) (f := f) (t := (Finset.univ : Finset α))
    (fun _ _ => Finset.mem_univ _)

/-- A total map on a finite type with a merger (some vertex indegree > 1) has a
    root (some vertex indegree 0). -/
theorem merger_forces_root {α : Type} [Fintype α] [DecidableEq α] (f : α → α) :
    (∃ y : α, 1 < (Finset.univ.filter (fun x : α => f x = y)).card) →
    (∃ z : α, (Finset.univ.filter (fun x : α => f x = z)).card = 0) := by
  classical
  let fiber (z : α) : Nat := (Finset.univ.filter (fun x : α => f x = z)).card
  intro ⟨y, hy⟩
  by_contra h
  have hpos : ∀ z : α, 0 < fiber z := by
    intro z
    by_contra hz
    exact h ⟨z, hz⟩
  have hsum : (Finset.univ.sum fiber) = Fintype.card α := by
    change (Finset.univ.sum (fun z : α => (Finset.univ.filter (fun x : α => f x = z)).card)) =
      Fintype.card α
    exact sum_fiber_card f
  have hsum_ge_erase : ((Finset.univ : Finset α).erase y).card ≤
      ((Finset.univ : Finset α).erase y).sum fiber := by
    calc
      ((Finset.univ : Finset α).erase y).card
          = ((Finset.univ : Finset α).erase y).sum (fun _ : α => (1 : Nat)) := by
              rw [Finset.sum_const, Nat.nsmul_eq_mul, Nat.mul_one]
      _ ≤ ((Finset.univ : Finset α).erase y).sum fiber := by
              refine Finset.sum_le_sum ?_
              intro z _hz
              exact Nat.succ_le_of_lt (hpos z)
  have hdecomp : (Finset.univ.sum fiber) =
      (∑ z in (Finset.univ : Finset α).erase y, fiber z) + fiber y := by
    exact Finset.sum_erase_add
      (s := (Finset.univ : Finset α)) (f := fiber) (Finset.mem_univ y)
  have hge : Fintype.card α + 1 ≤ (Finset.univ.sum fiber) := by
    rw [hdecomp]
    calc
      Fintype.card α + 1 = 2 + (Fintype.card α - 1) := by omega
      _ ≤ fiber y + ((Finset.univ : Finset α).erase y).sum fiber := by
          refine Nat.add_le_add ?_ ?_
          · exact Nat.succ_le_of_lt hy
          · calc
              Fintype.card α - 1 = ((Finset.univ : Finset α).erase y).card := by
                  rw [Finset.card_erase_of_mem (Finset.mem_univ y), Finset.card_univ]
              _ ≤ ((Finset.univ : Finset α).erase y).sum fiber := hsum_ge_erase
      _ = (∑ z in (Finset.univ : Finset α).erase y, fiber z) + fiber y := by
          rw [Nat.add_comm]
  omega

end MergerRoot
