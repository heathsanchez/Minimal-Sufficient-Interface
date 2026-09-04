import Std

/-! # Verified developmental chain — 3 generations, mechanism-driven

  The breakthrough experiment: can one verifier-certified representational repair
  change the reachable world so the SAME mechanism discovers the next previously
  unavailable residual, derives the next minimal extension, and continues?

  Micro-world: objects are `Fin 8` (3-bit vectors).  The repair candidate space is
  a FIXED list of three feature indices (bits 0,1,2); the ontology is a list of
  admitted feature indices.  The mechanism is:

    findResidual : search all ordered pairs in canonical order, return the first
                   pair that the ontology collapses but that is distinct;
    findRepair   : search the candidate features in canonical order, return the
                   first (minimal) feature that separates the pair;
    update       : admit the accepted feature (MinRepair = add one feature);
    step         : residual → repair → next ontology;
    runSteps     : iterate.

  Nothing is hand-declared: which residual is found and which feature is admitted
  at each generation are OUTPUTS of the search, and the next ontology is built by
  `update` from the accepted repair.  The ablation then proves each repair is what
  makes the next residual reachable under the same search policy.
-/

namespace DevelopmentalChain

abbrev Obj := Fin 8

/- Bit i of the object's numeric value (the repair candidate features). -/
def featureAt (i : Fin 3) (x : Obj) : Bool :=
  decide ((x.val / (2 ^ i.val)) % 2 = 0)

def bit0 : Fin 3 := ⟨0, by decide⟩
def bit1 : Fin 3 := ⟨1, by decide⟩
def bit2 : Fin 3 := ⟨2, by decide⟩

/- The FIXED repair candidate space (all three bit indices, canonical order). -/
def candidateIndices : List (Fin 3) := [bit0, bit1, bit2]

/- An ontology is a list of admitted feature indices. -/
abbrev Ontology := List (Fin 3)

/- The ontology collapses x,y iff every admitted feature agrees on them. -/
def collapsedBy (ont : Ontology) (x y : Obj) : Bool :=
  ont.all (fun i => featureAt i x == featureAt i y)

/- All objects and all ordered pairs, canonical order. -/
def allObjects : List Obj := List.finRange 8

def allPairs : List (Obj × Obj) :=
  allObjects.flatMap (fun x => allObjects.map (fun y => (x, y)))

/- RESIDUAL SEARCH: first pair collapsed by the ontology yet distinct. -/
def findResidual (ont : Ontology) : Option (Obj × Obj) :=
  allPairs.find? (fun xy => collapsedBy ont xy.1 xy.2 && (xy.1 != xy.2))

/- REPAIR SEARCH: first (minimal) feature separating the pair. -/
def findRepair (xy : Obj × Obj) : Option (Fin 3) :=
  candidateIndices.find? (fun i => featureAt i xy.1 != featureAt i xy.2)

/- MINIMAL REPAIR / REBUILD: admit the accepted feature. -/
def update (ont : Ontology) (i : Fin 3) : Ontology :=
  ont ++ [i]

/- One generation: residual → minimal repair → next ontology. -/
def step (ont : Ontology) : Option (Obj × Obj × Fin 3) :=
  match findResidual ont with
  | none => none
  | some xy =>
    match findRepair xy with
    | none => none
    | some i => some (xy.1, xy.2, i)

/- Run n generations, collecting (p, q, admitted feature) triples. -/
def runSteps (n : Nat) (ont : Ontology) : List (Obj × Obj × Fin 3) :=
  match n with
  | 0 => []
  | k + 1 =>
    match step ont with
    | none => []
    | some (x, y, i) => (x, y, i) :: runSteps k (update ont i)

/- Named objects (canonical). -/
def o0 : Obj := ⟨0, by decide⟩
def o1 : Obj := ⟨1, by decide⟩
def o2 : Obj := ⟨2, by decide⟩
def o4 : Obj := ⟨4, by decide⟩

/- The ontologies produced by the mechanism. -/
def G0 : Ontology := []
def G1 : Ontology := [bit0]
def G2 : Ontology := [bit0, bit1]
def G3 : Ontology := [bit0, bit1, bit2]

/- The full 3-generation chain, discovered and certified. -/
#eval runSteps 3 G0

/- Generation 0: miner discovers (0,1); minimal repair is bit0; world rebuilds. -/
theorem residual0 : findResidual G0 = some (o0, o1) := by native_decide
theorem repair0 : findRepair (o0, o1) = some bit0 := by native_decide
theorem rebuild0 : update G0 bit0 = G1 := by native_decide

/- Generation 1: miner discovers (0,2); minimal repair is bit1. -/
theorem residual1 : findResidual G1 = some (o0, o2) := by native_decide
theorem repair1 : findRepair (o0, o2) = some bit1 := by native_decide
theorem rebuild1 : update G1 bit1 = G2 := by native_decide

/- Generation 2: miner discovers (0,4); minimal repair is bit2. -/
theorem residual2 : findResidual G2 = some (o0, o4) := by native_decide
theorem repair2 : findRepair (o0, o4) = some bit2 := by native_decide
theorem rebuild2 : update G2 bit2 = G3 := by native_decide

/- Termination: after three bits are admitted, no residual remains. -/
theorem terminates : findResidual G3 = none := by native_decide

/- ABLATION: without the previous repair, the next residual is NOT returned by the
   same search policy — each accepted repair is what makes the next residual
   reachable. -/
theorem ablation1 : findResidual G0 ≠ some (o0, o2) := by native_decide
theorem ablation2 : findResidual G1 ≠ some (o0, o4) := by native_decide

/- PROPAGATION: the accepted repair changes the discovered residual. -/
theorem propagation0 : findResidual G0 ≠ findResidual G1 := by
  rw [residual0, residual1]; native_decide
theorem propagation1 : findResidual G1 ≠ findResidual G2 := by
  rw [residual1, residual2]; native_decide

end DevelopmentalChain
