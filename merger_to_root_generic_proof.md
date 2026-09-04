# merger→root : generic finite-functional-graph theorem

**Status: HAND PROOF — awaiting Lean kernel certification.** Do not cite as
kernel-verified. Z3 evidence below is BOUNDED (n=2..6), not generic.

## Statement (generic)

For every finite nonempty set `S` and total function `τ : S → S`:

    (∃ y ∈ S, indegree_τ(y) ≥ 2)  →  (∃ z ∈ S, indegree_τ(z) = 0),

where `indegree_τ(y) := |{ x ∈ S : τ(x) = y }| = |τ⁻¹(y)|`.

## Proof

1. **Fiber partition.** The preimage sets `τ⁻¹(y) = {x : τ(x) = y}` for `y ∈ S`
   form a partition of `S`: they are pairwise disjoint (an `x` cannot map to two
   distinct `y`), and they cover `S` (every `x` lies in `τ⁻¹(τ(x))`).

2. **Indegree-count identity.** Summing the cardinalities of the parts of a
   partition of `S` gives `|S|`:

        Σ_{y ∈ S} |τ⁻¹(y)|  =  |S|.

   (This is the exact statement of mathlib's
   `Finset.card_eq_sum_card_fiberwise` / `Fintype.card_congr`-adjacent
   fiber-cardinality lemma, applied to the function `τ` over the Fintype `S`.)

3. **Contradiction.** Assume every `z ∈ S` has `indegree(z) ≥ 1`, and some
   `y₀ ∈ S` has `indegree(y₀) ≥ 2`. Then

        Σ_{y ∈ S} indegree(y)
          = indegree(y₀) + Σ_{y ≠ y₀} indegree(y)
          ≥ 2 + Σ_{y ≠ y₀} 1
          = 2 + (|S| − 1)
          = |S| + 1.

   By (2), the sum equals `|S|`. Hence `|S| ≥ |S| + 1`, impossible.

4. **Conclusion.** Some `z ∈ S` has `indegree(z) = 0`. ∎

## Evidence boundary

| Evidence | Scope | Classification |
|---|---|---|
| `merger_to_root_certificate.py` (Z3) | n = 2..6, exhaustively | BOUNDED |
| the proof above (indegree-count identity) | all finite `S` | HAND PROOF, kernel-certification pending |

The hand proof is elementary (a partition/counting identity) and the intended
kernel witness is a single mathlib fiber-cardinality lemma; but per programme
standard it is **not** promoted to a generic theorem until a Lean (or
equivalent) kernel accepts it over an arbitrary `[Fintype S] [Nonempty S]`.

## Concrete instantiation (E677 mixed route)

In the mixed collision fibre, `S` is the finite τ-state set (pairs of magma
elements), `τ` is the tau map `τ(r,w) = (r·w, (r·w)\w)`, and the merger is the
state `(b,h)` with `indegree = N(u,b) = n ≥ 3 > 1`. The theorem then certifies
the existence of an indegree-0 root, but only once the generic statement above
is kernel-accepted.
