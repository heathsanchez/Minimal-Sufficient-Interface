import Std

/-! # Unified developmental step + the Boolean completeness boundary

  Two things, in order:
  1. *Unify* the developmental pieces into one transition `step` that performs
     `R → B → K → sufficiency → (genesis | no-genesis) → minimize → certified next worlds`,
     and a `runDevelopment` graph runner that threads the returned generators across generations.
  2. *Establish the Boolean completeness boundary* before any arity-genesis claim:
     (a) the single-application binary regime `θ(b,c)` cannot reach coordinate `a` (incomplete);
     (b) the nested binary regime (NAND alone) generates all 256 functions `Bool³ → Bool`
     (functionally complete).  Together they show the truth: single-application binary is a
     genuine obstruction, but *composition* already closes it — so no purely extensional
     Boolean residual can force a new Boolean constructor beyond composition.  That boundary is
     the verified reason to move to a richer ontology (contexts/operators).
-/

namespace UnifiedStep

structure Car3 where
  a : Bool
  b : Bool
  c : Bool
  deriving DecidableEq, Repr, Inhabited

def Residual := Car3 × Car3

def ρ0 : Residual := (⟨false, false, false⟩, ⟨false, true, false⟩)   -- differs in b
def ρ1 : Residual := (⟨false, false, false⟩, ⟨false, false, true⟩)   -- differs in c
def ρ3 : Residual := (⟨false, true, true⟩, ⟨false, false, true⟩)     -- conjunctive 1
def ρ4 : Residual := (⟨false, true, true⟩, ⟨false, true, false⟩)     -- conjunctive 2
def ρ2 : Residual := (⟨false, false, false⟩, ⟨true, false, false⟩)   -- differs in a

def RA : List Residual := [ρ0, ρ1]
def RB : List Residual := [ρ3, ρ4]
def RC : List Residual := [ρ2]          -- spans coordinate a (outside the binary (b,c) regime)

/- ── Constructor algebra ────────────────────────────────────────────────────── -/
structure BinOp where
  ff : Bool
  ft : Bool
  tf : Bool
  tt : Bool
  deriving DecidableEq, Repr, Inhabited

def BinOp.apply (θ : BinOp) (x y : Bool) : Bool :=
  match (x, y) with
  | (false, false) => θ.ff
  | (false, true) => θ.ft
  | (true, false) => θ.tf
  | (true, true) => θ.tt

def allBools : List Bool := [false, true]

def allBinOps : List BinOp :=
  allBools.flatMap (fun ff =>
    allBools.flatMap (fun ft =>
      allBools.flatMap (fun tf =>
        allBools.map (fun tt => ⟨ff, ft, tf, tt⟩))))

def orOp   : BinOp := ⟨false, true,  true,  true⟩
def xorOp  : BinOp := ⟨false, true,  true,  false⟩

def separatesVia (θ : BinOp) (Rs : List Residual) : Bool :=
  Rs.all (fun ρ => θ.apply ρ.1.b ρ.1.c != θ.apply ρ.2.b ρ.2.c)

def genSeparates (gen : List BinOp) (Rs : List Residual) : Bool :=
  gen.any (fun θ => separatesVia θ Rs)

def separatesAllObligs (gen : List BinOp) (obligs : List (List Residual)) : Bool :=
  obligs.all (fun Rs => genSeparates gen Rs)

def minimize (gen : List BinOp) (obligs : List (List Residual)) : List BinOp :=
  gen.filter (fun θ => ¬ separatesAllObligs (gen.filter (fun x => x ≠ θ)) obligs)

/- ── PART I: the unified developmental transition ───────────────────────────── -/
structure World where
  gen : List BinOp
  obligs : List (List Residual)

def initWorld : World := ⟨[], []⟩

/- One transition: basis → sufficiency → genesis-or-not → minimize → next worlds. -/
def step (w : World) (Rs : List Residual) : List World :=
  let newObligs := w.obligs ++ [Rs]
  if genSeparates w.gen Rs then
    [⟨minimize w.gen newObligs, newObligs⟩]
  else
    (allBinOps.filter (fun θ => separatesVia θ Rs)).map
      (fun θ => ⟨minimize (θ :: w.gen) newObligs, newObligs⟩)

def quotientWorlds (ws : List World) : List World :=
  ws.foldl (fun acc w => if acc.any (fun w' => w'.gen = w.gen) then acc else acc ++ [w]) []

/- Multi-generation graph runner: each generation uses the exact generators returned before. -/
def runDevelopment (ws : List World) (rss : List (List Residual)) : List World :=
  rss.foldl (fun ws Rs => quotientWorlds (ws.flatMap (fun w => step w Rs))) ws

/- ── PART I kernels: step correctness (executable, specific) ────────────────── -/
theorem step_RA_branches : (step initWorld RA).length = 4 := by native_decide
theorem step_RA_all_satisfy : (step initWorld RA).all (fun w => genSeparates w.gen RA) := by native_decide
theorem run_RA_RB_all_satisfy :
    (runDevelopment [initWorld] [RA, RB]).all (fun w => separatesAllObligs w.gen [RA, RB]) := by
  native_decide
theorem run_RA_RB_RC_empty : (runDevelopment [initWorld] [RA, RB, RC]).isEmpty := by native_decide

/- PART I executable demonstration: three generations, printing the branch graph. -/
#eval (runDevelopment [initWorld] [RA]).map (fun w => w.gen)
#eval (runDevelopment [initWorld] [RA, RB]).map (fun w => w.gen)
#eval (runDevelopment [initWorld] [RA, RB, RC]).map (fun w => w.gen)

/- ── PART II: the Boolean completeness boundary ─────────────────────────────── -/

/- (a) The single-application binary regime cannot reach coordinate `a`: no `θ(b,c)` separates a
   pair differing only in `a`. -/
theorem binary_regime_cannot_reach_a (θ : BinOp) :
    ¬ (θ.apply ρ2.1.b ρ2.1.c ≠ θ.apply ρ2.2.b ρ2.2.c) := by
  intro h
  exact h rfl

/- (b) Nested binary (NAND alone) is functionally complete: it generates all 256 Bool³→Bool
   functions.  Truth tables as 8-bit lists, closure as a fixpoint under NAND-of-pairs. -/
def tableOf (d : Car3 → Bool) : List Bool :=
  [d ⟨false,false,false⟩, d ⟨false,false,true⟩, d ⟨false,true,false⟩, d ⟨false,true,true⟩,
   d ⟨true,false,false⟩, d ⟨true,false,true⟩, d ⟨true,true,false⟩, d ⟨true,true,true⟩]

def atomTables : List (List Bool) :=
  [tableOf (fun x => x.a), tableOf (fun x => x.b), tableOf (fun x => x.c)]

def nandB (x y : Bool) : Bool := !(x && y)

def nandTable (t1 t2 : List Bool) : List Bool :=
  (t1.zip t2).map (fun p => nandB p.1 p.2)

def dedupTables (l : List (List Bool)) : List (List Bool) :=
  l.foldl (fun acc x => if acc.any (fun y => y = x) then acc else acc ++ [x]) []

def closureRound (ts : List (List Bool)) : List (List Bool) :=
  let pairs := ts.flatMap (fun t1 => ts.map (fun t2 => nandTable t1 t2))
  dedupTables (ts ++ pairs)

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n + 1 => iterate f n (f x)

def nandClosure (rounds : Nat) : List (List Bool) := iterate closureRound rounds atomTables

/- NAND alone generates all 256 functions: the nested binary regime is functionally complete. -/
theorem nand_functionally_complete : (nandClosure 6).length = 256 := by
  native_decide

#eval (nandClosure 6).length

end UnifiedStep
