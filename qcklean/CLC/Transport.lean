import CLC.Verdict
import Mathlib.Data.Fintype.Sigma

namespace CLC

universe u

structure Form where
  State : Type u
  Test : Type u
  stateFinite : Fintype State
  testFinite : Fintype Test
  decState : DecidableEq State
  decTest : DecidableEq Test
  «protected» : Test → Bool
  eval : State → Test → Verdict

attribute [instance] Form.stateFinite Form.testFinite Form.decState Form.decTest

def Protected (A : Form) := {d : A.Test // A.protected d = true}

structure AuthoritySnapshot (Cert : Type u) [DecidableEq Cert] where
  accepts : Cert → Bool
  live : Cert → Bool
  idCert : Cert
  compCert : Cert → Cert → Cert
  accepts_id : accepts idCert = true
  live_id : live idCert = true
  accepts_comp : ∀ {a b}, accepts a = true → accepts b = true →
    accepts (compCert a b) = true
  live_comp : ∀ {a b}, live a = true → live b = true →
    live (compCert a b) = true
  certEq : Cert → Cert → Prop
  certEq_refl : ∀ a, certEq a a
  certEq_symm : ∀ {a b}, certEq a b → certEq b a
  certEq_trans : ∀ {a b c}, certEq a b → certEq b c → certEq a c
  accepts_congr : ∀ {a b}, certEq a b → accepts a = accepts b
  live_congr : ∀ {a b}, certEq a b → live a = live b
  comp_congr : ∀ {a a' b b'}, certEq a a' → certEq b b' →
    certEq (compCert a b) (compCert a' b')
  comp_assoc : ∀ a b c,
    certEq (compCert (compCert a b) c) (compCert a (compCert b c))
  id_left : ∀ a, certEq (compCert idCert a) a
  id_right : ∀ a, certEq (compCert a idCert) a

structure TransportData (Cert : Type u) (A B : Form) where
  mapState : A.State → B.State
  pullTest : B.Test → A.Test
  pullProtected : ∀ d, B.protected d = true →
    A.protected (pullTest d) = true
  liftProtected : Protected A → Protected B
  refine : ∀ x d, A.eval x (pullTest d) ≤ B.eval (mapState x) d
  split : ∀ p, pullTest (liftProtected p).1 = p.1
  cert : Cert

structure VerifiedTransport {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A B : Form)
    extends TransportData Cert A B where
  checked : Ωauth.accepts cert = true
  liveAt : Ωauth.live cert = true

namespace VerifiedTransport

def id {Cert : Type u} [DecidableEq Cert]
    (Ωauth : AuthoritySnapshot Cert) (A : Form) :
    VerifiedTransport Ωauth A A where
  mapState := _root_.id
  pullTest := _root_.id
  pullProtected := by intro d h; exact h
  liftProtected := _root_.id
  refine := by intro x d; exact le_rfl
  split := by intro p; rfl
  cert := Ωauth.idCert
  checked := Ωauth.accepts_id
  liveAt := Ωauth.live_id

def comp {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B C : Form}
    (a : VerifiedTransport Ωauth A B) (b : VerifiedTransport Ωauth B C) :
    VerifiedTransport Ωauth A C where
  mapState := b.mapState ∘ a.mapState
  pullTest := a.pullTest ∘ b.pullTest
  pullProtected := by
    intro d hd
    exact a.pullProtected (b.pullTest d) (b.pullProtected d hd)
  liftProtected := fun p => b.liftProtected (a.liftProtected p)
  refine := by
    intro x d
    exact le_trans (a.refine x (b.pullTest d)) (b.refine (a.mapState x) d)
  split := by
    intro p
    change a.pullTest (b.pullTest (b.liftProtected (a.liftProtected p)).1) = p.1
    rw [b.split (a.liftProtected p), a.split p]
  cert := Ωauth.compCert a.cert b.cert
  checked := Ωauth.accepts_comp a.checked b.checked
  liveAt := Ωauth.live_comp a.liveAt b.liveAt

end VerifiedTransport

structure TransportEq {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B : Form}
    (a b : VerifiedTransport Ωauth A B) : Prop where
  mapState_eq : ∀ x, a.mapState x = b.mapState x
  pullTest_eq : ∀ d, a.pullTest d = b.pullTest d
  liftProtected_eq : ∀ p, (a.liftProtected p).1 = (b.liftProtected p).1
  certificate_semantic_eq : Ωauth.certEq a.cert b.cert

theorem transport_id_left {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B : Form}
    (a : VerifiedTransport Ωauth A B) :
    TransportEq ((VerifiedTransport.id Ωauth A).comp a) a where
  mapState_eq := by intro x; rfl
  pullTest_eq := by intro d; rfl
  liftProtected_eq := by intro p; rfl
  certificate_semantic_eq := Ωauth.id_left a.cert

theorem transport_id_right {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B : Form}
    (a : VerifiedTransport Ωauth A B) :
    TransportEq (a.comp (VerifiedTransport.id Ωauth B)) a where
  mapState_eq := by intro x; rfl
  pullTest_eq := by intro d; rfl
  liftProtected_eq := by intro p; rfl
  certificate_semantic_eq := Ωauth.id_right a.cert

theorem transport_comp_assoc {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B C D : Form}
    (a : VerifiedTransport Ωauth A B)
    (b : VerifiedTransport Ωauth B C)
    (c : VerifiedTransport Ωauth C D) :
    TransportEq ((a.comp b).comp c) (a.comp (b.comp c)) where
  mapState_eq := by intro x; rfl
  pullTest_eq := by intro d; rfl
  liftProtected_eq := by intro p; rfl
  certificate_semantic_eq := Ωauth.comp_assoc a.cert b.cert c.cert

def Strict {Cert : Type u} {A B : Form}
    (a : TransportData Cert A B) : Prop :=
  ∀ x d, A.eval x (a.pullTest d) = B.eval (a.mapState x) d

theorem Strict.toDevelopmental {Cert : Type u} {A B : Form}
    {a : TransportData Cert A B} (h : Strict a) :
    ∀ x d, A.eval x (a.pullTest d) ≤ B.eval (a.mapState x) d := by
  intro x d
  rw [h x d]

theorem decisive_preserved {Cert : Type u} [DecidableEq Cert]
    {Ωauth : AuthoritySnapshot Cert} {A B : Form}
    (a : VerifiedTransport Ωauth A B) (x : A.State) (p : Protected A)
    (h : Decisive (A.eval x p.1)) :
    B.eval (a.mapState x) (a.liftProtected p).1 = A.eval x p.1 := by
  have hrefine := a.refine x (a.liftProtected p).1
  rw [a.split p] at hrefine
  exact decisive_eq_of_le h hrefine

end CLC
