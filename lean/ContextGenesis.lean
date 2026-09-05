import Std

/-! # Residual-induced context calculus

  The Boolean completeness boundary (`nand_functionally_complete` in `UnifiedStep.lean`) proved
  that no purely extensional Boolean residual can force a new Boolean constructor class.  The
  next residual must therefore be *structural* — it must concern how an object behaves inside a
  surrounding expression (a continuation / context), not a new value-level predicate.

  This reconnects to two prior verified results in this repo:
  - `TypedBehaviouralCongruence.lean`: contextual behavioural equivalence — two states are
    identical iff every typed continuation (context) yields the same observation.  The
    "continuation" *is* a one-hole context: the hole is `id`, fill is `map f`, composition is
    `comp`.
  - `ConstitutionalRealizationAndRecursion.lean`: the fixed-point law
    `x = C[x]  ⟹  C[x] = C[C[x]]`.

  The micro-world here is the smallest load-bearing instance:
  - The OLD language observes *extensionally*: it sees only `fill C x` for concrete values `x`.
    It is complete for extensional behaviour, so it cannot separate two contexts that agree on
    every value.
  - The RESIDUAL: the contexts `neg (neg hole)` and `hole` are extensionally identical
    (`∀ x, fill … x = x`) yet *structurally* distinct.  Distinguishing them is not a new Boolean
    predicate — it requires observing the context's syntax (the hole, the `neg` constructor).

  The derived role, before naming it "context", is: a unary operator with a distinguished
  identity (hole), an application (fill), and composition — exactly the one-hole operator
  `C : X → X` with fill/composition laws.  The synthesized schema is the minimal context calculus.
-/

namespace ContextGenesis

/- The minimal context calculus: a unary operator over Bool with a distinguished hole. -/
inductive Ctx where
  | hole : Ctx
  | neg : Ctx → Ctx
  | const : Bool → Ctx
  deriving DecidableEq, Repr, Inhabited

def fill : Ctx → Bool → Bool
  | .hole, x => x
  | .neg C, x => !(fill C x)
  | .const b, _ => b

def compose : Ctx → Ctx → Ctx
  | .hole, D => D
  | .neg C, D => .neg (compose C D)
  | .const b, _ => .const b

/- ── The context laws ──────────────────────────────────────────────────────── -/

/- The hole is the identity for fill. -/
theorem fill_hole (x : Bool) : fill .hole x = x := by rfl

/- Composition is associative through fill: fill of a composite is fill of the fill. -/
theorem fill_compose (C D : Ctx) (x : Bool) :
    fill (compose C D) x = fill C (fill D x) := by
  induction C generalizing x with
  | hole => rfl
  | neg C ih => simp [compose, fill, ih]
  | const b => rfl

/- The absorption / fixed-point consequence: `x = C[x]` forces `C[x] = C[C[x]]`. -/
theorem absorption (C : Ctx) (x : Bool) (h : x = fill C x) :
    fill C x = fill C (fill C x) := by
  exact congrArg (fill C) h

/- ── The residual: extensionally equal, structurally distinct ──────────────── -/

/- The OLD (extensional) language collapses the two contexts: `neg (neg hole)` and `hole`
   agree on every value, so no value-level observation can separate them.  This is genuine
   closure exhaustion — a universal statement over all inputs, not an enumeration. -/
theorem ext_collapses : ∀ x : Bool, fill (.neg (.neg .hole)) x = fill .hole x := by
  intro x
  simp [fill]

/- The context calculus (structural) separates them: the two are distinct syntax. -/
theorem struct_separates : (.neg (.neg .hole) : Ctx) ≠ .hole := by
  intro h
  cases h

/- The residual therefore cannot be resolved by any extensional observation: every such
   observation identifies the two contexts (ext_collapses), yet they are genuinely distinct
   (struct_separates).  The missing capability is the *structure* of the context — the hole and
   the `neg` constructor — not another Boolean predicate. -/

/- ── Ablation: the extensional language is exactly what cannot separate them ── -/
/- `ext_collapses` IS the ablation: strip the structural syntax and the two contexts are
   indistinguishable, so the residual is unresolved. -/

/- ── Second generation: a residual expressible only because contexts now exist ── -/
/- Composition of contexts is the operation the flat observation language lacked.  The
   composite `neg (neg hole)` equals `compose (neg hole) (neg hole)` structurally. -/
theorem compose_neg_neg : compose (.neg .hole) (.neg .hole) = (.neg (.neg .hole) : Ctx) := by
  rfl

/- The composition law is load-bearing: it relates fill of a composite to repeated fill. -/
theorem fill_compose_neg_neg (x : Bool) :
    fill (compose (.neg .hole) (.neg .hole)) x = x := by
  simp [compose, fill]

end ContextGenesis
