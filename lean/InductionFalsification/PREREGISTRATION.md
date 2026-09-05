# External Falsification Test 1 — Induction Generalization (pre-registration)

Frozen kernel: the 13-rung developmental policy (residual → constraint → version space →
minimal certified update → next world), as externally kernel-verified through run
`33956345684` (commit `d231608`).  The kernel's developmental policy is FROZEN for this test:
no target-specific rule, no "induction generalization" constructor, no injection of the known
lemma.  Adapters presenting Lean proof states to the frozen policy must be target-neutral.

## 1. Starting theorem
  ∀ (xs : List α), rev (rev xs) = xs
where `rev` is a FRESH definition (below), isolated from `List.reverse` so no pre-existing
`rev_rev` theorem in Std can discharge it.

## 2. Permitted initial representation
  - The one-variable proposition `rev (rev xs) = xs`.
  - Ordinary structural induction on `xs`.
  - No append-generalized statement, no auxiliary lemma.

## 3. Allowed generic operators (declared BEFORE inspecting the solution)
  - abstract a subterm into a fresh variable;
  - universally quantify a fresh variable (generalize a constant/subterm);
  - form an equality between expressions built from already-present operators;
  - structural induction on an existing quantified variable;
  - rewrite with an existing (already-proven) lemma.
  These are generic lemma-synthesis operators, not target-specific constructors.
  Forbidden: a constructor named `reverse_append`, `generalize_over_suffix`, or any operator
  introduced specifically because of this target.

## 4. Verifier
  Lean 4 (the repository's `lean` + `LEAN_PATH=lean` toolchain).  A candidate repair is valid
  only if Lean accepts it with zero `sorry`/`axiom`.

## 5. Resource bound
  Candidate generation bounded to the generic operators above; search limited to a small
  finite set of syntheses (no unbounded enumeration).  Record the number of candidates.

## 6. Success criteria
  - A candidate lemma is generated from K(ρ0) (the stuck-state constraint), not supplied;
  - Lean proves it independently (zero sorry);
  - it discharges the stuck induction step ρ0;
  - it proves the original target `rev (rev xs) = xs`;
  - it transfers to held-out nearby obligations (below).

## 7. Failure criteria
  - no candidate within budget proves the target; OR
  - the only "success" is a target-specific patch injected after seeing the answer; OR
  - a depth/tag-style observation that distinguishes proof states but discharges no Lean goal.

## 8. Held-out solution (SEALED — not to be fed to the kernel)
  The textbook repair is the two-variable append/reverse lemma:
      rev (xs ++ ys) = rev ys ++ rev xs
  and/or the singleton-suffix special case:
      rev (xs ++ [x]) = x :: rev xs
  Either is acceptable as a *held-out* benchmark, but neither is given to the kernel.  A
  singleton-suffix lemma may be the minimal sufficient repair; the held-out transfer test is
  the discriminator between a minimal patch and a representation change.

## 9. Held-out transfer obligations (fixed before inspecting the selected repair)
  T1: rev over a non-singleton suffix: rev (rev (xs ++ [a, b])) = a :: b :: xs  (or equivalent
      requiring the two-variable form).
  T2: a second list theorem whose induction step requires a generalization beyond the
      one-variable hypothesis (selected independently).
  These are fixed here, before the kernel runs.

## 10. Ablation
  Run an equal-budget undirected lemma enumeration (generic operators, no residual guidance)
  and compare: candidate count, Lean rejections, number proving the target, transfer survival.
  Residual guidance is meaningful only if it materially reduces search or improves transfer.
