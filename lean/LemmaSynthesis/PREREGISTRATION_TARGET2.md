# External Falsification Target 2 — accumulator generalization (pre-registration)

## Frozen generator
The generic lemma-schema calculus in `lean/LemmaSynthesis/GenericLemmaSynthesis.lean`
(`LTerm` terms; `generalize` / `subterms` / `formEquality` operators; `closureRound` bounded
universe; `isRevOverApp` / `isStuckShape` residual filters) is FROZEN at its commit.  No change
to the schema language, enumeration, cost, K(ρ) interface, or policy is permitted after this
pre-registration.  Only a target-neutral adapter may parse target 2's Lean proof state into
`LTerm` + the existing operators.

## Target 2 (not inspected while writing this file)
A tail-recursive accumulator function over `List Nat`:
    sum_tr : List Nat → Nat → Nat
    sum_tr [] acc       = acc
    sum_tr (x::xs) acc  = sum_tr xs (x + acc)
The too-special statement (the one we attempt first):
    ∀ xs, sum_tr xs 0 = sum xs
The obvious structural induction on `xs` is expected to get stuck because the induction
hypothesis is specialized to `acc = 0` while the step needs `acc = x` (arbitrary).

## Sealed known solution (NOT to be fed to the generator)
The representation change is to generalize the concrete initial accumulator `0` to an arbitrary
universally-quantified accumulator:
    ∀ xs acc, sum_tr xs acc = sum xs + acc
The minimal repair is this generalized invariant (there is no "singleton" analogue here — the
parameter `0` must become a fresh variable `acc`).  This is structurally different from target 1
(reverse), whose repair was a rule for `rev` over `++`; here the repair is generalizing a
*parameter*, not discovering a missing rewrite rule.

## Success grades
  A  strong success — the frozen generator, unmodified, produces (something equivalent to)
     `∀ xs acc, sum_tr xs acc = sum xs + acc`, Lean proves it independently, and it discharges
     the stuck step + the target.
  B  synthesis works but guidance is inert — the generic generator finds it, but guided and
     unguided search are equivalent on this case.
  C  constraint transfers, generator misses — ρ → K works but V_B lacks the repair (the
     `generalize` operator must be able to replace the concrete `0` by a fresh variable `acc`).
  D  candidate generated, verifier cannot prove it — the seam is proof search, not synthesis.
  E  residual extraction fails — the ρ → K transfer was narrower than expected.

## Held-out nearby transfer (only if target 2 succeeds)
A third small theorem (fixed before inspecting the selected repair) that requires the same
parameter-generalization capability, e.g. a tail-recursive `prod` or `append` accumulator, to
test whether the learned schema changes future search beyond this one target.

## No-change rule
The generator is frozen.  If the run stalls, record exactly where.  A clean failure is
scientifically useful and becomes the next residual.
