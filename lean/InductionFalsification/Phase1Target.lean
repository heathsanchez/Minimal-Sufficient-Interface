/-! # Phase 1 — the exact stuck residual ρ0 (recorded, not left as an unsolved goal)

  Target: `∀ xs, rev (rev xs) = xs` for a FRESH `rev`.  Ordinary structural induction is the
  strongest available proof under the initial representation.  Running Lean on the obvious
  attempt produces the EXACT stuck state (verbatim from `lean`):

      case cons
      α : Type u_1
      x : α
      xs : List α
      ih : rev (rev xs) = xs
      ⊢ rev (rev xs ++ [x]) = x :: xs

  This is ρ0.  The induction hypothesis `rev (rev xs) = xs` is a rule for `rev ∘ rev`; the
  stuck subterm `rev (rev xs ++ [x])` has `rev` applied to an `++`-composite, which the IH
  cannot discharge.  The missing capability is a rule for `rev` over `++`.
-/
