import Std

/-! # Full-language self-hosting — branching, reconvergence, generator-level MSI

  `SelfHosting` threaded the generator *arity* through the world.  This file lifts the world's
  generator from an arity bound to the **actual constructor algebra** (a finite set of binary
  truth tables), and makes the developmental step *branch* over minimal generator extensions,
  *reconverge* when branches become semantically equivalent, and *contract* when a constructor
  becomes redundant over the retained obligations.

  Key structure of the demonstration:
  - Residual family `RA` forces disjunctive constructors `{xor,or,nor,xnor}`.
  - Residual family `RB` forces conjunctive constructors `{and,xor,xnor,nand}`.
  - `RA` and `RB` span the *same* basis `{b,c}` (same arity), so an arity-only world cannot tell
    them apart — but a full-language world can (the **strong control**).
  - Branch `{or}` fails `RB` (needs genesis); branch `{xor}` already suffices.
  - In `{or,xor}`, `xor` subsumes `or` over `{RA,RB}`, so the minimizer *deletes* `or` — the
    `{or}` branch reconverges to `{xor}`.
-/

namespace FullLangSelfHosting

structure Car3 where
  a : Bool
  b : Bool
  c : Bool
  deriving DecidableEq, Repr, Inhabited

def Residual := Car3 × Car3

def ρ0 : Residual := (⟨false, false, false⟩, ⟨false, true, false⟩)   -- differs in b
def ρ1 : Residual := (⟨false, false, false⟩, ⟨false, false, true⟩)   -- differs in c
def ρ3 : Residual := (⟨false, true, true⟩, ⟨false, false, true⟩)     -- conjunctive pair 1
def ρ4 : Residual := (⟨false, true, true⟩, ⟨false, true, false⟩)     -- conjunctive pair 2

def RA : List Residual := [ρ0, ρ1]
def RB : List Residual := [ρ3, ρ4]

/- The constructor algebra: a binary Boolean operator as a decidable truth table. -/
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
def andOp  : BinOp := ⟨false, false, false, true⟩
def xorOp  : BinOp := ⟨false, true,  true,  false⟩
def norOp  : BinOp := ⟨true,  false, false, false⟩
def xnorOp : BinOp := ⟨true,  false, false, true⟩

/- A distinction `θ(b,c)` separates a residual family iff every pair is split. -/
def separatesVia (θ : BinOp) (Rs : List Residual) : Bool :=
  Rs.all (fun ρ => θ.apply ρ.1.b ρ.1.c != θ.apply ρ.2.b ρ.2.c)

/- The closure test: does the generator (a set of constructors) separate the family? -/
def genSeparates (gen : List BinOp) (Rs : List Residual) : Bool :=
  gen.any (fun θ => separatesVia θ Rs)

def separatesAllObligs (gen : List BinOp) (obligs : List (List Residual)) : Bool :=
  obligs.all (fun Rs => genSeparates gen Rs)

/- Generator-level minimal sufficiency: keep only constructors whose deletion breaks some
   retained obligation. -/
def minimize (gen : List BinOp) (obligs : List (List Residual)) : List BinOp :=
  gen.filter (fun θ => ¬ separatesAllObligs (gen.filter (fun x => x ≠ θ)) obligs)

/- The version space of minimal generator extensions (from the empty generator) for a family. -/
def genesisVersionSpace (Rs : List Residual) : List (List BinOp) :=
  (allBinOps.filter (fun θ => separatesVia θ Rs)).map (fun θ => [θ])

/- The world carries its full constructor algebra. -/
structure World where
  gen : List BinOp
  deriving DecidableEq, Repr, Inhabited

def initWorld : World := ⟨[]⟩

/- ── Kernels ───────────────────────────────────────────────────────────────── -/

/- The two residual families force four minimal branches each. -/
theorem four_RA_branches : (genesisVersionSpace RA).length = 4 := by native_decide
theorem four_RB_branches : (genesisVersionSpace RB).length = 4 := by native_decide

theorem or_branch_in_RA : [orOp] ∈ genesisVersionSpace RA := by native_decide
theorem xor_branch_in_RA : [xorOp] ∈ genesisVersionSpace RA := by native_decide
theorem and_not_in_RA : [andOp] ∉ genesisVersionSpace RA := by native_decide
theorem and_branch_in_RB : [andOp] ∈ genesisVersionSpace RB := by native_decide
theorem or_not_in_RB : [orOp] ∉ genesisVersionSpace RB := by native_decide

/- STRONG CONTROL: `or` and `and` have the same arity (both binary), yet RA is generable under
   `{or}` but not `{and}`, and RB under `{and}` but not `{or}`.  Full-language state carries
   information genuinely absent from an arity bound. -/
theorem same_arity_different_language :
    genSeparates [orOp] RA = true ∧ genSeparates [andOp] RA = false ∧
    genSeparates [andOp] RB = true ∧ genSeparates [orOp] RB = false := by
  native_decide

/- The two version spaces differ, even though RA and RB span the same basis. -/
theorem version_spaces_differ : genesisVersionSpace RA ≠ genesisVersionSpace RB := by
  native_decide

/- Branch divergence: `{or}` needs genesis for RB, `{xor}` already suffices. -/
theorem or_branch_needs_genesis : genSeparates [orOp] RB = false := by native_decide
theorem xor_branch_no_genesis : genSeparates [xorOp] RB = true := by native_decide

/- REDUNDANCY + DELETION: over the retained obligations {RA, RB}, `xor` subsumes `or`, so the
   minimizer deletes `or`. -/
theorem xor_subsumes_or : minimize [orOp, xorOp] [RA, RB] = [xorOp] := by native_decide
theorem deletion_preserves : separatesAllObligs [xorOp] [RA, RB] = true := by native_decide

/- RECONVERGENCE: the `{or}` branch, after acquiring a constructor to satisfy RB, minimizes back
   to `{xor}` — reconverging with the branch that already existed. -/
theorem reconvergence : minimize [orOp, xorOp] [RA, RB] = [xorOp] := by native_decide

/- NEGATIVE CONTROL: a generator that already separates the family is not enlarged. -/
theorem no_genesis_when_sufficient :
    genSeparates [xorOp] RA = true ∧ minimize [xorOp] [RA] = [xorOp] := by
  native_decide

/- Executable demonstration: print the branches, their RB-sufficiency, and the minimization. -/
#eval genesisVersionSpace RA
#eval genesisVersionSpace RB
#eval (genesisVersionSpace RA).map (fun g => (g, genSeparates g RB))
#eval minimize [orOp, xorOp] [RA, RB]

end FullLangSelfHosting
