# Minimal Sufficient Interface

A tiny relational kernel for justified state distinction under protected continuations.

The seed is

\[
x \sim_B y \iff \forall c\in B,\;P(x,c)=P(y,c).
\]

Two situations are identified exactly while the retained protected continuations cannot distinguish their protected outcomes.

A verified separator forces refinement. Certified sameness requires coverage of the relevant continuation space.

This repository deliberately contains only the foundational semantics, executable reference kernel, exhaustive finite checks, and one capability-interface bridge. MathGraph, Triskelion, theorem proving, code repair, robotics, and developmental-agent architectures are applications, not assumptions.

## Core laws

For situations `X`, protected continuations `C`, outcomes `O`, and `P : X × C → O`:

1. `~_B` is an equivalence relation.
2. If `B ⊆ B'`, then `~_{B'} ⊆ ~_B`.
3. Adding a continuation `c` gives `~_{B∪{c}} = ~_B ∩ ker(P_c)`.
4. A live residual is a currently merged pair separated by some protected continuation.
5. Any separator of a live residual gives strict refinement.
6. With finite `C`, repeated lawful residual repair terminates at `~_C`.
7. Local silence of one continuation does not imply global sufficiency; sufficiency is exactly absence of separators over the covered continuation family.
8. A capability `f : X → X` acts on the quotient `X/~_B` iff it preserves `~_B`.

See [`SPEC.md`](SPEC.md) for formal statements and claim boundaries.

## Run

```bash
python -m unittest discover -s tests -v
python examples/capability_bridge.py
```

The finite tests exhaust all binary protected-outcome tables with `|X|=3, |C|=3`, plus targeted larger counterexamples to stronger claims.

## Scope

This repo does **not** claim that arbitrary open-ended intelligence is captured by the kernel, that separators can always be discovered cheaply, or that lawful repair is cardinality-optimal. It isolates the mathematics that stronger systems may build on.
