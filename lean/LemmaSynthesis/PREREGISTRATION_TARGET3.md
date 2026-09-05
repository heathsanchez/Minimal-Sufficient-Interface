# External Falsification Target 3 — tree-flatten accumulator (pre-registration)

## Frozen generator
The signature-generic typed term calculus in `lean/LemmaSynthesis/SignatureGenericTerm.lean`
(`Signature` with `Op : Srt → Type`; typed `Term S s`/`Args S ss`; `termEq`/`generalize`/
`subterms`/`diff`) is FROZEN at its commit.  No change to the signature, term representation,
operators, or policy is permitted after this pre-registration.  Only a target-neutral adapter may
parse target 3's proof state into the declared generic representation.

## Target 3 (not inspected while writing this file)
A tree datatype with a tail-recursive flatten accumulator:
    Tree : Type        -- leaf : Nat → Tree ; node : Tree → Tree → Tree
    flatten   : Tree → List Nat
    flattenAcc : Tree → List Nat → List Nat
        flattenAcc (leaf x)   acc = x :: acc
        flattenAcc (node l r) acc = flattenAcc l (flattenAcc r acc)
The too-special statement (attempted first):
    ∀ t, flattenAcc t [] = flatten t
Ordinary structural induction on `t` is expected to get stuck because the induction hypothesis is
specialized to `acc = []` while the `node` step threads a NON-`[]` accumulator through two
recursive calls.

## Sealed known solution (NOT to be fed to the generator)
The representation change is to generalize the concrete initial accumulator `[]` to an arbitrary
universally-quantified accumulator:
    ∀ t acc, flattenAcc t acc = flatten t ++ acc
This requires (i) parameter generalization (`[] ↦ acc`), and (ii) a richer invariant than target 2:
the RHS threads `++` through BOTH recursive calls, so the proof needs `++` associativity.  The
signature changes (new `Tree` sort + `node`/`leaf`/`flatten`/`flattenAcc` operators) and the
failure shape differs from `sum_tr` (the accumulator is threaded through two calls, not one).

## Success grades (strict, reused)
  A    proof state represented; residual extracted; candidate synthesized; candidate proved;
       original target proved.
  B    synthesis works but residual guidance gives no meaningful search reduction.
  C1   signature representation + residual succeed, but candidate grammar cannot express repair.
  C2   grammar can express repair but bounded search cannot find/rank it.
  D    candidate generated but verifier cannot establish it.
  E1   generic signature representation cannot encode the target proof state.
  E2   representation works but residual extraction fails.

## Calibration status at freeze time (honest)
Target 2 (sum_tr) is now CALIBRATION data for the signature-generic representation.  The
calibration established subproblem A (parameter generalization `0 ↦ acc`, via `generalize_acc`)
and K(ρ₂) extraction (`diff_acc`).  Subproblem B — automated synthesis of the strengthened RHS
(`sum xs + acc`) from existing symbols under a bounded closure — is NOT yet automated and is
recorded as the open seam.  Target 3 is the first fresh evaluation of the signature-generic
substrate; it is not a success claim for target 2.

## No-change rule
The generator is frozen.  A clean failure is scientifically useful and becomes the next residual.
