import Std

/-! # The general kernel: residual-forced new separator (observational separation)

  Strong D₂ (`ResidualInducedRoleDiscovery.lean`) proved, for a concrete witness,
  that a verified residual separating two objects collapsed by the current family
  forces every resolving extension to contain a new observable.

  This file deletes ALL concrete content — Policy, Car, the Bool×Bool constitution,
  P0, P1, selectsCapability, even the Bool codomain — and shows the surviving
  invariant is a purely observational-separation fact:

    If B0 identifies p and q (every b ∈ B0 has b p = b q), yet a verified residual
    separates them (some observation has b p ≠ b q), then every resolving family
    must break the B0-equivalence with an observable OUTSIDE B0.

  No structure on Obj or Obs is used, no decidability, no finiteness.  This is a
  theorem about quotients, refinement, and forced distinction — NOT about policies
  or MSI specifically.  Strong D₂ is therefore an INSTANCE of this kernel, not a
  separate phenomenon: the concrete work (in the witness files) is proving that a
  particular B0 genuinely collapses p,q and a particular c genuinely separates them;
  the "forced new observable" step itself is trivial and fully general.
-/

namespace ObservationalSeparation

/- The general theorem: failure outside the current observational quotient forces
   a distinguishing observable. -/
theorem forced_new_separator
    {Obj Obs : Type} (p q : Obj) (B0 B1 : (Obj → Obs) → Prop)
    (hcollapse : ∀ b, B0 b → b p = b q)
    (hresolve : ∃ b, B1 b ∧ b p ≠ b q) :
    ∃ b, B1 b ∧ ¬ B0 b ∧ b p ≠ b q := by
  rcases hresolve with ⟨b, hB1, hsep⟩
  exact ⟨b, hB1, (fun hB0 => hsep (hcollapse b hB0)), hsep⟩

/- Corollary: a collapsing family cannot itself resolve. -/
theorem collapsing_family_cannot_resolve
    {Obj Obs : Type} (p q : Obj) (B0 : (Obj → Obs) → Prop)
    (hcollapse : ∀ b, B0 b → b p = b q) :
    ¬ ∃ b, B0 b ∧ b p ≠ b q := by
  intro hres
  rcases hres with ⟨b, hB0, hsep⟩
  exact hsep (hcollapse b hB0)

/- Corollary: a sufficient extension is exactly B0 plus any one separating
   observable — the residual forces a CONSTRAINT (separate p,q), leaving a version
   space of realizations, not one canonical separator. -/
theorem minimal_extension_resolves
    {Obj Obs : Type} (p q : Obj) (B0 : (Obj → Obs) → Prop) (b : Obj → Obs)
    (hsep : b p ≠ b q) :
    (∃ b', (fun x => B0 x ∨ x = b) b' ∧ b' p ≠ b' q) := by
  exact ⟨b, Or.inr rfl, hsep⟩

end ObservationalSeparation
