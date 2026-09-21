import Mathlib.Data.Fintype.Basic

namespace CLC

inductive Verdict
  | unknown
  | eq
  | dist
  deriving DecidableEq, Repr

instance : Fintype Verdict where
  elems := {.unknown, .eq, .dist}
  complete := by intro v; cases v <;> simp

def Verdict.le : Verdict → Verdict → Prop
  | .unknown, _ => True
  | .eq, .eq => True
  | .dist, .dist => True
  | _, _ => False

instance : LE Verdict := ⟨Verdict.le⟩

@[instance_reducible] def Verdict.decLe : DecidableRel Verdict.le
  | .unknown, _ => isTrue trivial
  | .eq, .eq => isTrue trivial
  | .dist, .dist => isTrue trivial
  | .eq, .unknown => isFalse id
  | .eq, .dist => isFalse id
  | .dist, .unknown => isFalse id
  | .dist, .eq => isFalse id

instance (a b : Verdict) : Decidable (a ≤ b) := Verdict.decLe a b

instance : PartialOrder Verdict where
  le := Verdict.le
  le_refl := by intro a; cases a <;> trivial
  le_trans := by
    intro a b c hab hbc
    cases a <;> cases b <;> cases c <;> simp_all [Verdict.le]
  le_antisymm := by
    intro a b hab hba
    cases a <;> cases b <;> simp_all [Verdict.le]

def Decisive (v : Verdict) : Prop := v = .eq ∨ v = .dist

@[simp] theorem unknown_le (v : Verdict) : Verdict.unknown ≤ v := by
  cases v <;> trivial

theorem decisive_eq_of_le {v w : Verdict} (hv : Decisive v) (hvw : v ≤ w) : w = v := by
  rcases hv with rfl | rfl
  · change Verdict.le .eq w at hvw
    cases w <;> simp_all [Verdict.le]
  · change Verdict.le .dist w at hvw
    cases w <;> simp_all [Verdict.le]

end CLC
