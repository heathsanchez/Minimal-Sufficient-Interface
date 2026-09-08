import Std

/-!
# Recoverability-driven recursive model genesis

This file tests the concrete hypothesis suggested by the Order-5 E40909 / E11116 residuals:
a failed flat representation should be repaired by preserving (1) recoverable coordinates and
(2) the recursive rule obligation induced when an inner product is itself reduced.

Nothing below assumes the reported external rewrite-forest implementation.  The promotion rules
are derived directly from the source laws.
-/

namespace RecoverabilityModelGenesis

variable {G : Type} (op : G → G → G)

/-- E40909: `((((y*x)*y)*y)*z)*y = x`. -/
def Law40909 : Prop :=
  ∀ x y z, op (op (op (op (op y x) y) y) z) y = x

/-- E11116: `y*((x*(z*x))*(y*y)) = x`. -/
def Law11116 : Prop :=
  ∀ x y z, op y (op (op x (op z x)) (op y y)) = x

/-- E40909 forces every left translation to be injective. -/
theorem law40909_left_cancel (h : Law40909 op) (a u v : G)
    (huv : op a u = op a v) : u = v := by
  have hu := h u a u
  have hv := h v a u
  rw [huv] at hu
  exact hu.symm.trans hv

/-- E40909 forces every right translation to be surjective. -/
theorem law40909_right_surjective (h : Law40909 op) (y x : G) :
    ∃ t, op t y = x := by
  refine ⟨op (op (op (op y x) y) y) x, ?_⟩
  exact h x y x

/-- The two-coordinate encoder exposed by E40909. -/
def phi40909 (y x z : G) : G :=
  op (op (op (op y x) y) y) z

/-- The final right multiplication decodes the first coordinate. -/
theorem phi40909_decode_first (h : Law40909 op) (y x z : G) :
    op (phi40909 op y x z) y = x := by
  exact h x y z

/-- For fixed `y`, E40909 injects `G × G` into `G`.

The first coordinate is recovered by the final `* y`; after that coordinate is identified,
left cancellation recovers the second coordinate.
-/
theorem phi40909_injective (h : Law40909 op) (y : G) :
    Function.Injective (fun p : G × G => phi40909 op y p.1 p.2) := by
  intro p q hpq
  rcases p with ⟨x, z⟩
  rcases q with ⟨x', z'⟩
  have hx : x = x' := by
    have hdecode := congrArg (fun t => op t y) hpq
    simpa [phi40909, h x y z, h x' y z'] using hdecode
  subst x'
  have hz : z = z' := by
    exact law40909_left_cancel op h (op (op (op y x) y) y) z z' hpq
  exact Prod.ext rfl hz

/-- A currently available branch `A * p = q` forces a new E40909 branch.

This is the key grammar-growth obligation: treating the source equation as one isolated rewrite
rule is not closed under its own consequences.
-/
theorem law40909_forces_promotion (h : Law40909 op)
    (A p q : G) (branch : op A p = q) (z : G) :
    op (op (op (op q A) A) z) A = p := by
  have hp := h p A z
  rw [branch] at hp
  exact hp

/-- E11116 has the same higher-order phenomenon in a simpler form: if an inner `z*x` reduces,
that result must be promoted into the surrounding source-law pattern. -/
theorem law11116_forces_promotion (h : Law11116 op)
    (z x q y : G) (branch : op z x = q) :
    op y (op (op x q) (op y y)) = x := by
  have hp := h x y z
  rw [branch] at hp
  exact hp

/-- A representation that records only the original root law but not promotion is therefore not
closed under the source law once a reducible inner product is admitted.  This proposition packages
the exact extra capability demanded by both examples. -/
structure RecursiveRepairCapability where
  promote40909 :
    Law40909 op → ∀ A p q, op A p = q → ∀ z,
      op (op (op (op q A) A) z) A = p
  promote11116 :
    Law11116 op → ∀ z x q, op z x = q → ∀ y,
      op y (op (op x q) (op y y)) = x

/-- The required recursive capability is generated directly from the laws; it is not an
independent semantic guess. -/
def generatedRecursiveRepair : RecursiveRepairCapability op where
  promote40909 := by
    intro h A p q branch z
    exact law40909_forces_promotion op h A p q branch z
  promote11116 := by
    intro h z x q branch y
    exact law11116_forces_promotion op h z x q y branch

/-- Ablation witness: the generated capability contains strictly more operational information than
just the statement that a branch exists; it computes the forced continuation for every fresh `z`.
-/
theorem generated_repair_attaches_40909 (h : Law40909 op)
    (A p q : G) (branch : op A p = q) :
    ∀ z, op (op (op (op q A) A) z) A = p := by
  exact (generatedRecursiveRepair op).promote40909 h A p q branch

/-- Same attachment theorem for E11116. -/
theorem generated_repair_attaches_11116 (h : Law11116 op)
    (z x q : G) (branch : op z x = q) :
    ∀ y, op y (op (op x q) (op y y)) = x := by
  exact (generatedRecursiveRepair op).promote11116 h z x q branch

end RecoverabilityModelGenesis
