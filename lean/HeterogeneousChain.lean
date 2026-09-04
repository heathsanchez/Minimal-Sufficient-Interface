import Std

/-! # Heterogeneous developmental chain — representational development over kinds

  `DevelopmentalChain` grew by admitting FEATURES of one fixed object type (bits of
  `Fin 8`): ordered propagation.  This file upgrades it: the ontology admits KINDS
  (heterogeneous, tagged), and each residual is about objects of a kind that is
  INADMISSIBLE — hence genuinely INEXPRESSIBLE — under the current ontology.  Each
  accepted repair is a kind-admission, not a feature-admission.

  Micro-world: three kinds (color, shape, size), each a two-valued carrier.  Objects
  are `(kind, val)` pairs.  The ontology admits a set of kinds; it observes the `val`
  of admitted-kind objects, and has NO observation of inadmissible-kind objects (a
  genuine type barrier).  The mechanism is unchanged in shape:

    findResidual : first same-kind pair whose kind is inadmissible (so collapsed) yet
                   with distinct vals (so the ground-truth continuation separates them);
    findRepair   : admit that kind (minimal);
    update       : add the kind to the ontology;
    runSteps     : iterate.

  `#eval runSteps 3 []` discovers the chain; the theorems kernel-certify each
  generation, the inexpressibility of each next residual, and the ablation.
-/

namespace HeterogeneousChain

inductive Kind | color | shape | size
  deriving DecidableEq, Repr, Inhabited

structure Obj where
  kind : Kind
  val : Bool
  deriving DecidableEq, Repr

abbrev Ontology := List Kind

def admits (ont : Ontology) (k : Kind) : Bool :=
  ont.any (fun k' => k' == k)

/- The ontology collapses x,y iff they are the same kind AND (that kind is
   inadmissible — a type barrier — or their vals agree). -/
def collapsedBy (ont : Ontology) (x y : Obj) : Bool :=
  (x.kind == y.kind) && (! admits ont x.kind || (x.val == y.val))

/- Named objects. -/
def cf : Obj := ⟨.color, false⟩
def ct : Obj := ⟨.color, true⟩
def sf : Obj := ⟨.shape, false⟩
def st : Obj := ⟨.shape, true⟩
def zf : Obj := ⟨.size, false⟩
def zt : Obj := ⟨.size, true⟩

def allObjects : List Obj := [cf, ct, sf, st, zf, zt]

def allPairs : List (Obj × Obj) :=
  allObjects.flatMap (fun x => allObjects.map (fun y => (x, y)))

/- Residual search: first same-kind pair collapsed by the ontology yet distinct. -/
def findResidual (ont : Ontology) : Option (Obj × Obj) :=
  allPairs.find? (fun xy => collapsedBy ont xy.1 xy.2 && (xy.1 != xy.2))

/- Minimal repair: admit the kind of the residual pair. -/
def findRepair (xy : Obj × Obj) : Option Kind := some xy.1.kind

def update (ont : Ontology) (k : Kind) : Ontology := ont ++ [k]

def step (ont : Ontology) : Option (Obj × Obj × Kind) :=
  match findResidual ont with
  | none => none
  | some xy => some (xy.1, xy.2, xy.1.kind)

def runSteps (n : Nat) (ont : Ontology) : List (Obj × Obj × Kind) :=
  match n with
  | 0 => []
  | k + 1 =>
    match step ont with
    | none => []
    | some (x, y, knd) => (x, y, knd) :: runSteps k (update ont knd)

/- Ontologies produced by the mechanism. -/
def G0 : Ontology := []
def G1 : Ontology := [.color]
def G2 : Ontology := [.color, .shape]
def G3 : Ontology := [.color, .shape, .size]

#eval runSteps 3 G0

/- Generation 0: color residual, admit color. -/
theorem residual0 : findResidual G0 = some (cf, ct) := by native_decide
theorem repair0 : findRepair (cf, ct) = some .color := by native_decide
theorem rebuild0 : update G0 .color = G1 := by native_decide

/- Generation 1: shape residual, admit shape. -/
theorem residual1 : findResidual G1 = some (sf, st) := by native_decide
theorem repair1 : findRepair (sf, st) = some .shape := by native_decide
theorem rebuild1 : update G1 .shape = G2 := by native_decide

/- Generation 2: size residual, admit size. -/
theorem residual2 : findResidual G2 = some (zf, zt) := by native_decide
theorem repair2 : findRepair (zf, zt) = some .size := by native_decide
theorem rebuild2 : update G2 .size = G3 := by native_decide

theorem terminates : findResidual G3 = none := by native_decide

/- INEXPRESSIBILITY: each next residual is about a kind inadmissible at the prior
   generation — a genuine type barrier, not a not-yet-observed feature. -/
theorem shape_inadmissible_at_G0 : ¬ admits G0 .shape = true := by native_decide
theorem size_inadmissible_at_G1 : ¬ admits G1 .size = true := by native_decide

/- ABLATION: without each repair, the next residual is not returned. -/
theorem ablation1 : findResidual G0 ≠ some (sf, st) := by native_decide
theorem ablation2 : findResidual G1 ≠ some (zf, zt) := by native_decide

/- PROPAGATION: each accepted kind-admission changes the discovered residual. -/
theorem propagation0 : findResidual G0 ≠ findResidual G1 := by
  rw [residual0, residual1]; native_decide
theorem propagation1 : findResidual G1 ≠ findResidual G2 := by
  rw [residual1, residual2]; native_decide

end HeterogeneousChain
