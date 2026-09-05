# External Falsification Target 4 — tail-recursive multiplication (prospective test)

## Frozen architecture
The signature-generic machinery frozen at `0dfa251` (Signature/Term/Args + `generalize`/`diff`/
`subterms` from `d54c07b`, plus the candidate-construction algebra `termsUpTo`/`atoms`/
`closureRound` from this repair).  No change before Target 4 classification.

## Prospective prediction being tested (frozen at `9f036b0`, BEFORE the grammar repair)
After the candidate grammar is parameterized, the next hidden-concreteness locus is
search policy / candidate cost / ranking — NOT representation, residual extraction,
anti-unification, parameter generalization, grammar expressivity, or verification.
Predicted failure signature (C2-like): the repair is representable AND generatable, but is not
reached / ranked within the frozen bounded search.

## Target 4 (not inspected while writing this file)
Tail-recursive multiplication with an accumulator:
    mul   : Nat → Nat → Nat        -- naive: mul 0 b = 0 ; mul (n+1) b = b + mul n b
    mulTr : Nat → Nat → Nat → Nat  -- mulTr 0 b acc = acc ; mulTr (n+1) b acc = mulTr n b (acc + b)
The too-special statement (attempted first):
    ∀ n b, mulTr n b 0 = mul n b
Ordinary induction on `n` is expected to get stuck because the IH is specialized to `acc = 0`
while the step needs `acc = b`.

## Sealed known solution (NOT to be fed to the generator)
    ∀ n b acc, mulTr n b acc = mul n b + acc
i.e. `add (mul n b) acc`.  This changes the signature (single `Nat` sort; operators
{zero, add, mul, mulTr} — `mulTr` is 3-ary) and the strengthened RHS composes TWO operators
(`add` over `mul`), so the invariant is a size-2 term buried in a larger candidate space.

## Predicted observable failure signature
Representation succeeds; diff extracts `(0, b)`; generalize yields `mulTr n b acc`; the grammar
GENERATES `add (mul n b) acc` (it is in V_B); but the frozen search/ranking does not reach it
promptly — the invariant ranks late in the candidate enumeration.

## Explicit falsifiers (if any holds, the prediction at 9f036b0 is FALSE)
  F1 representation cannot encode the target (E1)
  F2 diff / residual extraction fails (E2)
  F3 grammar cannot express the repair (C1)
  F4 candidate reached but Lean cannot prove it (D)
  F5 target 4 succeeds with no search/ranking bottleneck

## No-change rule
The architecture is frozen.  A clean failure is the result; do not repair search in this run.
