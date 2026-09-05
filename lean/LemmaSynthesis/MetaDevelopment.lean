import Std

/-! # Meta-development as data: the programme's own trajectory, its repair schema, and a
    pre-registered prediction.

  The object-level developmental loop is `G_t → ρ_t → K(ρ_t) → Δ_t → G_{t+1}`.  The external
  falsification programme now appears to have the SAME shape at the meta level:

      Π_t → ρ^{meta}_t → K(ρ^{meta}_t) → Δ^{meta}_t → Π_{t+1}

  where Π is the problem-solving architecture, ρ^{meta} a falsification exposing where claimed
  generality stops, and Δ^{meta} the minimal parameterization that removes the exposed
  concreteness.  This file encodes the VERIFIED trajectory as data, proves the two observed
  repairs instantiate one schema (`expose a fixed component → parameterize it`), records the
  type-changing distinction vs the fixed-type `step`, and — crucially — pre-registers a
  PREDICTION about Target 3's seam BEFORE that target's proof state is inspected.
-/

namespace MetaDevelopment

/- A component of the architecture that can be concrete (hard-coded) or parametric. -/
inductive Component where
  | versionSpace   -- candidate construction (finite pre-enumerable vs. schema-generated)
  | carrier        -- term representation (LTerm vs. signature-generic Term S s)
  | grammar        -- candidate-grammar / RHS construction (reverse-shaped closure vs. generic)
  deriving DecidableEq, Repr, Inhabited

/- A meta state records which components are still concrete.  (Components not listed have been
   parameterized.)  The exact trajectory, from the verified falsification record:
     M0 — before Target 1: version space finite/enumerable, carrier LTerm, grammar = reverse closure.
     M1 — after Repair 1: schema operators generic, but carrier LTerm concrete.
     M2 — after Repair 2: carrier parameterized by Signature; grammar still concrete (predicted). -/
structure MetaState where
  concrete : List Component
  deriving DecidableEq, Repr, Inhabited

def M0 : MetaState := ⟨[.versionSpace, .carrier, .grammar]⟩
def M1 : MetaState := ⟨[.carrier, .grammar]⟩
def M2 : MetaState := ⟨[.grammar]⟩

/- The meta residuals (falsification witnesses), each exposing one hidden concreteness. -/
inductive MetaResidual where
  | synthesisArrow       -- Target 1: open lemma space cannot be synthesized (K(ρ)→Candidate).
  | representationArrow  -- Target 2: new vocabulary cannot be represented (carrier LTerm).
  deriving DecidableEq, Repr, Inhabited

/- K(ρ^{meta}): the structural locus each residual exposes. -/
def locus : MetaResidual → Component
  | .synthesisArrow => .versionSpace
  | .representationArrow => .carrier

/- ── The recurring repair shape: Fixed(X) → Expose(X) → Parameterize(X) ────── -/
def parameterize (M : MetaState) (X : Component) : MetaState :=
  ⟨M.concrete.filter (fun c => c != X)⟩

def repair (M : MetaState) (ρ : MetaResidual) : MetaState := parameterize M (locus ρ)

theorem meta_repair_0 : repair M0 .synthesisArrow = M1 := by native_decide
theorem meta_repair_1 : repair M1 .representationArrow = M2 := by native_decide
theorem same_repair_schema :
    repair M0 .synthesisArrow = M1 ∧ repair M1 .representationArrow = M2 := by native_decide

/- ── Hidden concreteness (finite) ───────────────────────────────────────────── -/
def Concrete (M : MetaState) (X : Component) : Bool := M.concrete.contains X

theorem versionSpace_concrete_in_M0 : Concrete M0 .versionSpace = true := by native_decide
theorem carrier_concrete_in_M1     : Concrete M1 .carrier = true := by native_decide
/- The residual's locus is exactly what remains concrete before its repair. -/
theorem locus_is_concrete (M : MetaState) (ρ : MetaResidual) :
    repair M ρ = parameterize M (locus ρ) := by rfl

/- ── Part IV: same-type vs type-changing repair ────────────────────────────── -/
/- The existing domain-generic `step` (DomainGenericKernel.lean) has a FIXED `World : Type`.
   Repair 0 parameterizes the version space (the world type — an LTerm-based schema calculus —
   is unchanged), so it is a same-type extension expressible by that `step`.  Repair 1
   parameterizes the CARRIER, changing the world type from LTerm-based to signature-generic
   `Term S s`, so it is a TYPE-CHANGING update — not expressible by the fixed-type `step`, but
   matching the DependentUniverse (type-changing) rung.  We make that distinction kernel-checkable
   via a world-kind predicate. -/
inductive WorldKind where | concreteCarrier | signatureCarrier
  deriving DecidableEq, Repr, Inhabited

def worldKind (M : MetaState) : WorldKind :=
  if M.concrete.contains .carrier then .concreteCarrier else .signatureCarrier

theorem repair_0_same_type : worldKind M0 = worldKind M1 := by native_decide
theorem repair_1_type_changing : worldKind M1 ≠ worldKind M2 := by native_decide

/- ── THE PRE-REGISTERED PREDICTION (frozen BEFORE Target 3 is inspected) ───── -/
/- After Repair 2, the typed representation, `diff`, and `generalize` transfer (calibration on
   Target 2, subproblem A).  Subproblem B — synthesizing the strengthened RHS (`sum xs + acc`)
   from existing symbols under a bounded closure — remains manual.  The meta model therefore
   predicts the NEXT hidden-concreteness locus is the candidate GRAMMAR / RHS construction:
   Target 3 should reach a representable residual and a correct difference + generalization,
   then FAIL (if anywhere) at grammar/RHS construction. -/
theorem prediction_locus : Concrete M2 .grammar = true := by native_decide

/- The predicted Target-3 grade under this model is C1 (grammar cannot express the repair),
   not E1/E2 (representation/residual would have to fail first). -/

end MetaDevelopment
