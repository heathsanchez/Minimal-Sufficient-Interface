import Std

universe u v w

namespace QuotientSufficiency

variable {X : Type u} {Q : Type v} {Y : Type w}

/-- A representation q is sufficient for a protected target exactly when the
    target can be recovered from q alone. -/
def FactorsThrough (q : X → Q) (target : X → Y) : Prop :=
  ∃ lift : Q → Y, ∀ x, lift (q x) = target x

/-- A same-representation / different-target pair is a decisive witness that
    the proposed quotient has discarded target-relevant information. -/
def SeparatingWitness (q : X → Q) (target : X → Y) : Prop :=
  ∃ x y, q x = q y ∧ target x ≠ target y

/-- One separating witness is sufficient to refute quotient sufficiency. -/
theorem witness_refutes_factorization
    {q : X → Q} {target : X → Y}
    (h : SeparatingWitness q target) :
    ¬ FactorsThrough q target := by
  intro hfactor
  rcases hfactor with ⟨lift, hlift⟩
  rcases h with ⟨x, y, hq, htarget⟩
  apply htarget
  calc
    target x = lift (q x) := (hlift x).symm
    _ = lift (q y) := congrArg lift hq
    _ = target y := hlift y

/-- Conversely, every genuine factorization rules out a separating witness. -/
theorem factorization_has_no_witness
    {q : X → Q} {target : X → Y}
    (h : FactorsThrough q target) :
    ¬ SeparatingWitness q target :=
  fun hw => witness_refutes_factorization hw h

/-!
Finite regression witness from Quinn Porter,
"Composition Does Not Determine Organization" (2026).

The two four-site fields
  K1 = (B4, B0, B4, B0)
  K2 = (B4, B4, B0, B0)
have the same histogram (two B0 and two B4 sites), Omega = 1, and mean
polarity M = 0, while their staggered orders are 1 and 0 respectively.
Only those exact stated consequences are encoded here; no physical dynamics
or broader Period Lattice claims are imported.
-/

inductive ExtremeArrangement where
  | alternating
  | blocked
  deriving DecidableEq, Repr

def histogram : ExtremeArrangement → Nat × Nat
  | .alternating => (2, 2)
  | .blocked => (2, 2)

def multiplicity : ExtremeArrangement → Nat
  | .alternating => 1
  | .blocked => 1

def meanNumerator : ExtremeArrangement → Int
  | .alternating => 0
  | .blocked => 0

def coarse :
    ExtremeArrangement → ((Nat × Nat) × Nat × Int) :=
  fun k => (histogram k, multiplicity k, meanNumerator k)

def staggeredOrder : ExtremeArrangement → Int
  | .alternating => 1
  | .blocked => 0

theorem paper_pair_same_coarse :
    coarse .alternating = coarse .blocked := by
  rfl

theorem paper_pair_target_diff :
    staggeredOrder .alternating ≠ staggeredOrder .blocked := by
  decide

theorem period_lattice_coarse_not_sufficient :
    ¬ FactorsThrough coarse staggeredOrder := by
  apply witness_refutes_factorization
  exact ⟨.alternating, .blocked, paper_pair_same_coarse, paper_pair_target_diff⟩

end QuotientSufficiency
