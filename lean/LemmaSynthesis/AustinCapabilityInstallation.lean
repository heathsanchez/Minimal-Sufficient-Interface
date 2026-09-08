import Std

namespace AustinCapabilityInstallation

theorem transport {G : Type} (C : G → G) {a b : G} (h : a = b) :
    C a = C b := congrArg C h

theorem sound_E40909 {G : Type} (op : G → G → G)
    (hLaw : ∀ x y z : G, (op (op (op (op (op y x) y) y) z) y) = x)
    {A p q : G} (hBranch : op A p = q) (z : G) :
    (op (op (op (op q A) A) z) A) = p := by
  have hctx : (op (op (op (op q A) A) z) A) = (op (op (op (op (op A p) A) A) z) A) :=
    transport (fun hole => (op (op (op (op hole A) A) z) A)) hBranch.symm
  exact hctx.trans (hLaw p A z)

theorem sound_E11116 {G : Type} (op : G → G → G)
    (hLaw : ∀ x y z : G, (op y (op (op x (op z x)) (op y y))) = x)
    {A p q : G} (hBranch : op A p = q) (y : G) :
    (op y (op (op p q) (op y y))) = p := by
  have hctx : (op y (op (op p q) (op y y))) = (op y (op (op p (op A p)) (op y y))) :=
    transport (fun hole => (op y (op (op p hole) (op y y)))) hBranch.symm
  exact hctx.trans (hLaw p y A)

end AustinCapabilityInstallation
