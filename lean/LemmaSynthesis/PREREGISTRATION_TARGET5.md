# External Falsification Target 5 — exponentiation accumulator (control-parametric transfer)

## Frozen architecture
Frozen at `9d82346`: Signature/Term + `diff`/`generalize` + candidate grammar + SearchPolicy
(explicit state) + frozen selector `SelectPolicy : SearchConstraint → SearchPolicy`.

## Prospective prediction being tested (frozen at `9d82346`, BEFORE Target 5)
Prediction 2: after search policy becomes state, the next hidden-concreteness locus is the
RESIDUAL-FEATURE EXTRACTOR / policy selector (the fixed {requiredDepth, safeArity} feature set).
If Target 5 fails *because the {depth, arity} features are insufficient to express the new
residual's constraint*, prediction 2 is CONFIRMED.  If the frozen selector transfers and Target 5
succeeds, control-parametric transfer is validated and prediction 2 remains live (deferred).

## Target 5 (not inspected while writing this file)
Exponentiation accumulator:
    pow    : Nat → Nat → Nat        -- pow b 0 = 1 ; pow b (e+1) = b * pow b e
    powAcc : Nat → Nat → Nat → Nat  -- powAcc b 0 acc = acc ; powAcc b (e+1) acc = powAcc b e (acc * b)
Too-special statement (attempted first): `∀ b e, powAcc b e 1 = pow b e`.  Ordinary induction on `e`
gets stuck because the IH is specialized to `acc = 1` while the step needs `acc = b`.

## Sealed known solution (NOT fed to the generator)
    ∀ b e acc, powAcc b e acc = pow b e * acc
i.e. `mul (pow b e) acc`.  New signature: Nat sort; operators {one, mul, pow, powAcc (3-ary)}.
The invariant RHS composes two binary operators (`mul` over `pow`), size 2.

## Load-bearing success criterion (control-parametric transfer)
1. selected policy determined before candidate success is known (frozen selector);
2. selection justified by residual structure (K(ρ₅) = {requiredDepth 2, safeArity 2});
3. differs from baseline when needed (depth 2 + arity cap 2 vs depth 1 uncapped);
4. succeeds where baseline/equal-budget naive search does not;
5. Lean externally verifies.

## Explicit falsifiers
  F1 representation fails (E1); F2 diff/residual fails (E2); F3 grammar fails (C1);
  F4 verifier fails (D); F5 baseline already reaches the invariant (no policy distinction).

## No-change rule
The architecture is frozen.  A clean failure is the result.
