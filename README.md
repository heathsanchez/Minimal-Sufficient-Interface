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

The general theorem is machine-checked in [`lean/BehaviouralCongruence.lean`](lean/BehaviouralCongruence.lean). It proves that `~*` is the greatest reachable-action-invariant observation-compatible equivalence relation: any invariant relation contained in `ker(v)` is contained in `~*`.

Every reachable action descends uniquely to the quotient `X/~*`, and the quotient action preserves identity and composition:

\[
\boxed{\bar 1=\mathrm{id}},
\qquad
\boxed{\overline{gf}=\bar g\circ\bar f}.
\]

In the finite case, given any finite list covering all reachable actions, **any** verifier-driven process that adds a genuine reachable separator whenever one remains reaches the exact behavioural quotient in at most the length of that list. No greedy policy or advance knowledge of the final quotient is assumed.

Thus:

\[
\boxed{\text{MSI refinement computes the maximal observation-compatible behavioural congruence.}}
\]

See [`BEHAVIOURAL_CONGRUENCE.md`](BEHAVIOURAL_CONGRUENCE.md).

## Typed behavioural congruence

The monoid result now lifts to a small category of typed continuations. If `f : X → Y` acts as a typed state transformation and each object has its own protected observation `v_X`, define

\[
\boxed{
x\sim_X y
\iff
\forall Y\;\forall f:X\to Y,
\quad v_Y(f(x))=v_Y(f(y)).
}
\]

The Lean development in [`lean/TypedBehaviouralCongruence.lean`](lean/TypedBehaviouralCongruence.lean) proves that this is the greatest observation-compatible categorical congruence family. Every typed morphism descends uniquely to the objectwise quotient, and the quotient action preserves identities and composition.

Thus the objectwise minimal sufficient interfaces assemble functorially:

\[
\boxed{Q(f)([x])=[f(x)]},
\qquad
\boxed{Q(1_X)=1_{Q(X)}},
\qquad
\boxed{Q(g\circ f)=Q(g)\circ Q(f)}.
\]

See [`TYPED_BEHAVIOURAL_CONGRUENCE.md`](TYPED_BEHAVIOURAL_CONGRUENCE.md).

## Developmental continuation category

The continuation family itself can now grow. A developmental stage is formalized as a composition-closed family of currently accessible morphisms inside a fixed ambient category. For stage `S`, only accessible continuations participate in behavioural identity:

\[
x\sim_X^S y
\iff
\forall f:X\to Y,\quad S(f)\Rightarrow v_Y(f(x))=v_Y(f(y)).
\]

[`lean/DevelopmentalCategory.lean`](lean/DevelopmentalCategory.lean) proves the structural growth law

\[
\boxed{
S\subseteq T
\Longrightarrow
\sim_X^T\subseteq\sim_X^S
\quad\forall X.
}
\]

So expanding the executable continuation subcategory can only refine the interface. If a newly accessible morphism separates a pair merged at the old stage, the new stage must split that pair.

Each stage has its own quotient dynamics; accessible identities and compositions still descend correctly. Moreover, every extension induces a canonical forgetful map from the finer new interface to the coarser old interface:

\[
\boxed{Q_T(X)\to Q_S(X).}
\]

At the ambient stage, the stage-relative equivalence is exactly the full typed behavioural congruence.

This gives the theorem-level structural chain

\[
\boxed{
\text{new morphism}
\to
\text{new protected distinction}
\to
\text{finer behavioural quotient}.
}
\]

See [`DEVELOPMENTAL_CATEGORY.md`](DEVELOPMENTAL_CATEGORY.md).

### Developmental claim boundary

Capability growth must be typed carefully. A finer interface, a larger reachable closure, a cheaper discovery process, and a larger constructor language are not the same event. In particular, an exact finite witness shows that a protected target can become newly reachable after a regime extension even though the later operation was already syntactically formable in the old raw constructor language:

\[
\boxed{
\text{strict reachability growth}
\not\Rightarrow
\text{strict formability growth}.
}
\]

See [`CLOSURE_RELATIVE_CAPABILITY.md`](CLOSURE_RELATIVE_CAPABILITY.md) for the closure-relative capability witness and the resulting claim discipline.

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

The exhaustive census finds **1,872** strict refinements and **220** autonomous post-refinement discovery witnesses.

See [`AUTONOMOUS_DISCOVERY.md`](AUTONOMOUS_DISCOVERY.md) and [`tests/test_autonomous_discovery.py`](tests/test_autonomous_discovery.py).

## Endogenous O1 genesis

The next finite experiment removes the supplied-`O1` assumption too. A verifier-visible residual drives search over the frozen language of all deterministic three-state transformations. Search chooses a candidate only if it repairs the residual through the existing observation and creates generic future capability value. A separate blind search then returns the first newly enabled nonprimitive `O2`.

The exhaustive result is **36** residual worlds and **648** residual-driven `O1` geneses; all 648 realize the full chain

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

See [`ENDOGENOUS_GENESIS.md`](ENDOGENOUS_GENESIS.md) and [`tests/test_endogenous_genesis.py`](tests/test_endogenous_genesis.py).

## Compositional closure

For a finite generator set `G`, let `G*` be the generated transformation monoid. Across all **5,832** three-state/two-generator worlds, the one-step family already induced the full behavioural quotient. At four states with one deterministic generator, exhaustive search over all **4,096** worlds finds **576** worlds requiring composite separators, with zero convergence, congruence, or quotient-composition failures and 576 exact ablation witnesses.

The general Lean theorem now explains the endpoint:

\[
\boxed{E_\infty=\bigcap_{f\in G^*}\ker(v\circ f).}
\]

See [`COMPOSITIONAL_CLOSURE.md`](COMPOSITIONAL_CLOSURE.md) and [`tests/test_compositional_closure.py`](tests/test_compositional_closure.py).

## Counterexample-driven composition discovery

The generated closure and useful composite separators need not be supplied. Starting from primitive actions only, the learner can search words in the primitive language after a verifier exposes a merged pair. In all 4,096 four-state / one-primitive worlds, the 576 worlds that require a proper composite are all recovered with zero failures. In a larger two-primitive branching census over 65,536 worlds, 23,808 require composite discovery and 13,056 require a learned word using both primitive symbols, again with zero recovery or congruence failures.

See [`COUNTEREXAMPLE_COMPOSITION_DISCOVERY.md`](COUNTEREXAMPLE_COMPOSITION_DISCOVERY.md) and [`tests/test_counterexample_composition_discovery.py`](tests/test_counterexample_composition_discovery.py).

## Counterexample-driven constructor law discovery

The next experiment moves uncertainty outward again: the learner is no longer told which binary constructor on actions is the correct one. It begins with a six-law hypothesis family containing sequential composition, reversed composition, left/right projection, and two pointwise alternatives. The verifier supplies only concrete execution counterexamples `(f,g,x,y)`.

Across all **5,832** binary-observation / two-primitive worlds on three states, **4,704** worlds uniquely identify sequential composition, **1,128** remain syntactically ambiguous, and **0** contain harmful ambiguity. Every surviving law in an ambiguous world is extensionally identical to true sequential composition on the reachable subalgebra.

See [`CONSTRUCTOR_LAW_DISCOVERY.md`](CONSTRUCTOR_LAW_DISCOVERY.md) and [`tests/test_constructor_law_discovery.py`](tests/test_constructor_law_discovery.py).

## Grammar-driven constructor genesis

The final finite step removes that hand-written law menu too. The learner receives only the generative syntax

\[
\boxed{t ::= x \mid F(t) \mid G(t)}
\]

and mechanically generates all terms through depth 3. Sequential composition `F(G(x))` is therefore generated rather than supplied as a named candidate.

Exhausting all **729** ordered pairs of deterministic primitive transformations on three states gives:

- **558** worlds with a unique surviving constructor syntax;
- **171** worlds with only operationally equivalent syntactic ambiguity;
- **0** harmful ambiguity;
- **3,626** verifier counterexamples in total, with at most **7** in any world;
- **0** identity-law failures for the retained operation;
- **0** associativity failures.

The deterministic shortest retained term is `F(G(x))` in **728/729** worlds. The sole exception is the trivial reachable algebra, where composition itself is operationally indistinguishable from the identity term.

Thus the finite developmental chain is now closed at the constructor level:

\[
\boxed{
\text{counterexample}
\to
\text{generated constructor}
\to
\text{retained composition}
\to
\text{generated continuations}
\to
\text{behavioural congruence}.
}
\]

See [`CONSTRUCTOR_GENESIS.md`](CONSTRUCTOR_GENESIS.md) and [`tests/test_constructor_genesis.py`](tests/test_constructor_genesis.py).

## Verified interface compilation

The constructor result now compounds across two promotions in a separate
resource-bounded synthesis experiment. Starting from variables and NAND only,
incremental verifier residuals isolate minimum formula representatives for the
two protected half-adder outputs. Retaining those representatives as unit-cost
constructors changes the minimum full-adder formula cost from **20** to **6**;
matched sham and exact-ablation arms remain at 20 under a frozen budget of 6.

The full-adder outputs are then promoted again and recursively composed. Python
exhausts all input pairs at widths 4 and 6, while Lean independently certifies
the half adder, full adder, all 256 four-bit pairs and all 4,096 six-bit pairs.

The gain is correctly typed: `20 → 6` is promoted-constructor description
cost, not fully expanded NAND-gate complexity. It establishes that a verified
behavioural program can be compiled into the constructor language and causally
change a later bounded synthesis frontier.

See [`VERIFIED_INTERFACE_COMPILATION.md`](VERIFIED_INTERFACE_COMPILATION.md),
[`tests/test_verified_interface_compilation.py`](tests/test_verified_interface_compilation.py)
and [`lean/AdderInterfaceCompilation.lean`](lean/AdderInterfaceCompilation.lean).

## Selection above the kernel

The kernel determines lawful refinement and exact stopping, but it does not determine the cheapest next separator. Immediate pair-split gain is cardinality-optimal on all 65,536 binary `4 × 4` worlds tested, but a `5 × 4` counterexample shows it is not a general theorem. Dynamic programming shows that optimal next-step value is residual-relative.

See [`tests/test_selection_layer.py`](tests/test_selection_layer.py).

## Run

```bash
python -m unittest discover -s tests -v
python examples/capability_bridge.py
lean -o lean/Kernel.olean lean/Kernel.lean
LEAN_PATH=lean lean lean/Completeness.lean
LEAN_PATH=lean lean lean/BehaviouralCongruence.lean
LEAN_PATH=lean lean -o lean/TypedBehaviouralCongruence.olean lean/TypedBehaviouralCongruence.lean
LEAN_PATH=lean lean lean/DevelopmentalCategory.lean
LEAN_PATH=lean lean lean/Falsifiers.lean
lean lean/AdderInterfaceCompilation.lean
```

CI runs the exhaustive Python suite, capability bridge, Lean kernel, completeness theorem, monoid behavioural congruence and finite recovery, typed behavioural congruence, developmental continuation-category theorem, falsifiers, and the standalone verified-interface compilation certificate.

## Scope

This repository deliberately isolates the foundation. It does **not** claim that arbitrary intelligence reduces to this kernel, that separators are always cheap to discover, that one silent test proves global sufficiency, that immediate greedy split gain is globally optimal, that every capability acquisition causes a useful refinement, that blind finite search is a sufficient model of general discovery, or that bounded constructor synthesis establishes open-ended natural-world invention.

The finite/theorem-level skeleton is now intentionally complete. The repo establishes a progression from verified distinctions to exact behavioural quotients, functorial quotient dynamics, endogenous capability/continuation discovery, counterexample-driven recovery of operational composition, and grammar-driven synthesis of a composition constructor.

The remaining frontier is no longer another small finite kernel experiment. It is **open-ended generative development**: richer typed grammars, learned object/type formation, transfer across semantically source-distinct tasks, and natural theorem-proving, code-repair, or scientific-intervention spaces. Those layers should sit above the frozen MSI kernel rather than alter it unless a counterexample forces a change.

