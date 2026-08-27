import Std

universe u v w

/-- A monoid acting on a state space.  We keep the laws explicit so this file
    depends only on Lean/Std, not Mathlib. -/
structure ActionMonoid (M : Type u) (X : Type v) where
  one : M
  mul : M → M → M
  act : M → X → X
  one_mul : ∀ a, mul one a = a
  mul_one : ∀ a, mul a one = a
  mul_assoc : ∀ a b c, mul (mul a b) c = mul a (mul b c)
  one_act : ∀ x, act one x = x
  mul_act : ∀ a b x, act (mul a b) x = act a (act b x)

namespace BehaviouralCongruence

variable {M : Type u} {X : Type v} {O : Type w}
variable (A : ActionMonoid M X) (obs : X → O)

/-- Equality under every reachable future observation. -/
def BehEq (x y : X) : Prop :=
  ∀ m : M, obs (A.act m x) = obs (A.act m y)

/-- An equivalence relation is invariant when every reachable action preserves it. -/
def Invariant (R : X → X → Prop) : Prop :=
  ∀ m x y, R x y → R (A.act m x) (A.act m y)

/-- Observation compatibility means the relation never identifies states that
    the current protected observation already distinguishes. -/
def ObsCompatible (R : X → X → Prop) : Prop :=
  ∀ x y, R x y → obs x = obs y

/-- Behavioural equivalence is reflexive. -/
theorem behEq_refl (x : X) : BehEq A obs x x := by
  intro m
  rfl

/-- Behavioural equivalence is symmetric. -/
theorem behEq_symm {x y : X} (h : BehEq A obs x y) : BehEq A obs y x := by
  intro m
  exact (h m).symm

/-- Behavioural equivalence is transitive. -/
theorem behEq_trans {x y z : X}
    (hxy : BehEq A obs x y) (hyz : BehEq A obs y z) : BehEq A obs x z := by
  intro m
  exact (hxy m).trans (hyz m)

/-- Behavioural equivalence is contained in the observation kernel. -/
theorem behEq_obsCompatible : ObsCompatible obs (BehEq A obs) := by
  intro x y h
  simpa [A.one_act] using h A.one

/-- Behavioural equivalence is invariant under every reachable action. -/
theorem behEq_invariant : Invariant A (BehEq A obs) := by
  intro g x y h m
  simpa [A.mul_act] using h (A.mul m g)

/-- Greatest-invariant characterization:

    BehEq is the greatest reachable-action-invariant relation contained in ker(obs).

    No equivalence assumptions on R are needed for maximality; if R is an
    invariant equivalence relation compatible with obs, it is therefore included
    automatically. -/
theorem greatest_invariant
    (R : X → X → Prop)
    (hInv : Invariant A R)
    (hObs : ObsCompatible obs R) :
    ∀ x y, R x y → BehEq A obs x y := by
  intro x y hxy m
  exact hObs (A.act m x) (A.act m y) (hInv m x y hxy)

/-- Setoid induced by all-reachable-futures behavioural equivalence. -/
def behSetoid : Setoid X where
  r := BehEq A obs
  iseqv := {
    refl := behEq_refl A obs
    symm := by intro x y; exact behEq_symm A obs
    trans := by intro x y z; exact behEq_trans A obs
  }

abbrev BehaviourQuotient := Quotient (behSetoid A obs)

/-- Every reachable action descends to the behavioural quotient. -/
def descend (g : M) : BehaviourQuotient A obs → BehaviourQuotient A obs :=
  Quotient.lift
    (fun x => Quotient.mk (behSetoid A obs) (A.act g x))
    (by
      intro x y hxy
      exact Quotient.sound (behEq_invariant A obs g x y hxy))

/-- The descended action has the expected value on representatives. -/
theorem descend_mk (g : M) (x : X) :
    descend A obs g (Quotient.mk (behSetoid A obs) x) =
      Quotient.mk (behSetoid A obs) (A.act g x) := rfl

/-- Descending the identity gives the identity quotient map. -/
theorem descend_one :
    ∀ q : BehaviourQuotient A obs, descend A obs A.one q = q := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [descend_mk, A.one_act]

/-- Descending preserves composition. -/
theorem descend_mul (g f : M) :
    ∀ q : BehaviourQuotient A obs,
      descend A obs (A.mul g f) q =
        descend A obs g (descend A obs f q) := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [descend_mk, descend_mk, descend_mk, A.mul_act]

/-- Uniqueness on quotient representatives: a quotient map agreeing with the
    action on every representative is extensionally the descended map. -/
theorem descend_unique (g : M)
    (F : BehaviourQuotient A obs → BehaviourQuotient A obs)
    (hF : ∀ x : X,
      F (Quotient.mk (behSetoid A obs) x) =
        Quotient.mk (behSetoid A obs) (A.act g x)) :
    ∀ q, F q = descend A obs g q := by
  intro q
  refine Quotient.inductionOn q ?_
  intro x
  rw [descend_mk]
  exact hF x

section FiniteRecovery

variable [Fintype M] [DecidableEq M]

/-- Equivalence induced by the currently retained finite set of continuations. -/
def EqBy (B : Finset M) (x y : X) : Prop :=
  ∀ m, m ∈ B → obs (A.act m x) = obs (A.act m y)

/-- No reachable continuation can further split a pair currently merged by B. -/
def Terminal (B : Finset M) : Prop :=
  ∀ m x y, EqBy A obs B x y → obs (A.act m x) = obs (A.act m y)

/-- Exact stopping: no reachable separator remains iff the current finite interface
    already equals all-futures behavioural equivalence. -/
theorem terminal_exact (B : Finset M) :
    Terminal A obs B ↔ ∀ x y, EqBy A obs B x y ↔ BehEq A obs x y := by
  constructor
  · intro hterm x y
    constructor
    · intro hB m
      exact hterm m x y hB
    · intro hstar m hm
      exact hstar m
  · intro h m x y hB
    exact (h x y).mp hB m

/-- A verifier-driven refinement step adds a reachable continuation that actually
    separates a pair still merged by the current interface. -/
def RefineStep (B B' : Finset M) : Prop :=
  ∃ m x y,
    EqBy A obs B x y ∧
    obs (A.act m x) ≠ obs (A.act m y) ∧
    B' = insert m B

/-- A genuine separator can never already be in the retained basis. -/
theorem refineStep_fresh {B B' : Finset M}
    (h : RefineStep A obs B B') :
    ∃ m, m ∉ B ∧ B' = insert m B := by
  rcases h with ⟨m, x, y, hB, hsep, rfl⟩
  refine ⟨m, ?_, rfl⟩
  intro hm
  exact hsep (hB m hm)

/-- Every genuine verifier-driven refinement step increases the retained basis
    cardinality by exactly one. -/
theorem refineStep_card {B B' : Finset M}
    (h : RefineStep A obs B B') :
    B'.card = B.card + 1 := by
  rcases refineStep_fresh A obs h with ⟨m, hm, rfl⟩
  simp [hm]

/-- Finite recovery theorem.

    Any process over a finite reachable action monoid that, whenever it is not
    terminal, incorporates some genuine reachable separator, must reach the exact
    behavioural quotient in at most |M| refinement stages.  The choice of separator
    is arbitrary: no greedy policy is assumed. -/
theorem finite_recovery
    (seq : Nat → Finset M)
    (progress : ∀ n, ¬ Terminal A obs (seq n) →
      RefineStep A obs (seq n) (seq (n + 1))) :
    ∃ n, n ≤ Fintype.card M ∧
      (∀ x y, EqBy A obs (seq n) x y ↔ BehEq A obs x y) := by
  by_contra hnone
  have hnoterm : ∀ n, n ≤ Fintype.card M → ¬ Terminal A obs (seq n) := by
    intro n hn hterm
    apply hnone
    refine ⟨n, hn, ?_⟩
    exact (terminal_exact A obs (seq n)).mp hterm
  have hgrow : ∀ n, n ≤ Fintype.card M + 1 → n ≤ (seq n).card := by
    intro n hn
    induction n with
    | zero => exact Nat.zero_le _
    | succ n ih =>
        have hncard : n ≤ Fintype.card M := by omega
        have hstep := progress n (hnoterm n hncard)
        have hcard := refineStep_card A obs hstep
        have ih' : n ≤ (seq n).card := ih (by omega)
        omega
  have hlower : Fintype.card M + 1 ≤ (seq (Fintype.card M + 1)).card :=
    hgrow (Fintype.card M + 1) (by omega)
  have hupper : (seq (Fintype.card M + 1)).card ≤ Fintype.card M := by
    simpa using Finset.card_le_card (Finset.subset_univ (seq (Fintype.card M + 1)))
  omega

end FiniteRecovery

end BehaviouralCongruence
