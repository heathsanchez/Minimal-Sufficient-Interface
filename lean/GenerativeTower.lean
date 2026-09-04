import Std

/-! # Nested generative tower — the domain is generated from the previous domain

  `HeterogeneousChain` admitted PARALLEL kinds (color/shape/size: independent enums).
  This file upgrades to a NESTED GENERATIVE tower: each level's domain is
  CONSTRUCTED from the previous one, so `X_{t+1}` cannot even be formed as an
  admissible object domain before `X_t` is admitted.

    X_0 = Bool
    X_1 = X_0 × X_0
    X_2 = X_1 × X_1
    X_3 = X_2 × X_2

  (Product is the tractable constructor; the canonical function-space tower
  `X_{n+1} = X_n → Bool` preserves the same nesting but explodes to 2^16 at level 3.)

  The mechanism is unchanged: findResidual → minimal repair (admit the level) →
  update → spin again.  The residual at generation t is a pair of distinct objects
  of level t+1, which is INADMISSIBLE — its domain `X_{t+1} = X_t × X_t` does not
  yet exist in the admitted ontology — so the residual is not formable over G_t,
  and the repair literally generates the domain in which the next discrepancy
  becomes possible.

  Search scope: CANDIDATE-BOUNDED.  The search space is two canonical witnesses per
  level (8 objects), not the exhaustive 278-object tower; exhaustiveness is claimed
  only over this candidate set.
-/

namespace GenerativeTower

abbrev X0 := Bool
abbrev X1 := X0 × X0
abbrev X2 := X1 × X1
abbrev X3 := X2 × X2

/- Objects: tagged union over the four generated domains. -/
inductive Obj where
  | l0 : X0 → Obj
  | l1 : X1 → Obj
  | l2 : X2 → Obj
  | l3 : X3 → Obj
  deriving DecidableEq, Repr

def levelOf : Obj → Nat
  | .l0 _ => 0
  | .l1 _ => 1
  | .l2 _ => 2
  | .l3 _ => 3

/- Ontology = max admitted level.  Level n is admissible iff n ≤ ont. -/
abbrev Ontology := Nat

def admits (ont : Ontology) (o : Obj) : Bool := decide (levelOf o ≤ ont)

/- Collapsed: same level AND (inadmissible level OR identical value).  A type
   barrier: the ontology has NO observation of inadmissible-level objects. -/
def collapsedBy (ont : Ontology) (x y : Obj) : Bool :=
  (levelOf x == levelOf y) && (! admits ont x || (x == y))

/- Canonical witness objects (two per level). -/
def z0 : Obj := .l0 false
def o0 : Obj := .l0 true
def z1 : Obj := .l1 (false, false)
def o1 : Obj := .l1 (true, true)
def z2 : Obj := .l2 ((false, false), (false, false))
def o2 : Obj := .l2 ((true, true), (true, true))
def z3 : Obj := .l3 (((false, false), (false, false)), ((false, false), (false, false)))
def o3 : Obj := .l3 (((true, true), (true, true)), ((true, true), (true, true)))

/- Candidate-bounded object set (explicit scope). -/
def allObjects : List Obj := [z0, o0, z1, o1, z2, o2, z3, o3]

def allPairs : List (Obj × Obj) :=
  allObjects.flatMap (fun x => allObjects.map (fun y => (x, y)))

/- Residual search: first pair collapsed by the ontology yet distinct. -/
def findResidual (ont : Ontology) : Option (Obj × Obj) :=
  allPairs.find? (fun xy => collapsedBy ont xy.1 xy.2 && (xy.1 != xy.2))

/- Minimal repair: admit the residual's level (the lowest inadmissible level). -/
def findRepair (xy : Obj × Obj) : Option Nat := some (levelOf xy.1)

def update (ont : Ontology) (n : Nat) : Ontology := Nat.max ont n

def step (ont : Ontology) : Option (Obj × Obj × Nat) :=
  match findResidual ont with
  | none => none
  | some xy => some (xy.1, xy.2, levelOf xy.1)

def runSteps (n : Nat) (ont : Ontology) : List (Obj × Obj × Nat) :=
  match n with
  | 0 => []
  | k + 1 =>
    match step ont with
    | none => []
    | some (x, y, lv) => (x, y, lv) :: runSteps k (update ont lv)

def G0 : Ontology := 0
def G1 : Ontology := 1
def G2 : Ontology := 2
def G3 : Ontology := 3

#eval runSteps 3 G0

/- THE NESTING: each domain is literally constructed from the previous one. -/
theorem X1_nested_in_X0 : X1 = (X0 × X0) := rfl
theorem X2_nested_in_X1 : X2 = (X1 × X1) := rfl
theorem X3_nested_in_X2 : X3 = (X2 × X2) := rfl

/- Generation 0: level-1 residual (X1 inadmissible), admit level 1. -/
theorem residual0 : findResidual G0 = some (z1, o1) := by native_decide
theorem repair0 : findRepair (z1, o1) = some 1 := by native_decide
theorem rebuild0 : update G0 1 = G1 := by native_decide

/- Generation 1: level-2 residual, admit level 2. -/
theorem residual1 : findResidual G1 = some (z2, o2) := by native_decide
theorem repair1 : findRepair (z2, o2) = some 2 := by native_decide
theorem rebuild1 : update G1 2 = G2 := by native_decide

/- Generation 2: level-3 residual, admit level 3. -/
theorem residual2 : findResidual G2 = some (z3, o3) := by native_decide
theorem repair2 : findRepair (z3, o3) = some 3 := by native_decide
theorem rebuild2 : update G2 3 = G3 := by native_decide

theorem terminates : findResidual G3 = none := by native_decide

/- INEXPRESSIBILITY: each next residual's domain is inadmissible at the prior
   generation — its type does not yet exist in the admitted ontology. -/
theorem level1_inadmissible_at_G0 : ¬ admits G0 z1 = true := by native_decide
theorem level2_inadmissible_at_G1 : ¬ admits G1 z2 = true := by native_decide
theorem level3_inadmissible_at_G2 : ¬ admits G2 z3 = true := by native_decide

/- ABLATION: without each repair, the next residual is not returned. -/
theorem ablation1 : findResidual G0 ≠ some (z2, o2) := by native_decide
theorem ablation2 : findResidual G1 ≠ some (z3, o3) := by native_decide

/- PROPAGATION: each accepted level-admission changes the discovered residual. -/
theorem propagation0 : findResidual G0 ≠ findResidual G1 := by
  rw [residual0, residual1]; native_decide
theorem propagation1 : findResidual G1 ≠ findResidual G2 := by
  rw [residual1, residual2]; native_decide

end GenerativeTower
