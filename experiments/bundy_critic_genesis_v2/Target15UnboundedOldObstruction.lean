import Std

/-!
A scoped proof-critic obstruction: the *entire unbounded old inference
language* consists of source premise, reflexivity, symmetry and transitivity.
Unlike V1, no depth bound causes failure. The new constructor is ordinary
function congruence, proved with the existing equality eliminator.

This theorem does NOT establish a new Lean inference principle, unrestricted
critic invention, or a strict gain against a full congruence prover.
-/
namespace BundyCriticV2

inductive Shape where
  | a | b | fa | fb
  deriving DecidableEq, Repr

inductive OldDerives : Shape → Shape → Prop where
  | refl (x : Shape) : OldDerives x x
  | premise : OldDerives .a .b
  | symm {x y : Shape} : OldDerives x y → OldDerives y x
  | trans {x y z : Shape} : OldDerives x y → OldDerives y z → OldDerives x z

def color : Shape → Nat
  | .a | .b => 0
  | .fa => 1
  | .fb => 2

theorem old_preserves_color {x y : Shape} (h : OldDerives x y) :
    color x = color y := by
  induction h with
  | refl x => rfl
  | premise => rfl
  | symm h ih => exact ih.symm
  | trans h₁ h₂ ih₁ ih₂ => exact ih₁.trans ih₂

-- Stronger than any finite search trace: this eliminates all derivations in
-- the unbounded old grammar, including arbitrary transitivity/symmetry.
theorem old_cannot_derive_lifted_equality :
    ¬ OldDerives .fa .fb := by
  intro h
  have hcolor : color Shape.fa = color Shape.fb := old_preserves_color h
  have hbad : (1 : Nat) = 2 := hcolor
  cases hbad

-- The newly admitted schema transports an independently checked equality
-- through an arbitrary function. It neither names f nor assumes injectivity.
theorem new_congruence_schema {α β : Type} (f : α → β)
    (x y : α) (h : x = y) : f x = f y := by
  cases h
  rfl

-- Negative control: dropping the shared function requirement is unsound.
theorem unconstrained_different_functions_invalid :
    ¬ ∀ (f g : Bool → Bool) (x y : Bool), x = y → f x = g y := by
  intro h
  have absurd : false = true := h (fun _ => false) (fun _ => true) false false rfl
  cases absurd

end BundyCriticV2