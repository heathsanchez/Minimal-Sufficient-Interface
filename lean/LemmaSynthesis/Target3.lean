/-! # Target 3 — the exact stuck residual ρ₃ (recorded, not left as an unsolved goal)

  Pre-registered too-special tree-flatten accumulator theorem: `∀ t, flattenAcc t [] = flatten t`,
  where `Tree = leaf Nat | node Tree Tree`, `flatten (leaf x) = [x]`, `flatten (node l r) =
  flatten l ++ flatten r`, `flattenAcc (leaf x) acc = x :: acc`, `flattenAcc (node l r) acc =
  flattenAcc l (flattenAcc r acc)`.

  Ordinary structural induction on `t` is the strongest available proof under the initial
  representation.  Running Lean on the obvious attempt produces the EXACT stuck state (verbatim
  from `lean`):

      case node
      l r : Tree
      ihl : flattenAcc l [] = flatten l
      ihr : flattenAcc r [] = flatten r
      ⊢ flattenAcc l (flattenAcc r []) = flatten l ++ flatten r

  This is ρ₃.  The induction hypotheses are specialized to `acc = []`; the `node` step threads a
  non-`[]` accumulator (`flattenAcc r []`, i.e. `flatten r`) through TWO recursive calls.  The
  missing capability is a rule for `flattenAcc` at an arbitrary accumulator — parameter
  generalization (`[] ↦ acc`), plus a strengthened RHS `flatten t ++ acc` whose proof needs `++`
  associativity.

  The frozen signature-generic machinery (frozen at `d54c07b`) is applied to ρ₃; the outcome is
  recorded in `Target3Result.lean` (outcome C1).
-/
