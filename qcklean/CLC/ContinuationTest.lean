import CLC.Continuation

open CLC

#check ContinuationSafe
#check continuationSafeSetoid
#check continuationSafe_refl
#check continuationSafe_symm
#check continuationSafe_trans
#check continuationSafe_map
#check ProtectedBehavior
#check observeProtected
#check behaviorMap
#check behaviorMap_naturality

namespace CLC.ContinuationTest

def form : Form where
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

example (x : form.State) : ContinuationSafe authority form x x :=
  continuationSafe_refl

example {x y : form.State} (h : ContinuationSafe authority form x y) :
    ContinuationSafe authority form y x :=
  continuationSafe_symm h

example {x y z : form.State}
    (hxy : ContinuationSafe authority form x y)
    (hyz : ContinuationSafe authority form y z) :
    ContinuationSafe authority form x z :=
  continuationSafe_trans hxy hyz

example {x y : form.State} (h : ContinuationSafe authority form x y) :
    ContinuationSafe authority form
      ((VerifiedTransport.id authority form).mapState x)
      ((VerifiedTransport.id authority form).mapState y) :=
  continuationSafe_map (VerifiedTransport.id authority form) h

example (x : form.State) :
    behaviorMap (VerifiedTransport.id authority form)
        (Quotient.mk (continuationSafeSetoid authority form) x) =
      Quotient.mk (continuationSafeSetoid authority form)
        ((VerifiedTransport.id authority form).mapState x) :=
  behaviorMap_naturality (a := VerifiedTransport.id authority form) x

end CLC.ContinuationTest
