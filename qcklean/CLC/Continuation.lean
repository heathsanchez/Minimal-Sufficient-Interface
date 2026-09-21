import CLC.Transport

namespace CLC

universe u v

def ContinuationSafe {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A : Form.{v}) (x y : A.State) : Prop :=
  ∀ (B : Form.{v}) (a : VerifiedTransport Ωauth A B) (p : Protected B),
    B.eval (a.mapState x) p.1 = B.eval (a.mapState y) p.1

theorem continuationSafe_refl {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A : Form.{v}} {x : A.State} :
    ContinuationSafe Ωauth A x x := by
  intro B a p
  rfl

theorem continuationSafe_symm {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A : Form.{v}} {x y : A.State}
    (h : ContinuationSafe Ωauth A x y) :
    ContinuationSafe Ωauth A y x := by
  intro B a p
  exact (h B a p).symm

theorem continuationSafe_trans {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A : Form.{v}} {x y z : A.State}
    (hxy : ContinuationSafe Ωauth A x y)
    (hyz : ContinuationSafe Ωauth A y z) :
    ContinuationSafe Ωauth A x z := by
  intro B a p
  exact (hxy B a p).trans (hyz B a p)

def continuationSafeSetoid {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A : Form.{v}) : Setoid A.State where
  r := ContinuationSafe Ωauth A
  iseqv := by
    constructor
    · intro x
      exact continuationSafe_refl
    · intro x y h
      exact continuationSafe_symm h
    · intro x y z hxy hyz
      exact continuationSafe_trans hxy hyz

theorem continuationSafe_map {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B : Form.{v}} {x y : A.State}
    (a : VerifiedTransport Ωauth A B)
    (hxy : ContinuationSafe Ωauth A x y) :
    ContinuationSafe Ωauth B (a.mapState x) (a.mapState y) := by
  intro C b p
  exact hxy C (a.comp b) p

abbrev ProtectedBehavior {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A : Form.{v}) :=
  Quotient (continuationSafeSetoid Ωauth A)

def observeProtected {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A : Form.{v}) (p : Protected A) :
    ProtectedBehavior Ωauth A → Verdict :=
  Quotient.lift (fun x => A.eval x p.1) (by
    intro x y hxy
    exact hxy A (VerifiedTransport.id Ωauth A) p)

def behaviorMap {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B : Form.{v}}
    (a : VerifiedTransport Ωauth A B) :
    ProtectedBehavior Ωauth A → ProtectedBehavior Ωauth B :=
  Quotient.map a.mapState (by
    intro x y hxy
    exact continuationSafe_map a hxy)

theorem behaviorMap_naturality {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B : Form.{v}}
    (a : VerifiedTransport Ωauth A B) (x : A.State) :
    behaviorMap a (Quotient.mk (continuationSafeSetoid Ωauth A) x) =
      Quotient.mk (continuationSafeSetoid Ωauth B) (a.mapState x) := by
  rfl

end CLC
