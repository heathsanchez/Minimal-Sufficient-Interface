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
* E11116 has the analogous promotion property: an inner equality
  `z ⋄ x = q` forces the higher rule `y ⋄ ((x ⋄ q) ⋄ (y ⋄ y)) = x`.

The point is deliberately narrower than constructing the full infinite model:
these are kernel-checked obligations that any adequate recursive construction
must realize.
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
E11116 has the same higher-order shape: reducing the inner product changes the
outer source-law instance, so closure under the source law forces promotion.
-/
theorem law11116_promotes_inner_branch {G : Type} (op : BinOp G)
    (hLaw : Law11116 op) {z x q : G} (hBranch : op z x = q) (y : G) :
    op y (op (op x q) (op y y)) = x := by
  simpa [hBranch] using hLaw x y z

/-- A packaged interface: the E40909 law itself supplies both decoder and promotion. -/
structure E40909DevelopmentInterface {G : Type} (op : BinOp G) where
  leftCancel : ∀ y a b, op y a = op y b → a = b
  encode : G → G × G → G
  decode : ∀ y p, op (encode y p) y = p.1
  encodeInjective : ∀ y, Function.Injective (encode y)
  promote : ∀ {A p q}, op A p = q → ∀ z, op (op (op (op q A) A) z) A = p

/-- The interface is not guessed: it compiles directly from E40909. -/
def compileE40909Interface {G : Type} (op : BinOp G) (hLaw : Law40909 op) :
    E40909DevelopmentInterface op where
  leftCancel := law40909_left_cancel op hLaw
  encode := phi40909 op
  decode := phi40909_decode op hLaw
  encodeInjective := phi40909_injective op hLaw
  promote := fun h z => law40909_promotes_branch op hLaw h z

end AustinRecursiveObligation
