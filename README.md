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

## Behavioural congruence theorem

Let a monoid `M` of reachable actions act on `X`, and let `v : X → O` be the protected observation. Define

\[
x\sim_*y
\iff
\forall m\in M,\quad v(m\cdot x)=v(m\cdot y).
\]

The general theorem is now machine-checked in [`lean/BehaviouralCongruence.lean`](lean/BehaviouralCongruence.lean). It proves that `~*` is the greatest reachable-action-invariant observation-compatible equivalence relation: any invariant relation contained in `ker(v)` is contained in `~*`.

Every reachable action descends uniquely to the quotient `X/~*`, and the quotient action preserves identity and composition:

\[
\boxed{\bar 1=\mathrm{id}},
\qquad
\boxed{\overline{gf}=\bar g\circ\bar f}.
\]

In the finite case, given any finite list covering all reachable actions, **any** verifier-driven process that adds a genuine reachable separator whenever one remains reaches the exact behavioural quotient in at most the length of that list. No greedy policy or advance knowledge of the final quotient is assumed.

Thus the theorem-level statement is:

\[
\boxed{\text{MSI refinement computes the maximal observation-compatible behavioural congruence.}}
\]

See [`BEHAVIOURAL_CONGRUENCE.md`](BEHAVIOURAL_CONGRUENCE.md) for the theorem package and scope.

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

## Endogenous O1 genesis

The next experiment removes the supplied-`O1` assumption too.

The current interface exposes a binary observation `v`; a protected binary target `t` is visible only to the verifier. When `v` merges a pair that `t` separates, the verifier returns that pair as a residual witness. Search then ranges over the frozen language of all deterministic three-state transformations and selects a candidate only if it both repairs the residual through the existing observation `v∘h` and creates generic future capability value: at least one transformation becomes newly reachable and quotient-admissible only after the induced refinement. Candidates are ranked by the number of such newly enabled capabilities, with lexicographic tie-breaking. Neither `O1` nor `O2` is supplied by identity.

A separate blind search then returns the first newly enabled nonprimitive `O2`.

The exhaustive result is:

- **36** binary `(v,t)` worlds contain a live verifier residual;
- across those worlds and all 27 primitive generators, **648** residual-driven `O1` geneses satisfy the frozen criterion;
- **all 648** realize the full chain

\[
\boxed{
\text{verifier residual}
\to
\text{endogenous }O_1
\to
\text{separator}
\to
Q_1
\to
\text{expanded closure}
\to
\text{autonomous }O_2.
}
\]

One concrete witness has `v=(0,0,1)`, verifier target `t=(0,1,0)`, primitive `g=(0,0,0)`, residual pair `(0,1)`, synthesized `O1=(1,2,0)`, and discovered `O2=(2,0,1)`. Exact `O1` ablation removes `O2` from the old closure and restores the coarse relation on the residual pair.

See [`ENDOGENOUS_GENESIS.md`](ENDOGENOUS_GENESIS.md) and [`tests/test_endogenous_genesis.py`](tests/test_endogenous_genesis.py). The claim remains bounded: the search uses a finite candidate language and an explicit generic future-capability-value criterion; it does not establish natural-world operator invention.

Together, the finite experiments now realize:

\[
\text{verified failure}
\to
\text{capability search}
\to
\text{new distinction}
\to
\text{changed discoverability}
\to
\text{new capability}.
\]

## Compositional closure

For a finite generator set `G`, let `G*` be the generated transformation monoid. The first proposed universe, `|X|=3` with binary observations and two generators, produced a useful boundary result: across all **5,832** worlds, the one-step family `{id,g0,g1}` already induced the full behavioural quotient. There were **0** necessary composite separators.

At `|X|=4` with one deterministic generator, exhaustive search over all **4,096** worlds finds:

- **576** worlds where `{id,g}` is too coarse relative to `G*`;
- **576** composite separators added by residual-driven refinement;
- **0** convergence failures;
- **0** congruence failures at the final quotient;
- **0** quotient composition-law failures;
- **576** exact ablation witnesses.

In every world the developmental process converges to

\[
\boxed{E_\infty=\bigcap_{f\in G^*}\ker(v\circ f),}
\]

and the final relation is stable under every reachable action. The general Lean theorem above now explains why this endpoint is forced for arbitrary monoid actions under its assumptions.

See [`COMPOSITIONAL_CLOSURE.md`](COMPOSITIONAL_CLOSURE.md) and [`tests/test_compositional_closure.py`](tests/test_compositional_closure.py).

## Selection above the kernel

The kernel determines lawful refinement and exact stopping, but it does not determine the cheapest next separator.

Immediate pair-split gain is cardinality-optimal on all 65,536 binary `4 × 4` worlds tested, but it is not a general theorem. A `5 × 4` counterexample requires three continuations under deterministic greedy choice while a two-continuation sufficient basis exists.

The corresponding dynamic-programming test shows that optimal next-step value is residual-relative: the best continuation is the one minimizing total remaining completion cost, not necessarily the one maximizing immediate split gain. See [`tests/test_selection_layer.py`](tests/test_selection_layer.py).

So the layers separate cleanly:

- **kernel:** what refinements are lawful;
- **completeness:** when refinement may stop;
- **behavioural congruence:** the coarsest observation-compatible identity stable under all reachable futures;
- **selection:** which lawful refinement is cheapest or most useful next;
- **development:** when verified residuals and interface changes alter the reachable/discoverable capability frontier;
- **composition:** which distinctions must survive action contexts so quotient dynamics remain coherent.

## Run

```bash
python -m unittest discover -s tests -v
python examples/capability_bridge.py
lean -o lean/Kernel.olean lean/Kernel.lean
LEAN_PATH=lean lean lean/Completeness.lean
LEAN_PATH=lean lean lean/BehaviouralCongruence.lean
LEAN_PATH=lean lean lean/Falsifiers.lean
```

CI runs the exhaustive Python suite, capability bridge, Lean kernel, completeness theorem, behavioural congruence theorem, finite recovery theorem, and falsifiers together.

## Scope

This repository deliberately isolates the foundation. It does **not** claim that arbitrary intelligence reduces to this kernel, that separators are always cheap to discover, that one silent test proves global sufficiency, that immediate greedy split gain is globally optimal, that every capability acquisition causes a useful refinement, that blind finite search is a sufficient model of general discovery, that bounded endogenous genesis establishes natural-world invention, or that the monoid theorem is already a theorem about arbitrary categories or developmental category growth.

The next open layer is typed/categorical: replace one state space and its endomorphism monoid with multiple objects and typed morphisms, then ask whether object-indexed behavioural quotients assemble functorially—and eventually whether the continuation category itself can grow under verified development.
