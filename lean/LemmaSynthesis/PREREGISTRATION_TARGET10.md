# Target 10 — adequacy of the one-hole context representation (prospective)

## Frozen architecture
Frozen at the relational-residual commit.  ResidualView = (Ctx, Filling): the distinguished diff
position is the hole, `fill` reconstructs the term, `compose` nests contexts — the object-side
one-hole machinery reused literally.  Calibrated: `fill_hole`, `fill_ctx_fillingA/B`,
`fillings_differ` (the same context f(□)y with different fillings g x a0 vs f x a0 is now separated).

## The adequacy test (recursive, now the sixth iteration)
    ∃ ρ_a, ρ_b :  ResidualView(ρ_a) = ResidualView(ρ_b)  ∧  Future(ρ_a) ≠ Future(ρ_b) ?
If YES, the one-hole context representation is still too coarse and the next discriminator is forced.
If NO, the context representation survives.

## Predicted next discriminator (PROVISIONAL, promoted only if a witness forces it)
COMPOSE-level structure — the context's own composition.  A single-hole context records ONE
distinguished position; a residual whose diff spans MULTIPLE positions (or whose evidence relation
is itself a nested context) would need a multi-hole / composed context, which the single-hole
(Ctx, Filling) conflates.  Explicitly provisional: do not add multi-hole/composed structure unless
Target 10 exhibits a witness that specifically requires it.

## Explicit falsifiers (any one ⇒ "context survives" for the tested class)
  F1  no two residuals with equal (Ctx, Filling) but different futures;
  F2  the one-hole representation is sufficient — every context-equal pair has the same required
      control (then the refinement is adequate and the chain stops at the one-hole context).

## No-change rule
ResidualView = (Ctx, Filling) is frozen.  Add multi-hole/compose-level structure only if a
verifier-certified witness (Target 10) forces exactly that discriminator.
