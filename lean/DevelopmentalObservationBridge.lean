import VerifiedDevelopmentCore
import FiniteCLC
import ScopedCertificates

/-!
# Staged Observation / CLC / Authority Snapshot Bridge (research candidate)

Lean 4.24.0. Uses original R7.2 definitions and a byte-identical, pinned
copy of FiniteCLC from realitygraph research/clc_lean_v3/FiniteTransport.lean.

This proves conditional mathematical interfaces. The source/measurement
authority, sensor accessibility, physical back-action and external verifier
soundness are NOT inferred. Old CLC tests from the earlier representation are
carried exactly; new observation tests pull back to explicit UNKNOWN.
Permission to perform external effects is an independent ceiling.
-/

universe u v w z t r a

namespace DevelopmentalObservationBridge

open VerifiedDevelopmentCore
open ScopedCertificates

-- FiniteCLC.Form is Type-0-only; specialize the existing universe-generic R7.2 API.
variable {M X Q D T : Type}

/-- Actions admitted in this frozen stage. -/
abbrev Allowed (A : ActionMonoid M X) (S : Stage A) :=
  {m : M // S.allow m}

/-- A new observation means observations of all stage-admitted continuations. -/
def history (A : ActionMonoid M X) (S : Stage A)
    (d : X → D) (x : X) : Allowed A S → D :=
  fun m => d (A.act m.1 x)

/-- Retain the original representation and append oldProtected future history. -/
def extended (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (d : X → D) (x : X) :
    Q × (Allowed A S → D) :=
  (q x, history A S d x)

/-- The new representation has exactly the R7.2 stage-refinement kernel.
    This is stronger than the insufficient pointwise (q x, d x). -/
theorem extended_eq_iff_refine (A : ActionMonoid M X)
    (S : Stage A) (q : X → Q) (d : X → D)
    {x y : X} :
    extended A S q d x = extended A S q d y ↔
      Refine A S (fun a b => q a = q b) d x y := by
  constructor
  · intro h
    constructor
    · exact congrArg Prod.fst h
    · intro m hm
      have hHist : history A S d x = history A S d y :=
        congrArg Prod.snd h
      exact congrArg (fun f : Allowed A S → D => f ⟨m, hm⟩) hHist
  · rintro ⟨hq, hd⟩
    apply Prod.ext
    · exact hq
    · funext m
      exact hd m.1 m.2

/-- Closing the new observation under admitted actions preserves congruence,
    provided the old representation is already congruent at this stage. -/
theorem extended_invariant (A : ActionMonoid M X)
    (S : Stage A) (q : X → Q) (d : X → D)
    (hOld : InvariantAt A S (fun a b => q a = q b)) :
    InvariantAt A S
      (fun a b => extended A S q d a = extended A S q d b) := by
  intro g hg x y hxy
  apply (extended_eq_iff_refine A S q d).2
  obtain ⟨hq, hFuture⟩ := (extended_eq_iff_refine A S q d).1 hxy
  constructor
  · exact hOld g hg x y hq
  · intro m hm
    calc
      d (A.act m (A.act g x)) =
          d (A.act (A.mul m g) x) :=
            congrArg d (A.mul_act m g x).symm
      _ = d (A.act (A.mul m g) y) :=
            hFuture (A.mul m g) (S.mul_allow m g hm hg)
      _ = d (A.act m (A.act g y)) :=
            congrArg d (A.mul_act m g y)

/-- A new witnessed observation at an allowed future forces a strict split. -/
theorem future_separator_forces_split (A : ActionMonoid M X)
    (S : Stage A) (q : X → Q) (d : X → D)
    {x y : X} (m : M) (hm : S.allow m)
    (hsep : d (A.act m x) ≠ d (A.act m y)) :
    extended A S q d x ≠ extended A S q d y := by
  intro hEq
  exact hsep (((extended_eq_iff_refine A S q d).1 hEq).2 m hm)

/-- The quotient-factorization obstruction requires surjectivity to build
    an h on every element of the specified codomain, not just q's image. -/
theorem factor_iff_kernel (q : X → Q) (d : X → D)
    (hsurj : Function.Surjective q) :
    (∃ h : Q → D, ∀ x, d x = h (q x)) ↔
      (∀ x y, q x = q y → d x = d y) := by
  constructor
  · rintro ⟨h, hh⟩ x y hxy
    calc
      d x = h (q x) := hh x
      _ = h (q y) := congrArg h hxy
      _ = d y := (hh y).symm
  · intro hker
    classical
    let h : Q → D := fun a => d (Classical.choose (hsurj a))
    refine ⟨h, ?_⟩
    intro x
    have heq : q x = q (Classical.choose (hsurj (q x))) :=
      (Classical.choose_spec (hsurj (q x))).symm
    exact hker x _ heq

/-- Old test values depend only on old representation q.
    The old form reserves NONE as an expressly unresolved future observation. -/
def sourceForm (q : X → Q) (valQ : Q → T → FiniteCLC.Verdict)
    (oldProtected : T → Bool) : FiniteCLC.Form X (Option T) where
  eval := fun x p =>
    match p with
    | none => .unknown
    | some t => valQ (q x) t
  isProtected := fun p =>
    match p with
    | none => true
    | some t => oldProtected t

/-- Target tests include each new admitted future.
    Classification D -> Verdict is supplied; no sensor authenticity is assumed. -/
def targetForm (A : ActionMonoid M X) (S : Stage A)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool) :
    FiniteCLC.Form (Q × (Allowed A S → D)) (T ⊕ Allowed A S) where
  eval := fun z p =>
    match p with
    | .inl t => valQ z.1 t
    | .inr m => classify (z.2 m)
  isProtected := fun p =>
    match p with
    | .inl t => oldProtected t
    | .inr _ => true

/-- All newly introduced target tests map to UNKNOWN on the old side.
    Each original oldProtected test lifts back exactly.
    The stage identity provides an image for the UNKNOWN placeholder. -/
def extensionTransport (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (d : X → D)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool) :
    FiniteCLC.Transport (sourceForm q valQ oldProtected)
      (targetForm A S valQ classify oldProtected) where
  forward := extended A S q d
  pull := fun p =>
    match p with
    | .inl t => some t
    | .inr _ => none
  lift := fun p =>
    match p with
    | none => .inr ⟨A.one, S.one_allow⟩
    | some t => .inl t

/-- Constructed, not merely postulated: stage extension satisfies the original
    CLC validity contract, including target pullback, oldProtected lift and split. -/
theorem extensionTransport_valid (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (d : X → D)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool) :
    FiniteCLC.Valid
      (sourceForm q valQ oldProtected)
      (targetForm A S valQ classify oldProtected)
      (extensionTransport A S q d valQ classify oldProtected) := by
  constructor
  · intro x p
    cases p with
    | inl t => exact Or.inr rfl
    | inr m => exact Or.inl rfl
  constructor
  · intro p hp
    cases p with
    | inl t => exact hp
    | inr m => rfl
  · intro p hp
    cases p with
    | none => exact ⟨rfl, rfl⟩
    | some t => exact ⟨hp, rfl⟩

/-- A previously decisive original test is exactly preserved in the extension.
    This derives from the *actual existing* CLC preservation lemma. -/
theorem old_decisive_preserved (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (d : X → D)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool)
    (x : X) (p : T)
    (hDec : (sourceForm q valQ oldProtected).eval x (some p) ≠ .unknown) :
    (sourceForm q valQ oldProtected).eval x (some p) =
      (targetForm A S valQ classify oldProtected).eval
        (extended A S q d x) (.inl p) := by
  exact FiniteCLC.preserve_decisive
    (extensionTransport_valid A S q d valQ classify oldProtected)
    x (.inl p) hDec

/-- A snapshot is NOT the representation. Negative policy guards are explicit. -/
structure AuthoritySnapshot (Record : Type r) where
  signed : Record → Prop
  permitted : Record → Prop
  denied : Record → Prop

def eligible {Record : Type r} (s : AuthoritySnapshot Record)
    (record : Record) : Prop :=
  s.signed record ∧ s.permitted record ∧ ¬ s.denied record

/-- Withdrawal changes current authority, not signed historical records. -/
def withdraw {Record : Type r} (s : AuthoritySnapshot Record)
    (revoked : Record) : AuthoritySnapshot Record :=
  { s with denied := fun record => s.denied record ∨ record = revoked }

theorem historical_signature_retained {Record : Type r}
    (s : AuthoritySnapshot Record) (revoked record : Record) :
    (withdraw s revoked).signed record = s.signed record := rfl

/-- Requalification of a record is expressible as the original scoped revoke. -/
theorem eligible_withdraw {Record : Type r}
    (s : AuthoritySnapshot Record) (revoked : Record) :
    eligible (withdraw s revoked) =
      ScopedCertificates.revoke (eligible s) revoked := by
  funext record
  apply propext
  constructor
  · rintro ⟨hs, hp, hnot⟩
    refine ⟨⟨hs, hp, ?_⟩, ?_⟩
    · intro h; exact hnot (Or.inl h)
    · intro h; exact hnot (Or.inr h)
  · rintro ⟨⟨hs, hp, hn⟩, hne⟩
    refine ⟨hs, hp, ?_⟩
    intro h
    cases h with
    | inl h => exact hn h
    | inr h => exact hne h

/-- Selective withdrawal retracts all mandatory dependent records at the
    new snapshot. The old signed evidence is not deleted. -/
theorem withdraw_retracts_descendants {Record : Type r}
    (s : AuthoritySnapshot Record) (depends : Record → Record → Prop)
    (revoked record : Record)
    (path : ScopedCertificates.Reaches depends record revoked) :
    ¬ ScopedCertificates.Valid (eligible (withdraw s revoked)) depends record := by
  rw [eligible_withdraw]
  exact ScopedCertificates.revoke_recloses
    (eligible s) depends revoked record path

theorem withdraw_retracts_self {Record : Type r}
    (s : AuthoritySnapshot Record) (depends : Record → Record → Prop)
    (revoked : Record) :
    ¬ ScopedCertificates.Valid (eligible (withdraw s revoked)) depends revoked := by
  rw [eligible_withdraw]
  exact ScopedCertificates.revoke_self (eligible s) depends revoked

/-- Compose positive dependency paths. -/
theorem reaches_append {Record : Type r}
    (depends : Record → Record → Prop) {a b c : Record}
    (h₁ : ScopedCertificates.Reaches depends a b)
    (h₂ : ScopedCertificates.Reaches depends b c) :
    ScopedCertificates.Reaches depends a c := by
  induction h₁ with
  | direct h =>
      exact ScopedCertificates.Reaches.next h h₂
  | next h tail ih =>
      exact ScopedCertificates.Reaches.next h (ih h₂)

/-- Requalification only needs the old root's entire support cone to remain
    eligible: no global monotonic-authority assumption is required. -/
theorem requalify_support_cone {Record : Type r}
    (before after : AuthoritySnapshot Record)
    (depends : Record → Record → Prop) (root : Record)
    (hOld : ScopedCertificates.Valid (eligible before) depends root)
    (hEligible : ∀ node, (node = root ∨
        ScopedCertificates.Reaches depends root node) →
        eligible after node) :
    ScopedCertificates.Valid (eligible after) depends root := by
  have aux : ∀ node, ScopedCertificates.Valid (eligible before) depends node →
      (node = root ∨ ScopedCertificates.Reaches depends root node) →
      ScopedCertificates.Valid (eligible after) depends node := by
    intro node hv
    induction hv with
    | admit node hc hd ih =>
        intro hCone
        apply ScopedCertificates.Valid.admit node (hEligible node hCone)
        intro p hp
        apply ih p hp
        rcases hCone with hEq | hPath
        · subst node
          exact Or.inr (ScopedCertificates.Reaches.direct hp)
        · exact Or.inr (reaches_append depends hPath
            (ScopedCertificates.Reaches.direct hp))
  exact aux root hOld (Or.inl rfl)

/-- An independent support cone survives selective withdrawal even if a
    different branch of the evidence graph depends on the revoked node. -/
theorem independent_cone_survives {Record : Type r}
    (s : AuthoritySnapshot Record) (depends : Record → Record → Prop)
    (root revoked : Record)
    (hOld : ScopedCertificates.Valid (eligible s) depends root)
    (hNoPath : ∀ node, (node = root ∨
        ScopedCertificates.Reaches depends root node) → node ≠ revoked) :
    ScopedCertificates.Valid (eligible (withdraw s revoked)) depends root := by
  apply requalify_support_cone s (withdraw s revoked) depends root hOld
  intro node hCone
  have hValid : ScopedCertificates.Valid (eligible s) depends node := by
    rcases hCone with hEq | hPath
    · subst node
      exact hOld
    · exact ScopedCertificates.reaches_valid (eligible s) depends hPath hOld
  have hBase := ScopedCertificates.valid_checked (eligible s) depends hValid
  rcases hBase with ⟨hs, hp, hn⟩
  refine ⟨hs, hp, ?_⟩
  intro h
  cases h with
  | inl h => exact hn h
  | inr h => exact (hNoPath node hCone) h

/-- Semantic warrant is existential across independently accepted records. -/
def ClaimWarrant {Record : Type r} {Claim : Type a}
    (s : AuthoritySnapshot Record)
    (depends : Record → Record → Prop)
    (asserts : Record → Claim) (claim : Claim) : Prop :=
  ∃ record, asserts record = claim ∧
    ScopedCertificates.Valid (eligible s) depends record

/-- Another support for the same claim remains current if its *own* cone
    is independent of the revoked authority; no blanket claim retraction. -/
theorem alternative_claim_survives {Record : Type r} {Claim : Type a}
    (s : AuthoritySnapshot Record) (depends : Record → Record → Prop)
    (asserts : Record → Claim) (claim : Claim)
    (alternate revoked : Record)
    (hClaim : asserts alternate = claim)
    (hOld : ScopedCertificates.Valid (eligible s) depends alternate)
    (hIndependent : ∀ node, (node = alternate ∨
        ScopedCertificates.Reaches depends alternate node) → node ≠ revoked) :
    ClaimWarrant (withdraw s revoked) depends asserts claim := by
  exact ⟨alternate, hClaim,
    independent_cone_survives s depends alternate revoked hOld hIndependent⟩

/-- Actual external permission is independent of epistemic warrant.
    This is an abstract policy requirement, NOT an enforcement proof. -/
def CanAct {Record : Type r} {Act : Type a}
    (s : AuthoritySnapshot Record)
    (depends : Record → Record → Prop)
    (outerPermission : Act → Prop) (capability : Record) (act : Act) : Prop :=
  outerPermission act ∧
    ScopedCertificates.Valid (eligible s) depends capability

theorem no_permission_escalation {Record : Type r} {Act : Type a}
    (s : AuthoritySnapshot Record)
    (depends : Record → Record → Prop)
    (outerPermission : Act → Prop) (capability : Record) (act : Act)
    (denied : ¬ outerPermission act) :
    ¬ CanAct s depends outerPermission capability act := by
  intro h
  exact denied h.1

end DevelopmentalObservationBridge
