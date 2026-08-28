universe u

namespace MSI

section

variable {α : Type u}
variable (R : α → α → Prop)
variable (trans : ∀ {a b c : α}, R a b → R b c → R a c)

/--
A reusable proof operator synthesized from the repeated three-edge residual shape.
The logical primitive available underneath is only binary transitivity; the new
operator packages the missing three-edge composition as one admissible grammar node.
-/
theorem chain3 {a b c d : α}
    (hab : R a b) (hbc : R b c) (hcd : R c d) : R a d :=
  trans (trans hab hbc) hcd

/-- Held-out theorem shape 1. -/
theorem heldout₁ {a b c d : α}
    (hab : R a b) (hbc : R b c) (hcd : R c d) : R a d :=
  chain3 R trans hab hbc hcd

/-- Held-out theorem shape 2 with renamed binders. -/
theorem heldout₂ {w x y z : α}
    (hwx : R w x) (hxy : R x y) (hyz : R y z) : R w z :=
  chain3 R trans hwx hxy hyz

/-- The synthesized operator composes with the old grammar to reach farther goals. -/
theorem chain4 {a b c d e : α}
    (hab : R a b) (hbc : R b c) (hcd : R c d) (hde : R d e) : R a e :=
  trans (chain3 R trans hab hbc hcd) hde

/-- And can itself be reused as a retained proof capability. -/
theorem chain6 {a b c d e f g : α}
    (hab : R a b) (hbc : R b c) (hcd : R c d)
    (hde : R d e) (hef : R e f) (hfg : R f g) : R a g :=
  trans (chain3 R trans hab hbc hcd) (chain3 R trans hde hef hfg)

end

end MSI
