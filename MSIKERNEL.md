# msikernel

`msikernel` is the executable path from the frozen Minimal Sufficient Interface laws to a real checker architecture.

It starts from the MSI kernel rather than from a pre-existing evaluator ontology.

## 1. Frozen foundation

For a carrier `X` and protected continuation family `B`,

\[
E_B = \bigcap_{c\in B} \ker(c).
\]

Developmental refinement is

\[
E_{t+1}=E_t\wedge K_t.
\]

The executable realization in `msikernel/kernel.py` uses finite equivalence relations; `meet_equivalence` is relation intersection.  Nothing in this layer names Lean concepts such as `Sort`, `Pi`, WHNF, closures, or conversion.

## 2. Continuation-relative interfaces

`Continuation` is the executable `c : X -> O_c` boundary.  `induced_equivalence` computes the behavioural quotient using only equality of continuation outcomes.  Outcome names are not ontological.

`CompiledInterface` is an executable quotient representation admitted only when its runtime classes induce exactly the protected future equivalence on the frozen carrier.

The guiding law is:

> represent only the distinctions protected future continuations can observe.

## 3. Development lives above the kernel

The frozen meet kernel does not decide provenance, cost, scope, promotion, transfer, or revocation. `msikernel/development.py` keeps those as explicit above-kernel state.

The first admission ladder is:

`CANDIDATE -> CAUSAL -> ADMITTED`, with `REVOKED` available under counterevidence.

A candidate is not admitted merely because it is extensionally correct. V0 requires a negative measured cost delta, causal ablation, and transfer.

## 4. First Lean-facing realization

`msikernel/lean_bootstrap.py` supplies the first host-domain carrier and continuation family corresponding to the experimentally measured Sort/application/let frontier.

This module is deliberately a bootstrap fixture, not the MSI ontology.  `sort`, `pi`, and related host labels are not primitives of the kernel.

The compiler sees protected continuation outcomes and induces the quotient.  On the frozen carrier the resulting interface separates Sort levels required by future consumers and quotients together states those consumers all route to generic fallback.

The gate checks that compiled decisions are extensionally identical to generic consumer-side rediscovery for every state/continuation pair.

It also counts a narrow operation-level residual:

- LOCAL: classify at every consumer;
- SHARED: classify once and reuse the induced interface;
- ABLATE: construct the interface but ignore it and rediscover locally.

This count is a structural falsifier, not a physical performance claim. Real performance remains the responsibility of the MathGraph/Lean checker experiments.

## 5. Build direction

The intended stack is

\[
\text{MSI kernel}
\to
\text{typed continuations}
\to
\text{verifier-induced types}
\to
\text{compiled interfaces}
\to
\text{economic lowering}
\to
\text{Lean checker realization}.
\]

The existing checker is therefore a behavioural reference and residual fallback, not the ontology that `msikernel` must preserve.

A future interface update has the form

\[
G_{t+1}=
\operatorname{EconomicCompress}
\left(
\operatorname{MinVerifiedExtension}(G_t,\rho_t)
\right).
\]

This equation is an architectural target, not yet a theorem of the frozen kernel.

## 6. V0 gates

V0 requires:

1. executable meet equals intersection of protected future distinctions;
2. independent outcome relabeling leaves the induced interface unchanged;
3. the Lean bootstrap interface is induced from futures rather than supplied class labels;
4. compiled decisions equal generic reference decisions exhaustively on the frozen carrier;
5. shared interface use strictly reduces semantic reclassification operations against LOCAL and ABLATE;
6. a residual in the indiscrete interface is removed by exact future-relative refinement;
7. promotion requires cost, ablation, and transfer, and admitted interfaces remain revocable;
8. the existing MSI finite-kernel and verified-interface-compilation tests still pass;
9. the Lean formal kernel, behavioural congruence, typed behavioural congruence, and developmental category still check.

## 7. Next decisive step

V0 still supplies the Lean host states and continuation functions manually.

The next experiment should remove that scaffold: instrument a real MathGraph checker run to emit anonymous producer states and protected continuation outcomes, then feed those traces into this compiler and ask whether the same useful runtime quotient is induced without naming `Sort` or `Pi` to the interface synthesizer.

Success would establish the stronger chain:

\[
\text{real checker residuals}
\to
\text{anonymous future outcomes}
\to
\text{induced runtime type}
\to
\text{compiled execution}
\to
\text{correctness + ablation + transferred work reduction}.
\]
