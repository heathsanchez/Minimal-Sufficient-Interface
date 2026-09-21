import CLC.Quotient

namespace CLC

universe u

def batchFamilies {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) : Label → SupportFamily U.Token :=
  prefixFamilies R (maxRank R + 1)

structure ClosedView (U : FiniteUniverse) (Label : Type u)
    [Fintype Label] [DecidableEq Label] where
  raw : RawView U Label
  valid : ValidRaw raw
  closed : Label → SupportFamily U.Token
  liveCache : Label → SupportFamily U.Token
  closed_correct : closed = batchFamilies raw
  live_correct : liveCache = fun z => liveView raw.sigma (closed z)

def batchClose {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (hR : ValidRaw R) : ClosedView U Label where
  raw := R
  valid := hR
  closed := batchFamilies R
  liveCache := fun z => liveView R.sigma (batchFamilies R z)
  closed_correct := rfl
  live_correct := rfl

structure ClosedViewEq {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C D : ClosedView U Label) : Prop where
  rawEq : ViewEq C.raw D.raw
  closed_eq : ∀ z, C.closed z = D.closed z
  liveCache_eq : ∀ z, C.liveCache z = D.liveCache z

namespace ClosedViewEq

theorem refl {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] (C : ClosedView U Label) :
    ClosedViewEq C C where
  rawEq := ViewEq.refl C.raw
  closed_eq := fun _ => rfl
  liveCache_eq := fun _ => rfl

theorem symm {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {C D : ClosedView U Label}
    (h : ClosedViewEq C D) : ClosedViewEq D C where
  rawEq := h.rawEq.symm
  closed_eq := fun z => (h.closed_eq z).symm
  liveCache_eq := fun z => (h.liveCache_eq z).symm

theorem trans {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {C D E : ClosedView U Label}
    (hCD : ClosedViewEq C D) (hDE : ClosedViewEq D E) : ClosedViewEq C E where
  rawEq := hCD.rawEq.trans hDE.rawEq
  closed_eq := fun z => (hCD.closed_eq z).trans (hDE.closed_eq z)
  liveCache_eq := fun z => (hCD.liveCache_eq z).trans (hDE.liveCache_eq z)

theorem toEq {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {C D : ClosedView U Label}
    (h : ClosedViewEq C D) : C = D := by
  have hraw := h.rawEq.toEq
  have hclosed := funext h.closed_eq
  have hlive := funext h.liveCache_eq
  cases C
  cases D
  simp_all only

end ClosedViewEq

theorem closedViewEq_query {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {C D : ClosedView U Label}
    (h : ClosedViewEq C D) (Q : ProtectedQuery Label) :
    evalQuery id C.raw C.closed Q = evalQuery id D.raw D.closed Q := by
  rw [h.rawEq.toEq, funext h.closed_eq]

def finsetAll {A : Type u} [DecidableEq A]
    (s : Finset A) (p : A → Bool) : Bool :=
  s.fold (fun x y => x && y) true p

@[simp] theorem finsetAll_eq_true {A : Type u} [DecidableEq A]
    (s : Finset A) (p : A → Bool) :
    finsetAll s p = true ↔ ∀ x ∈ s, p x = true := by
  induction s using Finset.induction_on with
  | empty => simp [finsetAll]
  | @insert a s ha ih =>
      rw [finsetAll, Finset.fold_insert ha, Bool.and_eq_true]
      change (p a = true ∧ finsetAll s p = true) ↔ _
      rw [ih]
      simp

def supportCompatibleB {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (R : RawView U Node) (q : Node → Label) : Bool :=
  decide (maxRank (projectRaw q R) = maxRank R) &&
    finsetAll (Finset.range (maxRank R + 1)) fun r =>
      finsetAll (Finset.univ : Finset Label) fun z =>
        decide (
          fibreMin q R (rankStep R r (prefixFamilies R r)) z =
          rankStep (projectRaw q R) r
            (fibreMin q R (prefixFamilies R r)) z)

theorem supportCompatibleB_eq_true_iff
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    {R : RawView U Node} {q : Node → Label} :
    supportCompatibleB R q = true ↔ SupportCompatible R q := by
  simp only [supportCompatibleB, Bool.and_eq_true, decide_eq_true_eq,
    finsetAll_eq_true, Finset.mem_range, Finset.mem_univ, forall_const]
  constructor
  · rintro ⟨hmax, hstep⟩
    exact {
      base_commutes := fun _ => rfl
      maxRank_commutes := hmax
      step_commutes := fun r hr z => hstep r hr z
      same_snapshot := rfl
    }
  · intro h
    exact ⟨h.maxRank_commutes, fun r hr z => h.step_commutes r hr z⟩

theorem prefix_projection_commutes
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    {R : RawView U Node} {q : Node → Label}
    (h : SupportCompatible R q) (n : Nat) (hn : n ≤ maxRank R + 1)
    (z : Label) :
    fibreMin q R (prefixFamilies R n) z =
      prefixFamilies (projectRaw q R) n z := by
  induction n generalizing z with
  | zero => exact h.base_commutes z
  | succ n ih =>
      rw [prefixFamilies, prefixFamilies]
      rw [h.step_commutes n (Nat.lt_of_succ_le hn) z]
      apply congrArg (fun F => rankStep (projectRaw q R) n F z)
      funext a
      exact ih (Nat.le_trans (Nat.le_succ n) hn) a

theorem batch_projection_commutes
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    {R : RawView U Node} {q : Node → Label}
    (h : SupportCompatible R q) (z : Label) :
    fibreMin q R (batchFamilies R) z =
      batchFamilies (projectRaw q R) z := by
  unfold batchFamilies
  rw [h.maxRank_commutes]
  exact prefix_projection_commutes h (maxRank R + 1) le_rfl z

structure ClosedData (U : FiniteUniverse) (Label : Type u)
    [Fintype Label] [DecidableEq Label] where
  raw : RawView U Label
  closed : Label → SupportFamily U.Token
  liveCache : Label → SupportFamily U.Token

def aggregateClosedData
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) (C : ClosedView U Node) : ClosedData U Label where
  raw := projectRaw q C.raw
  closed := fibreMin q C.raw C.closed
  liveCache := fun z => liveView C.raw.sigma (fibreMin q C.raw C.closed z)

def projectClosed
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) (C : ClosedView U Node)
    (h : SupportCompatible C.raw q)
    (hvalid : ValidRaw (projectRaw q C.raw)) : ClosedView U Label where
  raw := projectRaw q C.raw
  valid := hvalid
  closed := fibreMin q C.raw C.closed
  liveCache := fun z => liveView C.raw.sigma (fibreMin q C.raw C.closed z)
  closed_correct := by
    rw [C.closed_correct]
    exact funext (batch_projection_commutes h)
  live_correct := rfl

theorem closed_queries_preserved
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {S : CertifiedSource U Ωauth}
    {q : U.NodeId → Label} (hq : AdmissibleQuotient Ωauth S q)
    (C : ClosedView U U.NodeId) (hraw : C.raw = S.raw)
    (Q : ProtectedQuery Label) :
    evalQuery q C.raw C.closed Q =
      evalQuery id (projectRaw q C.raw) (fibreMin q C.raw C.closed) Q := by
  rw [hraw]
  cases Q with
  | reachable a b => exact reachable_preserved hq C.closed a b
  | dependsOn a b => exact dependsOn_preserved hq C.closed a b
  | currentlyWarranted a => exact currentlyWarranted_preserved q S.raw C.closed a
  | hasAlternativeSupport a => exact hasAlternativeSupport_preserved q S.raw C.closed a

inductive ViewEvent (U : FiniteUniverse) (Label : Type u)
  | absorbStructure
      (nodes : Finset Label) (edges : Finset U.EdgeId)
      (rankDelta : Label → Nat)
      (baseDelta : Label → SupportFamily U.Token)
  | addBaseSupport (node : Label) (support : Support U.Token)
  | enableToken (token : U.Token)
  | revokeToken (token : U.Token)

def EventPrecondition {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) : ViewEvent U Label → Prop
  | .absorbStructure nodes edges rankDelta _ =>
      Disjoint edges R.activeEdges ∧
      (∀ z ∈ nodes, z ∈ R.activeNodes → rankDelta z = R.rank z) ∧
      (∀ edge ∈ edges, R.edgeToken edge ∈ R.sigma.live)
  | .addBaseSupport node support =>
      node ∈ R.activeNodes ∧ support.Nonempty ∧
      ∀ t ∈ support, t ∉ R.sigma.revoked
  | .enableToken token => CanEnable R.sigma token
  | .revokeToken token => CanRevoke R.sigma token

instance instDecidableEventPrecondition
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (e : ViewEvent U Label) :
    Decidable (EventPrecondition R e) := by
  cases e <;> simp only [EventPrecondition] <;> infer_instance

private def applyRawWith {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (e : ViewEvent U Label)
    (h : EventPrecondition R e) : RawView U Label :=
  match e with
  | .absorbStructure nodes edges rankDelta baseDelta =>
      { R with
        activeNodes := R.activeNodes ∪ nodes
        activeEdges := R.activeEdges ∪ edges
        rank := fun z => if z ∈ nodes then rankDelta z else R.rank z
        base := fun z => if z ∈ nodes then
          normalize (R.base z ∪ baseDelta z) else R.base z }
  | .addBaseSupport node support =>
      { R with base := fun z =>
          if z = node then normalize (R.base z ∪ {support}) else R.base z }
  | .enableToken token => { R with sigma := enable R.sigma token h }
  | .revokeToken token => { R with sigma := revoke R.sigma token h }

def EventValid {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (e : ViewEvent U Label) : Prop :=
  ∃ h : EventPrecondition R e, ValidRaw (applyRawWith R e h)

structure CheckedViewEvent {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] (R : RawView U Label) where
  event : ViewEvent U Label
  precondition : EventPrecondition R event
  validAfter : ValidRaw (applyRawWith R event precondition)

def checkedEnable {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (hR : ValidRaw R) (token : U.Token)
    (h : CanEnable R.sigma token) : CheckedViewEvent R where
  event := .enableToken token
  precondition := h
  validAfter := {
    hR with snapshotDisjoint := (enable R.sigma token h).disjoint
  }

def checkedRevoke {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (hR : ValidRaw R) (token : U.Token)
    (h : CanRevoke R.sigma token) : CheckedViewEvent R where
  event := .revokeToken token
  precondition := h
  validAfter := {
    hR with snapshotDisjoint := (revoke R.sigma token h).disjoint
  }

def checkedAddBaseSupport {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (hR : ValidRaw R)
    (node : Label) (support : Support U.Token)
    (h : EventPrecondition R (.addBaseSupport node support)) :
    CheckedViewEvent R where
  event := .addBaseSupport node support
  precondition := h
  validAfter := by
    refine {
      activeEdgeHasInput := hR.activeEdgeHasInput
      activeEdgeHasOutput := hR.activeEdgeHasOutput
      maskOwner := hR.maskOwner
      activeInputNode := hR.activeInputNode
      activeOutputNode := hR.activeOutputNode
      rank_lt := hR.rank_lt
      baseNormalized := ?_
      snapshotDisjoint := hR.snapshotDisjoint
    }
    intro z
    dsimp [applyRawWith]
    split
    · exact normalize_idempotent _
    · exact hR.baseNormalized z

def checkedAbsorbNodes {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (hR : ValidRaw R)
    (nodes : Finset Label) (rankDelta : Label → Nat)
    (hrank : ∀ z ∈ nodes, rankDelta z = R.rank z) :
    CheckedViewEvent R where
  event := .absorbStructure nodes ∅ rankDelta (fun _ => ∅)
  precondition := by
    refine ⟨Finset.disjoint_empty_left R.activeEdges, ?_, ?_⟩
    · exact fun z hz _ => hrank z hz
    · simp
  validAfter := by
    refine {
      activeEdgeHasInput := ?_
      activeEdgeHasOutput := ?_
      maskOwner := ?_
      activeInputNode := ?_
      activeOutputNode := ?_
      rank_lt := ?_
      baseNormalized := ?_
      snapshotDisjoint := hR.snapshotDisjoint
    }
    · simpa [applyRawWith] using hR.activeEdgeHasInput
    · simpa [applyRawWith] using hR.activeEdgeHasOutput
    · simpa [applyRawWith] using hR.maskOwner
    · intro p hp
      exact Finset.mem_union_left nodes (hR.activeInputNode p (by simpa [applyRawWith] using hp))
    · intro o ho
      exact Finset.mem_union_left nodes (hR.activeOutputNode o (by simpa [applyRawWith] using ho))
    · intro o ho p hp
      have hold := hR.rank_lt o (by simpa [applyRawWith] using ho) p
        (by simpa [applyRawWith] using hp)
      dsimp [applyRawWith]
      by_cases hin : R.inputNode p ∈ nodes
      · by_cases hout : R.outputNode o ∈ nodes
        · rw [ite_eq_left hin, ite_eq_left hout]
          rw [hrank _ hin, hrank _ hout]
          exact hold
        · rw [ite_eq_left hin, ite_eq_right hout]
          rw [hrank _ hin]
          exact hold
      · by_cases hout : R.outputNode o ∈ nodes
        · rw [ite_eq_right hin, ite_eq_left hout]
          rw [hrank _ hout]
          exact hold
        · rw [ite_eq_right hin, ite_eq_right hout]
          exact hold
    · intro z
      dsimp [applyRawWith]
      split
      · exact normalize_idempotent _
      · exact hR.baseNormalized z

def applyRaw {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (e : CheckedViewEvent R) : RawView U Label :=
  applyRawWith R e.event e.precondition

def changedRoots {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) : Finset Label :=
  match e.event with
  | .absorbStructure nodes edges _ _ =>
      nodes ∪ (edges.biUnion fun edge =>
        ((Finset.univ : Finset U.OutPort).filter fun o =>
          C.raw.outOwner o = edge).image C.raw.outputNode)
  | .addBaseSupport node _ => {node}
  | .enableToken token | .revokeToken token =>
      Finset.univ.filter fun z => z ∈ C.raw.activeNodes ∧
        ∃ s ∈ C.closed z, token ∈ s

def affected {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) (z : Label) : Prop :=
  z ∈ changedRoots C e ∨
    ∃ root ∈ changedRoots C e, Reachable (applyRaw C.raw e) root z

instance instDecidableAffected {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) (z : Label) :
    Decidable (affected C e z) := by
  unfold affected
  infer_instance

def flashFamilies {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) :
    Label → SupportFamily U.Token :=
  match e.event with
  | .enableToken _ | .revokeToken _ => C.closed
  | _ => fun z =>
      if affected C e z then batchFamilies (applyRaw C.raw e) z
      else if C.closed z = batchFamilies (applyRaw C.raw e) z then C.closed z
      else batchFamilies (applyRaw C.raw e) z

theorem provenance_unchanged_by_token_event
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) (z : Label)
    {token : U.Token}
    (he : e.event = .enableToken token ∨ e.event = .revokeToken token) :
    flashFamilies C e z = C.closed z := by
  rcases he with he | he <;> simp [flashFamilies, he]

private theorem prefixFamilies_update_sigma
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (sigma : TokenSnapshot U.Token) (n : Nat) :
    prefixFamilies { R with sigma := sigma } n = prefixFamilies R n := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [prefixFamilies]
      rw [ih]
      rfl

private theorem batchFamilies_update_sigma
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (sigma : TokenSnapshot U.Token) :
    batchFamilies { R with sigma := sigma } = batchFamilies R := by
  unfold batchFamilies maxRank
  exact prefixFamilies_update_sigma R sigma _

theorem flashFamilies_eq_batch
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) :
    flashFamilies C e = batchFamilies (applyRaw C.raw e) := by
  funext z
  cases e with
  | mk event precondition validAfter =>
      cases event with
      | absorbStructure nodes edges rankDelta baseDelta =>
          simp only [flashFamilies]
          split
          · rfl
          · split
            · assumption
            · rfl
      | addBaseSupport node support =>
          simp only [flashFamilies]
          split
          · rfl
          · split
            · assumption
            · rfl
      | enableToken token =>
          simp only [flashFamilies]
          rw [C.closed_correct]
          exact (congrFun (batchFamilies_update_sigma C.raw
            (enable C.raw.sigma token precondition)) z).symm
      | revokeToken token =>
          simp only [flashFamilies]
          rw [C.closed_correct]
          exact (congrFun (batchFamilies_update_sigma C.raw
            (revoke C.raw.sigma token precondition)) z).symm

def flashLiveCache {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) :
    Label → SupportFamily U.Token := fun z =>
  let target := liveView (applyRaw C.raw e).sigma (flashFamilies C e z)
  if affected C e z then target
  else if C.liveCache z = target then C.liveCache z else target

theorem flashLiveCache_correct
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) :
    flashLiveCache C e = fun z =>
      liveView (applyRaw C.raw e).sigma (flashFamilies C e z) := by
  funext z
  simp only [flashLiveCache]
  split
  · rfl
  · split
    · assumption
    · rfl

def flashStep {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) : ClosedView U Label where
  raw := applyRaw C.raw e
  valid := e.validAfter
  closed := flashFamilies C e
  liveCache := flashLiveCache C e
  closed_correct := flashFamilies_eq_batch C e
  live_correct := flashLiveCache_correct C e

theorem flashStep_exact {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (C : ClosedView U Label) (e : CheckedViewEvent C.raw) :
    ClosedViewEq (flashStep C e)
      (batchClose (applyRaw C.raw e) e.validAfter) where
  rawEq := ViewEq.refl _
  closed_eq := by
    intro z
    exact congrFun (flashFamilies_eq_batch C e) z
  liveCache_eq := by
    intro z
    rw [show (flashStep C e).liveCache z =
      liveView (applyRaw C.raw e).sigma (flashFamilies C e z) from
        congrFun (flashLiveCache_correct C e) z]
    rw [show flashFamilies C e z = batchFamilies (applyRaw C.raw e) z from
      congrFun (flashFamilies_eq_batch C e) z]
    rfl

end CLC
