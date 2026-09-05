/-! # Target 2 — the exact stuck residual ρ₂ (recorded, not left as an unsolved goal)

  Pre-registered too-special accumulator theorem: `∀ xs, sum_tr xs 0 = sum xs`, where

      sum_tr [] acc       = acc
      sum_tr (x::xs) acc  = sum_tr xs (x + acc)
      sum []       = 0
      sum (x::xs)  = x + sum xs

  Ordinary structural induction on `xs` is the strongest available proof under the initial
  representation.  Running Lean on the obvious attempt produces the EXACT stuck state (verbatim
  from `lean`):

      case cons
      x : Nat
      xs : List Nat
      ih : sum_tr xs 0 = sum xs
      ⊢ sum_tr xs x = x + sum xs

  This is ρ₂.  The induction hypothesis `sum_tr xs 0 = sum xs` is specialized to the initial
  accumulator `acc = 0`; the step needs `sum_tr xs x = x + sum xs`, i.e. an ARBITRARY
  accumulator `x`.  The missing capability is a rule for `sum_tr` at an arbitrary accumulator,
  i.e. a *parameter generalization* (fix `0`, generalize to a universally-quantified `acc`) —
  structurally different from target 1's "rule for `rev` over `++`".

  The frozen generator (commit `64b490a`) is then applied to ρ₂; the result is recorded in
  `Target2Result.lean` (outcome E).
-/
