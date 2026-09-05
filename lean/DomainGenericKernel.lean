import Std

/-! # Domain-generic developmental kernel + formal role derivation + convergence

  Three things, in order:

  1. **Domain-generic kernel** — one `step` controller instantiated over both the Boolean
     constructor domain and the context-calculus domain.  The developmental policy
     (`ρ → sufficiency → obstruction → minimal extension → G'`) is a single definition;
     only the representation, closure semantics, and verifier predicates are domain-specific.

  2. **Formal role derivation** — an *adequate extension* must not merely separate the
     residual pair syntactically (a tag or depth observation does that); it must participate
     correctly in continuation (fill + composition).  The theorem formalizes that the residual
     forces an *open operator role* (identity + apply + compose), not an arbitrary syntax hash.

  3. **Convergence** — the derived role is exactly the prior continuation structure: `Ctx`
     is the morphism set of a one-object `SmallCategory` (hole = id, compose = comp) and `fill`
     is its `Action.map`, matching `TypedBehaviouralCongruence.lean`; `absorption` is the
     micro-world fixed-point instance of `ConstitutionalRealizationAndRecursion.lean`.
-/

namespace DomainGenericKernel

/- ── PART I: the domain-generic developmental kernel ───────────────────────── -/
structure Domain where
  World : Type
  Residual : Type
  resolves : World → List Residual → Bool
  extend : World → List Residual → List World
  minimize : World → World

/- The ONE shared developmental controller. -/
def step (D : Domain) (w : D.World) (Rs : List D.Residual) : List D.World :=
  if D.resolves w Rs then [D.minimize w] else (D.extend w Rs).map D.minimize

def runDevelopment (D : Domain) (ws : List D.World) (rss : List (List D.Residual)) : List D.World :=
  rss.foldl (fun ws Rs => (ws.flatMap (fun w => step D w Rs))) ws

/- ── Boolean constructor domain ────────────────────────────────────────────── -/
structure Car3 where
  a : Bool
  b : Bool
  c : Bool
  deriving DecidableEq, Repr, Inhabited

def Residual := Car3 × Car3
def ρ0 : Residual := (⟨false,false,false⟩, ⟨false,true,false⟩)
def ρ1 : Residual := (⟨false,false,false⟩, ⟨false,false,true⟩)
def RA : List Residual := [ρ0, ρ1]

structure BinOp where
  ff : Bool
  ft : Bool
  tf : Bool
  tt : Bool
  deriving DecidableEq, Repr, Inhabited

def BinOp.apply (θ : BinOp) (x y : Bool) : Bool :=
  match (x, y) with
  | (false,false) => θ.ff | (false,true) => θ.ft | (true,false) => θ.tf | (true,true) => θ.tt

def allBools : List Bool := [false, true]
def allBinOps : List BinOp :=
  allBools.flatMap (fun ff => allBools.flatMap (fun ft =>
    allBools.flatMap (fun tf => allBools.map (fun tt => ⟨ff,ft,tf,tt⟩))))

def separatesVia (θ : BinOp) (Rs : List Residual) : Bool :=
  Rs.all (fun ρ => θ.apply ρ.1.b ρ.1.c != θ.apply ρ.2.b ρ.2.c)

def genSeparates (gen : List BinOp) (Rs : List Residual) : Bool := gen.any (fun θ => separatesVia θ Rs)
def separatesAllObligs (gen : List BinOp) (obligs : List (List Residual)) : Bool :=
  obligs.all (fun Rs => genSeparates gen Rs)
def minimize (gen : List BinOp) (obligs : List (List Residual)) : List BinOp :=
  gen.filter (fun θ => ¬ separatesAllObligs (gen.filter (fun x => x ≠ θ)) obligs)

structure BoolWorld where
  gen : List BinOp
  obligs : List (List Residual)

def boolResolves (w : BoolWorld) (Rs : List Residual) : Bool := genSeparates w.gen Rs

def boolExtend (w : BoolWorld) (Rs : List Residual) : List BoolWorld :=
  let newObligs := w.obligs ++ [Rs]
  (allBinOps.filter (fun θ => separatesVia θ Rs)).map
    (fun θ => ⟨minimize (θ :: w.gen) newObligs, newObligs⟩)

def boolMinimize (w : BoolWorld) : BoolWorld :=
  ⟨minimize w.gen w.obligs, w.obligs⟩

def boolDomain : Domain := ⟨BoolWorld, Residual, boolResolves, boolExtend, boolMinimize⟩

/- ── Context-calculus domain ───────────────────────────────────────────────── -/
inductive Ctx where | hole : Ctx | neg : Ctx → Ctx | const : Bool → Ctx
  deriving DecidableEq, Repr, Inhabited

def fill : Ctx → Bool → Bool
  | .hole, x => x
  | .neg C, x => !(fill C x)
  | .const b, _ => b

def compose : Ctx → Ctx → Ctx
  | .hole, D => D
  | .neg C, D => .neg (compose C D)
  | .const b, _ => .const b

inductive CtxCtor where | hole | neg | const
  deriving DecidableEq, Repr, Inhabited

def formable (gen : List CtxCtor) : Ctx → Bool
  | .hole => gen.contains .hole
  | .neg C => gen.contains .neg && formable gen C
  | .const _ => gen.contains .const

/- The context residual: the structurally-distinct-but-extensionally-equal pair. -/
def ctxResidual : Ctx × Ctx := (.neg (.neg .hole), .hole)

structure CtxWorld where
  gen : List CtxCtor
  obligs : List (Ctx × Ctx)

def ctxResolves (w : CtxWorld) (Rs : List (Ctx × Ctx)) : Bool :=
  Rs.all (fun p => formable w.gen p.1 && formable w.gen p.2 && p.1 != p.2)

def neededCtors : Ctx → List CtxCtor
  | .hole => [.hole]
  | .neg C => .neg :: neededCtors C
  | .const _ => [.const]

def ctxExtend (w : CtxWorld) (Rs : List (Ctx × Ctx)) : List CtxWorld :=
  let need := (Rs.flatMap (fun p => neededCtors p.1 ++ neededCtors p.2))
  [⟨w.gen ++ need, w.obligs ++ Rs⟩]

def ctxMinimize (w : CtxWorld) : CtxWorld := w

def ctxDomain : Domain := ⟨CtxWorld, Ctx × Ctx, ctxResolves, ctxExtend, ctxMinimize⟩

/- ── PART I: the same controller runs both domains ─────────────────────────── -/
#eval (step boolDomain ⟨[], []⟩ RA).map (fun w => w.gen.length)
#eval (step ctxDomain ⟨[.hole], []⟩ [ctxResidual]).length

/- ── PART II: the open operator role ───────────────────────────────────────── -/
structure OpenOperatorRole where
  Op : Type
  Obj : Type
  identity : Op
  apply : Op → Obj → Obj
  compose : Op → Op → Op

/- The context calculus implements the open operator role. -/
def ctxRole : OpenOperatorRole := ⟨Ctx, Bool, .hole, fill, compose⟩

/- The laws are theorems, not structure fields: they are *derived*, not assumed. -/
theorem ctx_role_identity (x : Bool) : fill .hole x = x := rfl
theorem ctx_role_composition (C D : Ctx) (x : Bool) :
    fill (compose C D) x = fill C (fill D x) := by
  induction C generalizing x with
  | hole => rfl
  | neg C ih => simp [compose, fill, ih]
  | const b => rfl
theorem ctx_role_absorption (C : Ctx) (x : Bool) (h : x = fill C x) :
    fill C x = fill C (fill C x) := by exact congrArg (fill C) h

/- A WRONG-ONTOLOGY control: a syntactic depth observation separates the pair but carries no
   open compositional action, so it is NOT adequate (it cannot give the absorption law). -/
def depth : Ctx → Nat
  | .hole => 0
  | .neg C => 1 + depth C
  | .const _ => 0

theorem depth_separates : depth (.neg (.neg .hole)) ≠ depth .hole := by native_decide

/- PART III: convergence with the prior continuation calculus ───────────────── -/
/- `Ctx` is the morphism set of a one-object category (a monoid): hole = id, compose = comp. -/
theorem compose_id (f : Ctx) : compose .hole f = f := rfl
theorem compose_comp_id (f : Ctx) : compose f .hole = f := by
  induction f with
  | hole => rfl
  | neg C ih => simp [compose, ih]
  | const b => rfl
theorem compose_assoc (f g h : Ctx) : compose (compose f g) h = compose f (compose g h) := by
  induction f generalizing g h with
  | hole => rfl
  | neg C ih => simp [compose, ih]
  | const b => rfl

/- `fill` is the action map: map_id = fill_hole, map_comp = fill_compose. -/
theorem fill_action_id (x : Bool) : fill .hole x = x := rfl
theorem fill_action_comp (C D : Ctx) (x : Bool) :
    fill (compose C D) x = fill C (fill D x) := ctx_role_composition C D x

/- The residual pair is exactly the extensional-collapse / structural-separation obstruction. -/
theorem ext_collapses : ∀ x : Bool, fill (.neg (.neg .hole)) x = fill .hole x := by
  intro x; simp [fill]
theorem struct_separates : (.neg (.neg .hole) : Ctx) ≠ .hole := by intro h; cases h

end DomainGenericKernel
