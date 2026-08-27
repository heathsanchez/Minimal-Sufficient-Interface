# Minimal Sufficient Interface

A tiny mathematical kernel for justified refinement under protected distinctions.

## Canonical kernel

The frozen core is two equations:

\[
\boxed{E_{t+1}=E_t\wedge K_t}
\]

and, for the state-identification realization,

\[
\boxed{E_B=\bigcap_{c\in B}K_c.}
\]

The first is the abstract refinement law: verified constraints accumulate by an idempotent, commutative, associative meet. The second gives that algebra its intended meaning here: the current interface keeps exactly the sameness that survives every retained protected distinction.

Equivalently, if each protected continuation is represented by an outcome map `c : X → O_c`,

\[
x\,E_B\,y
\iff
\forall c\in B,\;c(x)=c(y).
\]

So two situations remain identified exactly while the retained protected continuations cannot distinguish them.

See [`KERNEL.md`](KERNEL.md) for the canonical snapshot, [`SPEC.md`](SPEC.md) for the full relational development, and [`FINAL_KERNEL.md`](FINAL_KERNEL.md) for the algebraic compression boundary.

## What follows from it

A verified separator forces strict refinement. Evidence order and duplication do not matter. Certified sufficiency requires coverage of the relevant separator space. Finite strict refinement converges. A capability acts on a quotient exactly when it preserves the current equivalence relation.

The repo includes an executable reference implementation, exhaustive finite checks, counterexamples to stronger false claims, and one capability-interface bridge.

## Run

```bash
python -m unittest discover -s tests -v
python examples/capability_bridge.py
```

## Scope

This repository deliberately isolates the foundation. It does **not** claim that arbitrary intelligence reduces to this kernel, that separators are always cheap to discover, that one silent test proves global sufficiency, or that lawful refinement is cardinality-optimal. MathGraph, Triskelion, theorem proving, code repair, robotics, and developmental-agent architectures are applications above the kernel, not assumptions inside it.
