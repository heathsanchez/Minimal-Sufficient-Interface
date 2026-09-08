import LemmaSynthesis.AustinRecursiveObligation

namespace AustinRecursiveObligation

/-- Opposite magma operation. -/
def opp {G : Type} (op : BinOp G) : BinOp G := fun a b => op b a

/-- E5295 in the orientation used by the countermodel search:
    `y ⋄ (z ⋄ (y ⋄ (y ⋄ (x ⋄ y)))) = x`. -/
def Law5295 {G : Type} (op : BinOp G) : Prop :=
  ∀ x y z : G, op y (op z (op y (op y (op x y)))) = x

/-- E5295 is exactly the binary-tree dual of E40909. -/
theorem law40909_to_law5295_opp {G : Type} (op : BinOp G)
    (h : Law40909 op) : Law5295 (opp op) := by
  intro x y z
  simpa [opp] using h x y z

/-- Duality is involutive at the law level. -/
theorem law5295_to_law40909_opp {G : Type} (op : BinOp G)
    (h : Law5295 op) : Law40909 (opp op) := by
  intro x y z
  simpa [opp] using h x y z

/-- A branch in E5295 is promoted by the dual image of the E40909 constructor. -/
theorem law5295_promotes_branch {G : Type} (op : BinOp G)
    (hLaw : Law5295 op) {A p q : G} (hBranch : op A p = q) (z : G) :
    op p (op z (op p (op p q))) = A := by
  simpa [hBranch] using hLaw A p z

end AustinRecursiveObligation
