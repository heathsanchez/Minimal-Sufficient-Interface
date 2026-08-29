import Std
import VerifiedDevelopment
import ResourceIndexedConsequence

universe u v w z

namespace DevelopmentalFailureTaxonomy

open BehaviouralCongruence
open ResidualRegimeBridge
open VerifiedDevelopment
open ResourceIndexedConsequence

/-- A closure obstruction is an exact non-expressibility certificate inside the
    current generated language. It is stronger than unsuccessful search. -/
def ClosureObstruction {Atom : Type u} {Cap : Type v}
    (G : PromotionLanguage Atom Cap) (L : List Atom) (c : Cap) : Prop :=
  ¬ G.Expresses L c

/-- A resource obstruction says the capability is semantically represented by
    the cost model but lies strictly beyond the current budget. -/
def ResourceObstruction {C : Type u}
    (L : CostModel C) (B : Nat) (c : C) : Prop :=
  B < L.cost c

/-- Protected consequence equivalence between two candidate structures. -/
def ConsequenceEquivalent {Test : Type u} {Cand : Type v} {Out : Type w}
    (eval : Test → Cand → Out) (C : List Test) (a b : Cand) : Prop :=
  ∀ t ∈ C, eval t a = eval t b

/-- A protected separator distinguishes two candidates on one protected test. -/
def ProtectedSeparator {Test : Type u} {Cand : Type v} {Out : Type w}
    (eval : Test → Cand → Out) (C : List Test) (a b : Cand) : Prop :=
  ∃ t ∈ C, eval t a ≠ eval t b

/-- A measurement/observation obstruction: a protected distinction exists, but
    every currently authorized probe identifies the two states. -/
def ObservationObstruction {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}
    (observe : Probe → X → V) (target : X → Y)
    (Available : List Probe) (x y : X) : Prop :=
  target x ≠ target y ∧
  ∀ p, p ∈ Available → observe p x = observe p y

/-- Consequence-equivalent alternatives admit no separator from the currently
    protected consequence family. This is the formal WAIT/version-space case. -/
theorem equivalent_has_no_protected_separator
    {Test : Type u} {Cand : Type v} {Out : Type w}
    (eval : Test → Cand → Out) (C : List Test) (a b : Cand)
    (h : ConsequenceEquivalent eval C a b) :
    ¬ ProtectedSeparator eval C a b := by
  intro hs
  rcases hs with ⟨t, ht, hneq⟩
  exact hneq (h t ht)

/-- Adding a genuinely separating protected consequence destroys the prior
    consequence-equivalence relation for that pair. -/
theorem new_consequence_resolves_ambiguity
    {Test : Type u} {Cand : Type v} {Out : Type w}
    (eval : Test → Cand → Out) (C : List Test) (a b : Cand) (t : Test)
    (hsep : eval t a ≠ eval t b) :
    ¬ ConsequenceEquivalent eval (t :: C) a b := by
  intro h
  exact hsep (h t (by simp))

/-- A newly licensed probe that separates an observation obstruction removes
    that obstruction for the enlarged observation authority. -/
theorem observation_obstruction_resolved_by_new_probe
    {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}
    (observe : Probe → X → V) (target : X → Y)
    (Available : List Probe) (q : Probe) (x y : X)
    (hobs : ObservationObstruction observe target Available x y)
    (hq : observe q x ≠ observe q y) :
    ¬ ObservationObstruction observe target (q :: Available) x y := by
  intro hnew
  exact hq (hnew.2 q (by simp))

/-- Exact closure evidence plus a strict promotion witness certifies the EXTEND
    move: the target is absent in the cold generated language and present after
    retaining the promoted atom. -/
theorem closure_obstruction_resolved_by_strict_promotion
    {Atom : Type u} {Cap : Type v}
    (G : PromotionLanguage Atom Cap) (L : List Atom) (a : Atom) (c : Cap)
    (hcold : ClosureObstruction G L c)
    (hwarm : G.Expresses (a :: L) c) :
    StrictPromotion G L a c := by
  exact { cold := hcold, warm := hwarm }

/-- A resource obstruction can be discharged by a reorganization that moves the
    same capability below the frozen budget; this yields an exact cold/warm
    bounded reachability transition without claiming a new denotation. -/
theorem resource_obstruction_resolved_by_reorganization
    {C : Type u}
    (L L' : CostModel C) (B : Nat) (c : C)
    (hcold : ResourceObstruction L B c)
    (hwarm : L'.cost c ≤ B) :
    ¬ ReachableAt L B c ∧ ReachableAt L' B c := by
  exact crosses_budget_becomes_reachable L L' B c hcold hwarm

/-- Certified evidence classes used by the developmental controller. The type
    does not assert that every opaque failure belongs to one class; a verifier
    or completeness theorem must provide a certificate. -/
inductive EvidenceClass where
  | separator
  | closure
  | resource
  | ambiguity
  | observation
  deriving DecidableEq, Repr

/-- The controller move associated with each certified evidence class. -/
inductive DevelopmentMove where
  | split
  | extend
  | promote
  | wait
  | observe
  deriving DecidableEq, Repr

/-- Evidence-to-move routing is deterministic once the evidence class itself is
    externally certified. -/
def route : EvidenceClass → DevelopmentMove
  | .separator => .split
  | .closure => .extend
  | .resource => .promote
  | .ambiguity => .wait
  | .observation => .observe

theorem route_separator : route .separator = .split := rfl
theorem route_closure : route .closure = .extend := rfl
theorem route_resource : route .resource = .promote := rfl
theorem route_ambiguity : route .ambiguity = .wait := rfl
theorem route_observation : route .observation = .observe := rfl

end DevelopmentalFailureTaxonomy
