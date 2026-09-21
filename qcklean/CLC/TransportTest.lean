import CLC.Transport

open CLC

#check Form
#check Protected
#check AuthoritySnapshot
#check TransportData
#check VerifiedTransport
#check VerifiedTransport.id
#check VerifiedTransport.comp
#check TransportEq
#check transport_comp_assoc
#check transport_id_left
#check transport_id_right
#check decisive_preserved
#check Strict
#check Strict.toDevelopmental

namespace CLC.TransportTest

def sourceForm : Form where
  State := Bool
  Test := Bool
  stateFinite := inferInstance
  testFinite := inferInstance
  decState := inferInstance
  decTest := inferInstance
  «protected» := fun _ => true
  eval := fun _ _ => .unknown

def targetForm : Form where
  State := Bool
  Test := Bool
  stateFinite := inferInstance
  testFinite := inferInstance
  decState := inferInstance
  decTest := inferInstance
  «protected» := fun _ => true
  eval := fun x _ => if x then .eq else .unknown

def equalityForm : Form where
  State := Bool
  Test := Bool
  stateFinite := inferInstance
  testFinite := inferInstance
  decState := inferInstance
  decTest := inferInstance
  «protected» := fun _ => true
  eval := fun x d => if x = d then .eq else .dist

def authority : AuthoritySnapshot Unit where
  accepts := fun _ => true
  live := fun _ => true
  idCert := ()
  compCert := fun _ _ => ()
  accepts_id := rfl
  live_id := rfl
  accepts_comp := by simp
  live_comp := by simp
  certEq := Eq
  certEq_refl := by simp
  certEq_symm := by intro _ _ h; exact h.symm
  certEq_trans := by intro _ _ _ h₁ h₂; exact h₁.trans h₂
  accepts_congr := by intro _ _ h; cases h; rfl
  live_congr := by intro _ _ h; cases h; rfl
  comp_congr := by simp
  comp_assoc := by simp
  id_left := by simp
  id_right := by simp

def developmental : VerifiedTransport authority sourceForm targetForm where
  mapState := id
  pullTest := id
  pullProtected := by intro d hd; rfl
  liftProtected := fun p => ⟨p.1, by simp [targetForm]⟩
  refine := by intro x d; exact unknown_le _
  split := by intro p; rfl
  cert := ()
  checked := rfl
  liveAt := rfl

example : ¬ Decisive (sourceForm.eval false false) := by
  simp [sourceForm, Decisive]

example :
    targetForm.eval
        ((VerifiedTransport.id authority targetForm).mapState true)
        ((VerifiedTransport.id authority targetForm).liftProtected
          ⟨true, by rfl⟩).1 =
      targetForm.eval true true := by
  exact decisive_preserved (VerifiedTransport.id authority targetForm) true
    ⟨true, by rfl⟩ (by simp [targetForm, Decisive])

example : TransportEq
    ((developmental.comp (VerifiedTransport.id authority targetForm)).comp
      (VerifiedTransport.id authority targetForm))
    (developmental.comp
      ((VerifiedTransport.id authority targetForm).comp
        (VerifiedTransport.id authority targetForm))) :=
  transport_comp_assoc developmental
    (VerifiedTransport.id authority targetForm)
    (VerifiedTransport.id authority targetForm)

structure TransportCandidate (A B : Form) where
  mapState : A.State → B.State
  pullTest : B.Test → A.Test

def finiteRefines (a : TransportCandidate equalityForm equalityForm) : Bool :=
  decide (∀ x d, equalityForm.eval x (a.pullTest d) ≤
    equalityForm.eval (a.mapState x) d)

def wrongPullback : TransportCandidate equalityForm equalityForm where
  mapState := id
  pullTest := not

example : finiteRefines wrongPullback = false := by native_decide

example : Strict (VerifiedTransport.id authority equalityForm).toTransportData := by
  intro x d
  rfl

example :
    equalityForm.eval true
        ((VerifiedTransport.id authority equalityForm).pullTest true) ≤
      equalityForm.eval
        ((VerifiedTransport.id authority equalityForm).mapState true) true := by
  exact Strict.toDevelopmental
    (a := (VerifiedTransport.id authority equalityForm).toTransportData)
    (by intro x d; rfl) true true

end CLC.TransportTest
