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

A verified separator forces strict refinement. Evidence order and duplication do not matter. Finite strict refinement converges. A capability acts on a quotient exactly when it preserves the current equivalence relation.

The exact stopping boundary is formalized in Lean. If the retained basis `B` is covered by protected target family `T`, then absence of any pair merged by `B` but split by `T` is equivalent to extensional sufficiency:

\[
\boxed{\neg\operatorname{Residual}(B,T)\iff E_B=E_T.}
\]

This is deliberately paired with a machine-checked counterexample showing that one locally silent continuation does **not** imply global sufficiency. See [`lean/Completeness.lean`](lean/Completeness.lean) and [`lean/Falsifiers.lean`](lean/Falsifiers.lean).

## Developmental bridge

The repo contains a unified finite causal bridge from capability acquisition to new state distinction to new executable capability:

\[
\boxed{O_1\rightarrow\text{new separator}\rightarrow Q_1\rightarrow\text{new reachable }O_2.}
\]

The exhaustive three-state census searches binary protected observations, deterministic base actions `g`, and deterministic acquired actions `O1`, with derived `O2 = g ∘ O1`. A witness requires all of the following at once: `O2` is absent from the old action closure; `O1` exposes a new protected continuation that strictly refines the interface; `O2` is quotient-inadmissible before but admissible after refinement; `O2` becomes reachable only after adding `O1`; and ablating `O1` restores the old interface and closure.

The census finds 1,944 strict capability-induced interface refinements and 744 full causal witnesses. See [`tests/test_capstone_bridge.py`](tests/test_capstone_bridge.py).

## Autonomous post-refinement discovery

The stronger experiment removes the predefined `O2` from the search procedure.

On the same three-state universe, the candidate language is all 27 deterministic maps `X → X` in one fixed lexicographic order. At each stage, a blind discovery rule returns the first candidate that is reachable from the current executable generators, quotient-admissible under the current interface, and neither identity nor an already supplied primitive. The search order is frozen independently of the world and no target `O2` is named or constructed in advance.

After acquiring `O1`, the executable closure expands and the new protected continuation `v ∘ O1` may refine the interface. A developmental witness is counted only when the unchanged blind search then discovers an emergent nonprimitive `O2` that was outside the old closure, quotient-inadmissible before refinement, quotient-admissible afterward, and lost again under exact `O1` ablation.

The exhaustive census finds:

- **1,872** strict refinements among the nontrivial acquisitions considered;
- **220** autonomous post-refinement discovery witnesses.

Thus the bounded system realizes the stronger chain

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
\text{autonomously discovered }O_2.
}
\]

See [`AUTONOMOUS_DISCOVERY.md`](AUTONOMOUS_DISCOVERY.md) and [`tests/test_autonomous_discovery.py`](tests/test_autonomous_discovery.py). This is a finite exhaustive existence result, not a claim that every acquisition produces useful development or that lexicographic search is itself an intelligent policy.

This gives a concrete bounded realization of the loop:

\[
\text{what can be done}\;\to\;\text{what can be distinguished}\;\to\;\text{what can subsequently be discovered and done}.
\]

## Selection above the kernel

The kernel determines lawful refinement and exact stopping, but it does not determine the cheapest next separator.

Immediate pair-split gain is surprisingly strong in the smallest tested universe: it is cardinality-optimal on all 65,536 binary `4 × 4` worlds. But it is not a general theorem. A `5 × 4` counterexample requires three continuations under deterministic greedy choice while a two-continuation sufficient basis exists.

The corresponding dynamic-programming test shows that optimal next-step value is residual-relative: the best continuation is the one minimizing total remaining completion cost, not necessarily the one maximizing immediate split gain. See [`tests/test_selection_layer.py`](tests/test_selection_layer.py).

So the layers separate cleanly:

- **kernel:** what refinements are lawful;
- **completeness:** when refinement may stop;
- **selection:** which lawful refinement is cheapest or most useful next;
- **development:** when a lawful interface change exposes genuinely new discoverable capability.

## Run

```bash
python -m unittest discover -s tests -v
python examples/capability_bridge.py
lean -o lean/Kernel.olean lean/Kernel.lean
LEAN_PATH=lean lean lean/Completeness.lean
LEAN_PATH=lean lean lean/Falsifiers.lean
```

CI runs the exhaustive Python suite, capability bridge, Lean kernel, Lean completeness theorem, and Lean falsifiers together.

## Scope

This repository deliberately isolates the foundation. It does **not** claim that arbitrary intelligence reduces to this kernel, that separators are always cheap to discover, that one silent test proves global sufficiency, that immediate greedy split gain is globally optimal, that every capability acquisition causes a useful refinement, or that blind finite search is a sufficient model of general discovery. MathGraph, Triskelion, theorem proving, code repair, robotics, and developmental-agent architectures are applications above the kernel, not assumptions inside it.
