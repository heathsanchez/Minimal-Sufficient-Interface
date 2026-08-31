import InfiniteBitOmegaFixedPoint
import FailureGeneratedOmegaPlusOne

namespace ExtensionalOmegaFailureObstruction

/-- A family of observations is point-separating when observational agreement
    already forces equality of states. -/
def PointSeparating {X I O : Type}
    (observe : I → X → O) (C : I → Prop) : Prop :=
  ∀ x y, (∀ i, C i → observe i x = observe i y) → x = y

/-- The abstract shape of the extensional residual used by quotient refinement:
    two genuinely distinct states remain invisible to every retained
    observation. -/
structure ExtensionalFailure {X I O : Type}
    (observe : I → X → O) (C : I → Prop) where
  left : X
  right : X
  distinct : left ≠ right
  invisible : ∀ i, C i → observe i left = observe i right

/-- Once the retained observation family is point-separating, an invisible
    distinct-pair residual is impossible. -/
theorem pointSeparating_blocks_extensional_failure
    {X I O : Type} {observe : I → X → O} {C : I → Prop}
    (hsep : PointSeparating observe C) :
    ¬ Nonempty (ExtensionalFailure observe C) := by
  rintro ⟨r⟩
  exact r.distinct (hsep r.left r.right r.invisible)

/-- Conversely, absence of all invisible distinct-pair residuals is exactly
    point separation. -/
theorem no_extensional_failure_implies_pointSeparating
    {X I O : Type} {observe : I → X → O} {C : I → Prop}
    (hno : ¬ Nonempty (ExtensionalFailure observe C)) :
    PointSeparating observe C := by
  intro x y hagree
  apply Classical.byContradiction
  intro hxy
  exact hno ⟨{
    left := x
    right := y
    distinct := hxy
    invisible := hagree
  }⟩

/-- The exact V16 Nat-bit observation map, with the index before the state. -/
def natBitObserve (k n : Nat) : Bool :=
  InfiniteBitOmegaFixedPoint.bit n k

/-- At the genuine Nat omega limit, the retained finite-bit family is already
    point-separating.  No latent state component is left outside the family. -/
theorem exact_nat_omega_is_pointSeparating :
    PointSeparating natBitObserve
      InfiniteBitOmegaFixedPoint.omegaLanguage := by
  intro x y hagree
  apply Nat.eq_of_testBit_eq
  intro k
  have hk := hagree k (by trivial)
  simpa [natBitObserve, InfiniteBitOmegaFixedPoint.bit] using hk

/-- Therefore the exact Nat omega closure admits no extensional representation
    failure of the form distinct-but-observationally-indistinguishable. -/
theorem exact_nat_omega_has_no_extensional_failure :
    ¬ Nonempty
      (ExtensionalFailure natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage) := by
  exact pointSeparating_blocks_extensional_failure
    exact_nat_omega_is_pointSeparating

/-- The obstruction is not peculiar to bits: any proposed post-limit genesis
    law whose *only* trigger is an invisible distinct pair is silent at every
    point-separating closure. -/
def InvisiblePairEvidence {X I O : Type}
    (observe : I → X → O) (C : I → Prop) : Prop :=
  Nonempty (ExtensionalFailure observe C)

theorem pointSeparating_blocks_invisible_pair_genesis
    {X I O : Type} {observe : I → X → O} {C : I → Prop}
    (hsep : PointSeparating observe C) :
    ¬ InvisiblePairEvidence observe C := by
  exact pointSeparating_blocks_extensional_failure hsep

/-- Coordinate observations used by the existing `Nat × Bool` omega+1 model.
    They inspect the Nat component only. -/
def suppliedCoordinateObserve
    (k : Nat) (w : FailureGeneratedOmegaPlusOne.World) : Bool :=
  w.1.testBit k

def allCoordinates : Nat → Prop := fun _ => True

/-- In the existing omega+1 construction, the completed coordinate family is
    deliberately *not* point-separating because the supplied Bool component is
    invisible to every finite coordinate. -/
theorem supplied_hidden_bool_breaks_pointSeparation :
    ¬ PointSeparating suppliedCoordinateObserve allCoordinates := by
  intro hsep
  have hEq :
      ((0, false) : FailureGeneratedOmegaPlusOne.World) = (0, true) :=
    hsep (0, false) (0, true) (by
      intro k _
      rfl)
  have hBool : false = true := congrArg Prod.snd hEq
  simp at hBool

/-- The canonical post-limit failure used by the existing omega+1 theorem
    preserves the entire Nat component and changes only the pre-existing Bool
    mode. -/
theorem canonical_omega_failure_changes_only_supplied_mode
    (w : FailureGeneratedOmegaPlusOne.World) :
    (FailureGeneratedOmegaPlusOne.omegaFailure w).left.1 =
        (FailureGeneratedOmegaPlusOne.omegaFailure w).right.1 ∧
    (FailureGeneratedOmegaPlusOne.omegaFailure w).left.2 ≠
        (FailureGeneratedOmegaPlusOne.omegaFailure w).right.2 := by
  constructor
  · rfl
  · simp [FailureGeneratedOmegaPlusOne.omegaFailure,
      FailureGeneratedOmegaPlusOne.toggle]

/-- Exact scientific boundary: the genuine Nat-bit omega closure has no
    extensional residual left, whereas the current omega+1 witness exists only
    after enlarging the world with an observationally hidden Bool mode. -/
theorem extensional_omega_plus_one_boundary :
    (¬ Nonempty
      (ExtensionalFailure natBitObserve
        InfiniteBitOmegaFixedPoint.omegaLanguage)) ∧
    Nonempty
      (FailureGeneratedOmegaPlusOne.Failure
        FailureGeneratedOmegaPlusOne.omegaStage) := by
  exact ⟨exact_nat_omega_has_no_extensional_failure,
    ⟨FailureGeneratedOmegaPlusOne.omegaFailure (0, false)⟩⟩

#check pointSeparating_blocks_extensional_failure
#check no_extensional_failure_implies_pointSeparating
#check exact_nat_omega_is_pointSeparating
#check exact_nat_omega_has_no_extensional_failure
#check pointSeparating_blocks_invisible_pair_genesis
#check supplied_hidden_bool_breaks_pointSeparation
#check canonical_omega_failure_changes_only_supplied_mode
#check extensional_omega_plus_one_boundary

end ExtensionalOmegaFailureObstruction
