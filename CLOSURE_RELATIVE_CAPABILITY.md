# Closure-relative capability and developmental claim boundaries

A developmental gain must be typed carefully. Three changes that can look similar operationally are mathematically distinct:

\[
\boxed{
\text{representation refinement}
\neq
\text{reachability growth}
\neq
\text{constructor-language growth}.
}
\]

This note records an exact finite base case for the middle distinction.

## Four different objects

In a finite rewrite system, distinguish:

1. a literal rewrite program;
2. a rewrite class modulo transformations already available in the current regime;
3. reachability under the currently retained transition regime;
4. syntactic formability in the raw constructor language.

These should not be identified.

Consider four token coordinates with the cyclic group `C₄` acting by coordinate transport. A one-site rewrite is identified with another when the old cyclic symmetry transports its coordinate while preserving its source and destination tokens. Two coordinate-distinct `LT → LE` rewrites therefore belong to one closure-relative capability class.

For the protected source

```text
(A, LT, B, AND)
```

and target

```text
(A, LE, B, OR)
```

the target is unreachable when the retained regime contains the transported `LT → LE` capability but no `AND → OR` capability. After adjoining the transported `AND → OR` class, the target becomes reachable by reusing `LT → LE` and then applying `AND → OR`.

Thus, for regimes `S₁ ⊂ S₂`,

\[
\boxed{
\operatorname{Reach}_{S_1}(x)
\subsetneq
\operatorname{Reach}_{S_2}(x).
}
\]

But the later `AND → OR` rewrite was already a literal member of the raw one-site constructor language before the regime extension. Hence the same witness satisfies

\[
\boxed{
\operatorname{Form}(L_1)=\operatorname{Form}(L_2)
}
\]

for the relevant raw constructor language.

Therefore

\[
\boxed{
\text{strict reachability growth}
\not\Rightarrow
\text{strict formability growth}.
}
\]

The converse identification is equally unsafe: the existence of a syntactically formable operation does not imply that it is currently installed, reachable, selectable, or available under the retained developmental regime.

## Relation to MSI

MSI identifies states relative to protected verified futures. At developmental stage `S`,

\[
x\sim_X^S y
\iff
\forall Y\;\forall f:X\to Y,
\quad
S(f)\Rightarrow v_Y(f(x))=v_Y(f(y)).
\]

If `T` extends `S`, the developmental-category theorem gives

\[
S\subseteq T
\Longrightarrow
\sim_X^T\subseteq\sim_X^S.
\]

So new accessible continuations can force a finer representation. The finite witness above supplies an orthogonal boundary: an increase in accessible or reachable capability need not mean that the host constructor language itself has become more expressive.

The developmental vocabulary should therefore distinguish at least:

- **interface gain** — protected futures force a finer quotient;
- **reachability gain** — a target enters the closure of the installed regime;
- **discovery gain** — a fixed bounded search can now find a capability it previously could not find;
- **formability gain** — the admissible constructor language can now express something it previously could not express;
- **policy gain** — retained developmental evidence changes how later distinctions or constructions are sought.

These claims require different controls and should not be promoted into one another.

## Claim discipline

A useful causal test for reachability growth is

\[
K\notin\operatorname{Reach}(S_t),
\qquad
K\in\operatorname{Reach}(S_t+\Delta),
\]

with exact ablation of `Δ` restoring failure.

That does **not** establish constructor-language growth. For that stronger claim one must additionally show

\[
K\notin\operatorname{Form}(L_t),
\qquad
K\in\operatorname{Form}(L_{t+1}),
\]

under a frozen and explicit formability boundary.

Likewise, reduced search cost under a fixed language is evidence of discovery or policy improvement, not automatically of new formability.

## Why this belongs in the kernel boundary

The distinction prevents a common category error in developmental systems: treating every new verified capability as an invented primitive.

A system may:

- distinguish more without gaining a new constructor;
- reach more without becoming able to express more;
- discover more under a fixed language because its retained interface or policy changed;
- or genuinely enlarge the language of formable constructions.

Those are different developmental events.

The MSI kernel should remain neutral between them and record which boundary was actually crossed.

\[
\boxed{
\textbf{A developmental gain is meaningful only relative to the boundary that changed.}
}
\]

This finite closure-relative witness is therefore a base-case falsifier for any inference of the form

\[
\text{newly reachable}\Rightarrow\text{newly formable}.
\]

It establishes the separation cleanly while leaving the stronger problem — endogenous, verifier-justified growth of the constructor language itself — open.