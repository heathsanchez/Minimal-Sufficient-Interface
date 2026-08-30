import Std

/-!
Equality-free residual-generated measurement from the bedrock directed substrate.

The previous residual-genesis gate generated a Boolean/Prop probe by testing
whether the observed state was definitionally equal to a distinguished endpoint.
This file removes that state-equality constructor.

Only a raw directed generator family `G : Ω → Ω → Type` is assumed. Its free
finite continuation type `Path G x y` is generated from reflexivity and raw
one-step generators. A residual is now an operational obstruction: from one
endpoint there is no continuation to a target. The residual itself generates
its measurement by asking for continuation evidence to that target.

The observation remains Type-valued path evidence. Only the externally checked
separation statements use propositional truncation via `Nonempty`; no equality
predicate on states appears in the probe constructor.
-/

universe u v

namespace ReachabilityGeneratedProbeGenesis

/-- Free finite continuation generated only from raw directed possibilities. -/
inductive Path {Ω : Type u} (G : Ω → Ω → Type v) : Ω → Ω → Type (max u v)
  | refl (x : Ω) : Path G x x
  | step {x y z : Ω} : G x y → Path G y z → Path G x z

/-- Type-valued observation: evidence that `z` can continue to `target`. -/
def ReachProbe {Ω : Type u} (G : Ω → Ω → Type v) (target : Ω) :
    Ω → Type (max u v) :=
  fun z => Path G z target

/-- Equality-free operational residual: verified absence of a continuation from
    `blocked` to `target`. -/
structure ReachabilityResidual {Ω : Type u} (G : Ω → Ω → Type v) where
  blocked : Ω
  target : Ω
  obstruction : Path G blocked target → Empty

/-- The residual constructs its own observation directly from the raw substrate. -/
def generatedProbe {Ω : Type u} {G : Ω → Ω → Type v}
    (r : ReachabilityResidual G) : Ω → Type (max u v) :=
  ReachProbe G r.target

/-- The generated probe is inhabited at its target without using state equality. -/
def generatedProbe_target
    {Ω : Type u} {G : Ω → Ω → Type v} (r : ReachabilityResidual G) :
    generatedProbe r r.target :=
  Path.refl r.target

/-- The verified obstruction empties the same probe at the blocked endpoint. -/
def generatedProbe_blocked_empty
    {Ω : Type u} {G : Ω → Ω → Type v} (r : ReachabilityResidual G) :
    generatedProbe r r.blocked → Empty :=
  r.obstruction

/-- Propositional certificate that the Type-valued generated probe separates
    the residual endpoints. -/
theorem residual_generates_typed_separator
    {Ω : Type u} {G : Ω → Ω → Type v} (r : ReachabilityResidual G) :
    (¬ Nonempty (generatedProbe r r.blocked)) ∧
      Nonempty (generatedProbe r r.target) := by
  constructor
  · intro h
    rcases h with ⟨p⟩
    exact (r.obstruction p).elim
  · exact ⟨generatedProbe_target r⟩

/-- A raw generator itself creates a nontrivial continuation without equality. -/
def rawGeneratorCreatesPath
    {Ω : Type u} {G : Ω → Ω → Type v} {x y : Ω} (g : G x y) :
    Path G x y :=
  Path.step g (Path.refl y)

/-- Mutual reachability means every state can continue to every other state. -/
def MutuallyReachable {Ω : Type u} (G : Ω → Ω → Type v) : Prop :=
  ∀ x y : Ω, Nonempty (Path G x y)

/-- Under mutual reachability every target-reachability probe is inhabited at
    every state, so this bedrock constructor has no separating power there. -/
theorem reachProbe_inhabited_everywhere_of_mutual
    {Ω : Type u} {G : Ω → Ω → Type v}
    (hmut : MutuallyReachable G) (target z : Ω) :
    Nonempty (ReachProbe G target z) :=
  hmut z target

/-- No equality-free reachability residual can coexist with mutual reachability. -/
theorem no_reachability_residual_of_mutual
    {Ω : Type u} {G : Ω → Ω → Type v}
    (hmut : MutuallyReachable G) :
    ¬ Nonempty (ReachabilityResidual G) := by
  intro hr
  rcases hr with ⟨r⟩
  have hp : Nonempty (Path G r.blocked r.target) := hmut r.blocked r.target
  rcases hp with ⟨p⟩
  exact (r.obstruction p).elim

/-- Minimal boundary certificate: raw directed structure suffices to generate a
    typed separator when the verified residual exposes an asymmetric
    continuation obstruction; such a residual itself certifies that the
    substrate is not mutually reachable. -/
theorem equality_free_probe_genesis_certificate
    {Ω : Type u} {G : Ω → Ω → Type v}
    (r : ReachabilityResidual G) :
    ((¬ Nonempty (generatedProbe r r.blocked)) ∧
      Nonempty (generatedProbe r r.target)) ∧
    ¬ MutuallyReachable G := by
  constructor
  · exact residual_generates_typed_separator r
  · intro hmut
    exact no_reachability_residual_of_mutual hmut ⟨r⟩

end ReachabilityGeneratedProbeGenesis

#check ReachabilityGeneratedProbeGenesis.residual_generates_typed_separator
#check ReachabilityGeneratedProbeGenesis.rawGeneratorCreatesPath
#check ReachabilityGeneratedProbeGenesis.reachProbe_inhabited_everywhere_of_mutual
#check ReachabilityGeneratedProbeGenesis.no_reachability_residual_of_mutual
#check ReachabilityGeneratedProbeGenesis.equality_free_probe_genesis_certificate
