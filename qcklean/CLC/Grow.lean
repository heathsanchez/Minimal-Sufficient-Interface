import CLC.Flash

namespace CLC

universe u

inductive SourceEvent (U : FiniteUniverse)
  | activateStructure (nodes : Finset U.NodeId) (edges : Finset U.EdgeId)
  | addBaseSupport (node : U.NodeId) (support : Support U.Token)
  | enableToken (token : U.Token)
  | revokeToken (token : U.Token)

def sourceViewEvent {U : FiniteUniverse}
    {Ωauth : AuthoritySnapshot U.CertId}
    (S : CertifiedSource U Ωauth) : SourceEvent U → ViewEvent U U.NodeId
  | .activateStructure nodes edges =>
      .absorbStructure nodes edges S.raw.rank
        (fun z => if z ∈ nodes then S.raw.base z else ∅)
  | .addBaseSupport node support => .addBaseSupport node support
  | .enableToken token => .enableToken token
  | .revokeToken token => .revokeToken token

structure CheckedSourceEvent {U : FiniteUniverse}
    {Ωauth : AuthoritySnapshot U.CertId}
    (S : CertifiedSource U Ωauth) (e : SourceEvent U) where
  sourcePrecondition :
    match e with
    | .activateStructure nodes edges =>
        Disjoint nodes S.raw.activeNodes ∧ Disjoint edges S.raw.activeEdges
    | .addBaseSupport node support =>
        node ∈ S.raw.activeNodes ∧ support.Nonempty ∧
          ∀ t ∈ support, t ∉ S.raw.sigma.revoked
    | .enableToken token => CanEnable S.raw.sigma token
    | .revokeToken token => CanRevoke S.raw.sigma token
  sourceDelta : CheckedViewEvent S.raw
  sourceDelta_matches : sourceDelta.event = sourceViewEvent S e
  nextSource : CertifiedSource U Ωauth
  nextRaw_eq : nextSource.raw = applyRaw S.raw sourceDelta

def applySource {U : FiniteUniverse}
    {Ωauth : AuthoritySnapshot U.CertId} {S : CertifiedSource U Ωauth}
    {e : SourceEvent U} (checked : CheckedSourceEvent S e) :
    CertifiedSource U Ωauth :=
  checked.nextSource

structure ClosedSource (U : FiniteUniverse)
    (Ωauth : AuthoritySnapshot U.CertId) where
  source : CertifiedSource U Ωauth
  closed : ClosedView U U.NodeId
  raw_eq : closed.raw = source.raw

def sourceClosedView {U : FiniteUniverse}
    {Ωauth : AuthoritySnapshot U.CertId}
    (C : ClosedSource U Ωauth) : ClosedView U U.NodeId := C.closed

def rebaseChecked {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R S : RawView U Label} (h : ViewEq R S)
    (e : CheckedViewEvent R) : CheckedViewEvent S := by
  rw [← h.toEq]
  exact e

theorem applyRaw_congr {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R S : RawView U Label} (h : ViewEq R S) (e : CheckedViewEvent R) :
    ViewEq (applyRaw R e) (applyRaw S (rebaseChecked h e)) := by
  have heq := h.toEq
  subst S
  exact ViewEq.refl (applyRaw R e)

def rebaseClosedChecked {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {C D : ClosedView U Label} (h : ClosedViewEq C D)
    (e : CheckedViewEvent C.raw) : CheckedViewEvent D.raw :=
  rebaseChecked h.rawEq e

theorem flashStep_congr {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {C D : ClosedView U Label} (h : ClosedViewEq C D)
    (e : CheckedViewEvent C.raw) :
    ClosedViewEq (flashStep C e)
      (flashStep D (rebaseClosedChecked h e)) := by
  have heq := h.toEq
  subst D
  exact ClosedViewEq.refl (flashStep C e)

theorem viewEqOfEq {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R S : RawView U Label} (h : R = S) : ViewEq R S := by
  subst S
  exact ViewEq.refl _

def sourceStep {U : FiniteUniverse}
    {Ωauth : AuthoritySnapshot U.CertId}
    (C : ClosedSource U Ωauth) {e : SourceEvent U}
    (checked : CheckedSourceEvent C.source e) : ClosedSource U Ωauth := by
  let hraw : ViewEq C.source.raw C.closed.raw := viewEqOfEq C.raw_eq.symm
  let delta := rebaseChecked hraw checked.sourceDelta
  let nextClosed := flashStep C.closed delta
  refine {
    source := applySource checked
    closed := nextClosed
    raw_eq := ?_
  }
  exact (applyRaw_congr hraw checked.sourceDelta).toEq.symm.trans
    checked.nextRaw_eq.symm

theorem closedSupportCompatible {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {q : U.NodeId → Label}
    (C : ClosedSource U Ωauth)
    (hq : AdmissibleQuotient Ωauth C.source q) :
    SupportCompatible (sourceClosedView C).raw q := by
  change SupportCompatible C.closed.raw q
  rw [C.raw_eq]
  exact hq.supportCompatible

theorem closedProjectedValid {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {q : U.NodeId → Label}
    (C : ClosedSource U Ωauth)
    (hq : AdmissibleQuotient Ωauth C.source q) :
    ValidRaw (projectRaw q (sourceClosedView C).raw) := by
  change ValidRaw (projectRaw q C.closed.raw)
  rw [C.raw_eq]
  exact projectedValid hq

def canonicalProjected {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {q : U.NodeId → Label}
    (C : ClosedSource U Ωauth)
    (hq : AdmissibleQuotient Ωauth C.source q) : ClosedView U Label :=
  projectClosed q (sourceClosedView C)
    (closedSupportCompatible C hq) (closedProjectedValid C hq)

def mapEvent {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId}
    (C : ClosedSource U Ωauth) (q : U.NodeId → Label)
    (e : SourceEvent U) (checked : CheckedSourceEvent C.source e) :
    ViewEvent U Label :=
  match e with
  | .activateStructure nodes edges =>
      .absorbStructure (nodes.image q) edges
        (fun z => fibreRank q (applyRaw C.closed.raw
          (rebaseChecked (viewEqOfEq C.raw_eq.symm) checked.sourceDelta)) z)
        (fun z => fibreMin q C.source.raw
          (fun x => if x ∈ nodes then C.source.raw.base x else ∅) z)
  | .addBaseSupport node support => .addBaseSupport (q node) support
  | .enableToken token => .enableToken token
  | .revokeToken token => .revokeToken token

structure AllowedStep {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (Ωauth : AuthoritySnapshot U.CertId)
    (q : U.NodeId → Label)
    (C : ClosedSource U Ωauth)
    (hq : AdmissibleQuotient Ωauth C.source q)
    (e : SourceEvent U) where
  checkedSource : CheckedSourceEvent C.source e
  projectedDelta : CheckedViewEvent (projectRaw q C.source.raw)
  projectedDelta_eq : projectedDelta.event = mapEvent C q e checkedSource
  rawCommutes :
    ViewEq
      (projectRaw q (applySource checkedSource).raw)
      (applyRaw (projectRaw q C.source.raw) projectedDelta)
  nextAdmissible :
    AdmissibleQuotient Ωauth (applySource checkedSource) q
  closedCommutes :
    ClosedViewEq
      (flashStep (canonicalProjected C hq)
        (rebaseChecked
          (viewEqOfEq (congrArg (projectRaw q) C.raw_eq).symm)
          projectedDelta))
      (canonicalProjected (sourceStep C checkedSource) nextAdmissible)

set_option genSizeOf false in
inductive AllowedTrace {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (Ωauth : AuthoritySnapshot U.CertId) (q : U.NodeId → Label) :
    (C : ClosedSource U Ωauth) →
    AdmissibleQuotient Ωauth C.source q →
    List (SourceEvent U) → Type (u + 1)
  | nil (C) (hq) : AllowedTrace Ωauth q C hq []
  | cons {C hq e es}
      (step : AllowedStep Ωauth q C hq e)
      (tail : AllowedTrace Ωauth q (sourceStep C step.checkedSource)
        step.nextAdmissible es) :
      AllowedTrace Ωauth q C hq (e :: es)

inductive ProjectedTrace {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] :
    (C : ClosedView U Label) → Type (max u 1)
  | nil (C) : ProjectedTrace C
  | cons {C} (e : CheckedViewEvent C.raw)
      (tail : ProjectedTrace (flashStep C e)) : ProjectedTrace C

def rebaseProjectedTrace {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {C D : ClosedView U Label} (h : ClosedViewEq C D) :
    ProjectedTrace C → ProjectedTrace D
  | .nil _ => .nil D
  | .cons e tail =>
      .cons (rebaseClosedChecked h e)
        (rebaseProjectedTrace (flashStep_congr h e) tail)

def growProjected {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) : ProjectedTrace C → ClosedView U Label
  | .nil _ => C
  | .cons e tail => growProjected (flashStep C e) tail

theorem growProjected_rebase {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {C D : ClosedView U Label} (h : ClosedViewEq C D)
  (trace : ProjectedTrace C) :
    ClosedViewEq (growProjected C trace)
      (growProjected D (rebaseProjectedTrace h trace)) := by
  induction trace generalizing D with
  | nil => exact h
  | cons e tail ih => exact ih (flashStep_congr h e)

def projectTrace {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {q : U.NodeId → Label}
    {C : ClosedSource U Ωauth} {hq : AdmissibleQuotient Ωauth C.source q}
    {E : List (SourceEvent U)} :
    AllowedTrace Ωauth q C hq E → ProjectedTrace (canonicalProjected C hq)
  | .nil _ _ => .nil _
  | .cons step tail =>
      let event := rebaseChecked
        (viewEqOfEq (congrArg (projectRaw q) C.raw_eq).symm)
        step.projectedDelta
      .cons event
        (rebaseProjectedTrace step.closedCommutes.symm (projectTrace tail))

def growSource {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {q : U.NodeId → Label}
    (C : ClosedSource U Ωauth) {hq : AdmissibleQuotient Ωauth C.source q}
    {E : List (SourceEvent U)} :
    AllowedTrace Ωauth q C hq E → ClosedSource U Ωauth
  | .nil _ _ => C
  | .cons step tail => growSource (sourceStep C step.checkedSource) tail

theorem grow_dissolve_preserves_protected_queries
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {q : U.NodeId → Label}
    {C : ClosedSource U Ωauth} {E : List (SourceEvent U)}
    (hq : AdmissibleQuotient Ωauth C.source q)
    (hE : AllowedTrace Ωauth q C hq E)
    (Q : ProtectedQuery Label) :
    evalQuery q
        (sourceClosedView (growSource C hE)).raw
        (sourceClosedView (growSource C hE)).closed Q =
      evalQuery id
        (growProjected (canonicalProjected C hq) (projectTrace hE)).raw
        (growProjected (canonicalProjected C hq) (projectTrace hE)).closed Q := by
  induction hE with
  | nil C hq =>
      change evalQuery q C.closed.raw C.closed.closed Q =
        evalQuery id (projectRaw q C.closed.raw)
          (fibreMin q C.closed.raw C.closed.closed) Q
      exact closed_queries_preserved hq C.closed C.raw_eq Q
  | @cons C hq e es step tail ih =>
      calc
        evalQuery q
            (sourceClosedView
              (growSource (sourceStep C step.checkedSource) tail)).raw
            (sourceClosedView
              (growSource (sourceStep C step.checkedSource) tail)).closed Q =
          evalQuery id
            (growProjected
              (canonicalProjected (sourceStep C step.checkedSource)
                step.nextAdmissible)
              (projectTrace tail)).raw
            (growProjected
              (canonicalProjected (sourceStep C step.checkedSource)
                step.nextAdmissible)
              (projectTrace tail)).closed Q := ih
        _ = _ := by
          exact closedViewEq_query
            (growProjected_rebase step.closedCommutes.symm (projectTrace tail)) Q

end CLC
