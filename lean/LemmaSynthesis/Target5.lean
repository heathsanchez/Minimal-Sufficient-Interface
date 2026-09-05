/-! # Target 5 — the exact stuck residual ρ₅ (recorded, not left as an unsolved goal)

  Pre-registered too-special exponentiation-accumulator theorem: `∀ b e, powAcc b e 1 = pow b e`,
  where `pow b 0 = 1`, `pow b (e+1) = b * pow b e`, `powAcc b 0 acc = acc`,
  `powAcc b (e+1) acc = powAcc b e (acc * b)`.

  Ordinary induction on `e` produces the EXACT stuck state (verbatim from `lean`):

      case succ
      b e : Nat
      ih : powAcc b e 1 = pow b e
      ⊢ powAcc b e b = b * pow b e

  This is ρ₅.  The IH is specialized to `acc = 1`; the step needs `acc = b`.  The sealed repair is
  `∀ b e acc, powAcc b e acc = pow b e * acc`, i.e. `mul (pow b e) acc`.

  The FROZEN selector (frozen at `9d82346`) is applied to the new residual's constraint
  K(ρ₅) = {requiredDepth 2, safeArity 2}; the outcome is recorded in `Target5Result.lean`
  (control-parametric transfer SUCCEEDS).
-/
