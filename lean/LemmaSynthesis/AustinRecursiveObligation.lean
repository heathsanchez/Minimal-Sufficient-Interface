import Std

/-!
# Austin recursive-obligation test

This file tests a concrete claim suggested by the Order-5 residual work:
source-law structure can force a new recursive proof/model constructor, rather
than merely requiring more search in a fixed term grammar.

We formalize two reported source laws directly as binary operations.  The key
results are:

* E40909 forces left cancellation.
* E40909 therefore carries an explicit injective encoder `G × G ↪ G`.
* Any already-required branch `A ⋄ p = q` is promoted by E40909 to the next
  branch `((((q ⋄ A) ⋄ A) ⋄ z) ⋄ A) = p`.
* E11116 has the analogous promotion property: from `A ⋄ p = q` it forces
  `y ⋄ ((p ⋄ q) ⋄ (y ⋄ y)) = p`.
* On the free binary-term syntax, both promotion operators generate an
  unbounded lineage: a measured coordinate strictly grows at every step.
* The syntactic lineages are sound in every model of the corresponding law.

Thus the source laws themselves compile a recursive closure obligation.  This
is stronger than the statement that a bounded search happened to fail, but is
still deliberately short of a full normal-form/confluence model construction.
-/

namespace AustinRecursiveObligation

abbrev BinOp (G : Type) := G → G → G

/-- E40909: `((((y⋄x)⋄y)⋄y)⋄z)⋄y = x`. -/
def Law40909 {G : Type} (op : BinOp G) : Prop :=
  ∀ x y z : G, op (op (op (op (op y x) y) y) z) y = x

/-- E11116: `y⋄((x⋄(z⋄x))⋄(y⋄y)) = x`. -/
def Law11116 {G : Type} (op : BinOp G) : Prop :=
  ∀ x y z : G, op y (op (op x (op z x)) (op y y)) = x

/-- E40909 makes every left translation injective. -/
theorem law40909_left_cancel {G : Type} (op : BinOp G)
    (hLaw : Law40909 op) (y a b : G) (h : op y a = op y b) : a = b := by
  have hctx := congrArg (fun t => op (op (op (op t y) y) y) y) h
  exact (hLaw a y y).symm.trans (hctx.trans (hLaw b y y))

/-- The law itself is a decoder for the first coordinate of this encoding. -/
def phi40909 {G : Type} (op : BinOp G) (y : G) : G × G → G :=
  fun p => op (op (op (op y p.1) y) y) p.2

theorem phi40909_decode {G : Type} (op : BinOp G)
    (hLaw : Law40909 op) (y : G) (p : G × G) :
    op (phi40909 op y p) y = p.1 := by
  exact hLaw p.1 y p.2

/-- E40909 therefore injects two coordinates into one carrier element. -/
theorem phi40909_injective {G : Type} (op : BinOp G)
    (hLaw : Law40909 op) (y : G) : Function.Injective (phi40909 op y) := by
  intro a b h
  rcases a with ⟨x, z⟩
  rcases b with ⟨x', z'⟩
  have hx : x = x' := by
    calc
      x = op (phi40909 op y (x, z)) y := (phi40909_decode op hLaw y (x, z)).symm
      _ = op (phi40909 op y (x', z')) y := congrArg (fun t => op t y) h
      _ = x' := phi40909_decode op hLaw y (x', z')
  subst x'
  have hz : z = z' := by
    apply law40909_left_cancel op hLaw (op (op (op y x) y) y)
    simpa [phi40909] using h
  exact Prod.ext rfl hz

/-- Every right translation is surjective; the encoder gives an explicit preimage. -/
theorem law40909_right_surjective {G : Type} (op : BinOp G)
    (hLaw : Law40909 op) (y : G) : Function.Surjective (fun t => op t y) := by
  intro x
  exact ⟨phi40909 op y (x, y), phi40909_decode op hLaw y (x, y)⟩

/--
A branch already demanded by rewriting is not isolated under E40909.
If `A ⋄ p = q`, the source law forces the promoted branch
`((((q ⋄ A) ⋄ A) ⋄ z) ⋄ A) = p` for every `z`.
-/
theorem law40909_promotes_branch {G : Type} (op : BinOp G)
    (hLaw : Law40909 op) {A p q : G} (hBranch : op A p = q) (z : G) :
    op (op (op (op q A) A) z) A = p := by
  simpa [hBranch] using hLaw p A z

/--
E11116 closes a branch recursively too.  Feeding `A ⋄ p = q` into the inner
`z ⋄ x` occurrence yields the next branch with a fresh/free parameter `y`.
-/
theorem law11116_promotes_branch {G : Type} (op : BinOp G)
    (hLaw : Law11116 op) {A p q : G} (hBranch : op A p = q) (y : G) :
    op y (op (op p q) (op y y)) = p := by
  simpa [hBranch] using hLaw p y A

/-- A packaged interface: the E40909 law itself supplies decoder and promotion. -/
structure E40909DevelopmentInterface {G : Type} (op : BinOp G) where
  leftCancel : ∀ y a b, op y a = op y b → a = b
  rightSurjective : ∀ y, Function.Surjective (fun t => op t y)
  encode : G → G × G → G
  decode : ∀ y p, op (encode y p) y = p.1
  encodeInjective : ∀ y, Function.Injective (encode y)
  promote : ∀ {A p q}, op A p = q → ∀ z, op (op (op (op q A) A) z) A = p

/-- The interface is not guessed: it compiles directly from E40909. -/
def compileE40909Interface {G : Type} (op : BinOp G) (hLaw : Law40909 op) :
    E40909DevelopmentInterface op where
  leftCancel := law40909_left_cancel op hLaw
  rightSurjective := law40909_right_surjective op hLaw
  encode := phi40909 op
  decode := phi40909_decode op hLaw
  encodeInjective := phi40909_injective op hLaw
  promote := fun h z => law40909_promotes_branch op hLaw h z

/-! ## Syntactic recursive closure -/

/-- Free binary terms; variables are only labels, so this layer assumes no model. -/
inductive FTerm where
  | var : Nat → FTerm
  | app : FTerm → FTerm → FTerm
  deriving DecidableEq, Repr

namespace FTerm

def size : FTerm → Nat
  | .var _ => 1
  | .app a b => size a + size b + 1

end FTerm

/-- A directed root branch `left ⋄ right → out`. -/
structure Branch where
  left : FTerm
  right : FTerm
  out : FTerm
  deriving DecidableEq, Repr

/-- Syntactic E40909 promotion, read directly from `law40909_promotes_branch`. -/
def promote40909 (b : Branch) (z : FTerm) : Branch :=
  { left := .app (.app (.app b.out b.left) b.left) z
    right := b.left
    out := b.right }

/-- Syntactic E11116 promotion, read directly from `law11116_promotes_branch`. -/
def promote11116 (b : Branch) (y : FTerm) : Branch :=
  { left := y
    right := .app (.app b.right b.out) (.app y y)
    out := b.right }

/-- E40909 promotion strictly grows the branch's left coordinate. -/
theorem promote40909_left_grows (b : Branch) (z : FTerm) :
    b.left.size < (promote40909 b z).left.size := by
  simp [promote40909, FTerm.size]
  omega

/-- E11116 promotion strictly grows the branch's right coordinate. -/
theorem promote11116_right_grows (b : Branch) (y : FTerm) :
    b.right.size < (promote11116 b y).right.size := by
  simp [promote11116, FTerm.size]
  omega

/-- Iterate E40909 promotion along an arbitrary stream of parameters. -/
def iter40909 (zs : Nat → FTerm) : Nat → Branch → Branch
  | 0, b => b
  | n + 1, b => promote40909 (iter40909 zs n b) (zs n)

/-- Iterate E11116 promotion along an arbitrary stream of parameters. -/
def iter11116 (ys : Nat → FTerm) : Nat → Branch → Branch
  | 0, b => b
  | n + 1, b => promote11116 (iter11116 ys n b) (ys n)

/-- Every E40909 generation is syntactically new from its predecessor. -/
theorem iter40909_step_ne (zs : Nat → FTerm) (n : Nat) (b : Branch) :
    iter40909 zs (n + 1) b ≠ iter40909 zs n b := by
  intro h
  have hs := promote40909_left_grows (iter40909 zs n b) (zs n)
  rw [show iter40909 zs (n + 1) b = promote40909 (iter40909 zs n b) (zs n) by rfl] at h
  have hleft := congrArg Branch.left h
  rw [hleft] at hs
  exact (Nat.lt_irrefl _ hs)

/-- Every E11116 generation is syntactically new from its predecessor. -/
theorem iter11116_step_ne (ys : Nat → FTerm) (n : Nat) (b : Branch) :
    iter11116 ys (n + 1) b ≠ iter11116 ys n b := by
  intro h
  have hs := promote11116_right_grows (iter11116 ys n b) (ys n)
  rw [show iter11116 ys (n + 1) b = promote11116 (iter11116 ys n b) (ys n) by rfl] at h
  have hright := congrArg Branch.right h
  rw [hright] at hs
  exact (Nat.lt_irrefl _ hs)

/-- Evaluate a free term in a concrete magma. -/
def eval {G : Type} (op : BinOp G) (env : Nat → G) : FTerm → G
  | .var n => env n
  | .app a b => op (eval op env a) (eval op env b)

/-- A syntactic branch is valid in a concrete magma under an environment. -/
def Branch.Holds {G : Type} (op : BinOp G) (env : Nat → G) (b : Branch) : Prop :=
  op (eval op env b.left) (eval op env b.right) = eval op env b.out

/-- Syntactic E40909 promotion is semantically sound in every E40909 model. -/
theorem promote40909_sound {G : Type} (op : BinOp G) (env : Nat → G)
    (hLaw : Law40909 op) (b : Branch) (hb : b.Holds op env) (z : FTerm) :
    (promote40909 b z).Holds op env := by
  exact law40909_promotes_branch op hLaw hb (eval op env z)

/-- Syntactic E11116 promotion is semantically sound in every E11116 model. -/
theorem promote11116_sound {G : Type} (op : BinOp G) (env : Nat → G)
    (hLaw : Law11116 op) (b : Branch) (hb : b.Holds op env) (y : FTerm) :
    (promote11116 b y).Holds op env := by
  exact law11116_promotes_branch op hLaw hb (eval op env y)

/-- All recursively generated E40909 obligations are valid once the seed is. -/
theorem iter40909_sound {G : Type} (op : BinOp G) (env : Nat → G)
    (hLaw : Law40909 op) (zs : Nat → FTerm) (b : Branch) (hb : b.Holds op env) :
    ∀ n, (iter40909 zs n b).Holds op env := by
  intro n
  induction n with
  | zero => exact hb
  | succ n ih =>
      exact promote40909_sound op env hLaw (iter40909 zs n b) ih (zs n)

/-- All recursively generated E11116 obligations are valid once the seed is. -/
theorem iter11116_sound {G : Type} (op : BinOp G) (env : Nat → G)
    (hLaw : Law11116 op) (ys : Nat → FTerm) (b : Branch) (hb : b.Holds op env) :
    ∀ n, (iter11116 ys n b).Holds op env := by
  intro n
  induction n with
  | zero => exact hb
  | succ n ih =>
      exact promote11116_sound op env hLaw (iter11116 ys n b) ih (ys n)

end AustinRecursiveObligation
