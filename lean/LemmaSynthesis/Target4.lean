/-! # Target 4 — the exact stuck residual ρ₄ (recorded, not left as an unsolved goal)

  Pre-registered too-special tail-recursive multiplication theorem: `∀ n b, mulTr n b 0 = mul n b`,
  where `mul 0 b = 0`, `mul (n+1) b = b + mul n b`, `mulTr 0 b acc = acc`,
  `mulTr (n+1) b acc = mulTr n b (acc + b)`.

  Ordinary induction on `n` produces the EXACT stuck state (verbatim from `lean`):

      case succ
      b n : Nat
      ih : mulTr n b 0 = mul n b
      ⊢ mulTr n b b = b + mul n b

  This is ρ₄.  The IH is specialized to `acc = 0`; the step needs `acc = b`.  The sealed repair is
  `∀ n b acc, mulTr n b acc = mul n b + acc`, i.e. `add (mul n b) acc`.

  The frozen machinery (frozen at `0dfa251`) is applied to ρ₄; the outcome is recorded in
  `Target4Result.lean` (outcome C2 — prospective prediction at `9f036b0` confirmed).
-/
