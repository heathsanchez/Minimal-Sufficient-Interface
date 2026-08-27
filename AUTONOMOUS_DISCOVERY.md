# Autonomous post-refinement discovery

The earlier capstone supplied a derived target `O2 = g ∘ O1`. This experiment removes that target from the search procedure.

## Fixed candidate language

Let `X = {0,1,2}`. The candidate language is **all 27 deterministic maps** `h : X → X`, ordered lexicographically once and for all, independently of the current world.

At any interface basis `B` and executable generator family `A`, the discovery rule returns the first candidate `h` in that fixed order such that:

1. `h` is reachable by composition from `A`;
2. `h` preserves the current interface equivalence `E_B`;
3. `h` is neither identity nor one of the supplied primitive generators.

No target `O2` is named, constructed, or scored in advance.

## Developmental intervention

For every binary observation `v`, base action `g`, and acquired action `O1`, acquisition does two things:

- expands the executable generator family from `{g}` to `{g,O1}`;
- exposes the new protected continuation `v ∘ O1`, refining the basis from `{v}` to `{v, v∘O1}` whenever it creates a strict split.

A witness is counted only when the blind discovery rule then returns some `O2` satisfying all of:

- `O2` is outside the old executable closure;
- `O2` is not identity, `g`, or `O1`;
- `O2` was quotient-inadmissible before refinement;
- `O2` is quotient-admissible after refinement;
- `O2` lies in the new executable closure;
- ablating `O1` removes `O2` from the old closure and the old search cannot recover it as the same discovery.

## Exhaustive result

The full three-state census found:

- **1,872** strict refinements among nontrivial acquisitions considered by this experiment;
- **220** autonomous post-refinement discovery witnesses.

One witness is:

- protected observation `v = (0,0,1)`;
- old generator `g = (0,0,0)`;
- acquired primitive `O1 = (2,0,0)`;
- blindly discovered emergent map `O2 = (0,2,2)`;
- old search result after ablation: `None`.

Thus, within this frozen bounded language, the stronger causal chain exists:

\[
\boxed{
O_1
\to
\text{new protected separator}
\to
Q_1
\to
\text{expanded executable closure}
\to
\text{autonomously discovered } O_2
}
\]

The key distinction from the previous capstone is that `O2` is selected by a fixed target-free search rule rather than defined from `O1` ahead of time.

## Claim boundary

This is a finite exhaustive existence result, not a theorem that every acquisition yields useful discovery and not evidence that lexicographic search is an intelligent policy. The candidate language is deliberately tiny and complete on three states. The result establishes that interface refinement can causally make a previously illegal and unreachable nonprimitive capability both executable and discoverable under an unchanged blind search procedure.

See `tests/test_autonomous_discovery.py` for the exact census.
