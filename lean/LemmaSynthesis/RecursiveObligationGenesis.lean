import Std

/-!
# Recursive obligation genesis from Austin-law consequences

This file tests a specific developmental claim:

A verifier-visible branch equality can force a new branch constructor that is not
present in a seed-only representation.  If the representation omits that promoted
branch, it is consequence-incomplete.  The same mechanism is tested on two
structurally different Order-5 source laws, E40909 and E11116.

This does NOT claim that the recursive closure is already a confluent rewrite
system or that it by itself constructs a nontrivial model.  It proves the earlier,
load-bearing step: the source law itself forces recursive closure obligations, and
those obligations iterate to arbitrary finite depth.
-/

namespace RecursiveObligationGenesis

class Magma (G : Type) where
  op : G → G → G

infixl:70 " ◇ " => Magma.op

/-- E40909: ((((y◇x)◇y)◇y)◇z)◇y = x. -/
def Law40909 (G : Type) [Magma G] : Prop :=
  ∀ x y z : G, (((((y ◇ x) ◇ y) ◇ y) ◇ z) ◇ y) = x

/-- E11116: y◇((x◇(z◇x))◇(y◇y)) = x. -/
def Law11116 (G : Type) [Magma G] : Prop :=
  ∀ x y z : G, y ◇ ((x ◇ (z ◇ x)) ◇ (y ◇ y)) = x

/-- A branch packages the oriented equality A◇p = q. -/
structure Branch (G : Type) where
  A : G
  p : G
  q : G

variable {G : Type} [Magma G]

def Holds (b : Branch G) : Prop := b.A ◇ b.p = b.q

/--
E40909 promotion.  From A◇p=q, the law forces
((((q◇A)◇A)◇z)◇A)=p.
Written again as A'◇p'=q', this is the next branch.
-/
def promote40909 (b : Branch G) (z : G) : Branch G :=
  { A := ((b.q ◇ b.A) ◇ b.A) ◇ z
    p := b.A
    q := b.p }

/--
E11116 promotion.  From z◇x=q, the law forces
  y◇((x◇q)◇(y◇y))=x,
which is itself another branch.
-/
def promote11116 (b : Branch G) (y : G) : Branch G :=
  { A := y
    p := (b.p ◇ b.q) ◇ (y ◇ y)
    q := b.p }

/-- E40909 semantically forces its recursive branch constructor. -/
theorem law40909_promotes
    (h : Law40909 G) (b : Branch G) (z : G) (hb : Holds b) :
    Holds (promote40909 b z) := by
  dsimp [Holds, promote40909]
  simpa [hb] using h b.p b.A z

/-- E11116 semantically forces its recursive branch constructor. -/
theorem law11116_promotes
    (h : Law11116 G) (b : Branch G) (y : G) (hb : Holds b) :
    Holds (promote11116 b y) := by
  dsimp [Holds, promote11116]
  simpa [hb] using h b.p y b.A

/-- Iterate E40909 promotion along an arbitrary stream of fresh parameters. -/
def iter40909 (b : Branch G) (zs : Nat → G) : Nat → Branch G
  | 0 => b
  | n + 1 => promote40909 (iter40909 b zs n) (zs n)

/-- Iterate E11116 promotion along an arbitrary stream of parameters. -/
def iter11116 (b : Branch G) (ys : Nat → G) : Nat → Branch G
  | 0 => b
  | n + 1 => promote11116 (iter11116 b ys n) (ys n)

/-- E40909 forces every finite stage of the recursively generated obligation chain. -/
theorem law40909_forces_all_finite_stages
    (h : Law40909 G) (b : Branch G) (zs : Nat → G) (hb : Holds b) :
    ∀ n : Nat, Holds (iter40909 b zs n) := by
  intro n
  induction n with
  | zero => exact hb
  | succ n ih =>
      exact law40909_promotes h (iter40909 b zs n) (zs n) ih

/-- E11116 forces every finite stage of its recursively generated obligation chain. -/
theorem law11116_forces_all_finite_stages
    (h : Law11116 G) (b : Branch G) (ys : Nat → G) (hb : Holds b) :
    ∀ n : Nat, Holds (iter11116 b ys n) := by
  intro n
  induction n with
  | zero => exact hb
  | succ n ih =>
      exact law11116_promotes h (iter11116 b ys n) (ys n) ih

/--
A representation is consequence-complete for branch equalities when it records
every branch equality that actually holds in the model under consideration.
This deliberately abstracts away implementation details of the representation.
-/
def ConsequenceComplete (R : Branch G → Prop) : Prop :=
  ∀ b : Branch G, Holds b → R b

/--
If an E40909-promoted branch is missing from the representation, that missing
consequence is a certificate that the representation is incomplete.
-/
theorem missing40909_promotion_refutes_completeness
    (h : Law40909 G) (R : Branch G → Prop) (b : Branch G) (z : G)
    (hb : Holds b) (hmiss : ¬ R (promote40909 b z)) :
    ¬ ConsequenceComplete R := by
  intro hcomplete
  exact hmiss (hcomplete (promote40909 b z) (law40909_promotes h b z hb))

/-- The same representation-level obstruction transfers to E11116. -/
theorem missing11116_promotion_refutes_completeness
    (h : Law11116 G) (R : Branch G → Prop) (b : Branch G) (y : G)
    (hb : Holds b) (hmiss : ¬ R (promote11116 b y)) :
    ¬ ConsequenceComplete R := by
  intro hcomplete
  exact hmiss (hcomplete (promote11116 b y) (law11116_promotes h b y hb))

/--
Stronger form: if any stage n of the forced E40909 chain is omitted, the
representation is consequence-incomplete.
-/
theorem missing40909_stage_refutes_completeness
    (h : Law40909 G) (R : Branch G → Prop) (b : Branch G) (zs : Nat → G)
    (hb : Holds b) (n : Nat) (hmiss : ¬ R (iter40909 b zs n)) :
    ¬ ConsequenceComplete R := by
  intro hcomplete
  exact hmiss (hcomplete (iter40909 b zs n)
    (law40909_forces_all_finite_stages h b zs hb n))

/-- Same arbitrary-depth incompleteness witness for E11116. -/
theorem missing11116_stage_refutes_completeness
    (h : Law11116 G) (R : Branch G → Prop) (b : Branch G) (ys : Nat → G)
    (hb : Holds b) (n : Nat) (hmiss : ¬ R (iter11116 b ys n)) :
    ¬ ConsequenceComplete R := by
  intro hcomplete
  exact hmiss (hcomplete (iter11116 b ys n)
    (law11116_forces_all_finite_stages h b ys hb n))

/-- A representation closed under the E40909 constructor. -/
def Closed40909 (R : Branch G → Prop) : Prop :=
  ∀ b z, R b → R (promote40909 b z)

/-- A representation closed under the E11116 constructor. -/
def Closed11116 (R : Branch G → Prop) : Prop :=
  ∀ b y, R b → R (promote11116 b y)

/--
Semantic consequence-completeness plus E40909-validity forces constructor
closure on every represented branch that actually holds.
-/
theorem complete_representation_is_40909_closed_on_holds
    (h : Law40909 G) (R : Branch G → Prop) (hc : ConsequenceComplete R) :
    ∀ b z, Holds b → R (promote40909 b z) := by
  intro b z hb
  exact hc _ (law40909_promotes h b z hb)

/-- Transfer of the same developmental pattern to E11116. -/
theorem complete_representation_is_11116_closed_on_holds
    (h : Law11116 G) (R : Branch G → Prop) (hc : ConsequenceComplete R) :
    ∀ b y, Holds b → R (promote11116 b y) := by
  intro b y hb
  exact hc _ (law11116_promotes h b y hb)

/--
Cross-law result: the reusable principle is not the concrete forest shape but
"verified branch consequence -> law-derived promotion constructor -> recursive
closure obligation".  Both laws instantiate that same interface.
-/
theorem cross_law_recursive_obligation_interface
    (h40909 : Law40909 G) (h11116 : Law11116 G)
    (b40909 b11116 : Branch G) (z y : G)
    (hb40909 : Holds b40909) (hb11116 : Holds b11116) :
    Holds (promote40909 b40909 z) ∧ Holds (promote11116 b11116 y) := by
  exact ⟨law40909_promotes h40909 b40909 z hb40909,
    law11116_promotes h11116 b11116 y hb11116⟩

end RecursiveObligationGenesis
