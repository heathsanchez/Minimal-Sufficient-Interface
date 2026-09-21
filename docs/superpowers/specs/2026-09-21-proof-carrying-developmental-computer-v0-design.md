# Proof-Carrying Developmental Computer V0 — Design Specification

**Status:** Draft for user review  
**Repository:** \`heathsanchez/Minimal-Sufficient-Interface\`  
**Feature branch:** \`proof-carrying-developmental-computer-v0\`  
**Base commit:** \`900a73c1d386ee0eee1205a1cf31d270f3311ef7\`  
**Primary aim:** integrate the strongest established programme results into one minimal executable developmental architecture whose growth and compression are constrained by proof.

## 1. Constitutional principle

The V0 constitution is:

\[
\boxed{
\textbf{Never add structure merely because it is imaginable.
Add it only when the current system is certified insufficient.}
}
\]

The intended product is:

\[
\boxed{\textbf{a proof-carrying developmental computer}}
\]

whose representation, executable vocabulary, and active memory may grow when forced, contract when safe, and retain only what can still matter under the declared protected future.

The machine is not defined by any one current project name. QCK, CLC, Flash, RealityGraph, .mg, DIR, and the Nucleus programme are treated as discovered mechanisms or theorem packages that may become derived layers of the integrated system.

## 2. Ground zero: directed generators, not a prebuilt ontology

Literal assumption-free computation is impossible. V0 therefore begins from one explicit generative hypothesis:

\[
\mathcal N=(R,\Delta).
\]

Interpret this as quiver data:

\[
G=(V,E,s,t),
\]

where:

- \(V\) are explicit references;
- \(E\) are directed distinctions;
- \(s,t:E\to V\) give endpoint incidence.

No initial claim is made that a reference is an object, proposition, theorem, state, person, or program.

No primitive assumption is made that:

- arrows compose;
- identities exist;
- associativity is a separate law;
- a global type ontology exists;
- persistent objects exist;
- every vertex is recoverable from edge incidence.

The safe foundational statement is:

\[
\boxed{
\text{Reference + Directed Difference}
=
\text{underlying directed generating quiver}.
}
\]

This remains a generative hypothesis, not a theorem that reality has one uniquely correct ontology.

## 3. Free completion supplies compositional consequence

Once the generating quiver exists, compositional structure should not be separately designed.

Use the free category:

\[
\boxed{
G\longmapsto F(G).
}
\]

Finite directed paths are morphisms.

- empty path gives identity;
- path concatenation gives composition;
- associativity follows from concatenation.

Thus the machine should not privilege “compose” as a separately invented ontology item when free completion already supplies it canonically.

The active Nucleus theorem programme is intended to formalize this layer. V0 of this integration spec depends only on the mathematical contract and must not claim that the still-active Nucleus branch has already qualified until its own workflow is green.

## 4. The development rule: free extension, then warranted quotient

The earlier rule

\[
L_{t+1}
=
\operatorname{MinimumVerifiedRepair}(L_t,\rho_t)
\]

is refined into:

\[
\boxed{
L_{t+1}
=
\operatorname{WarrantedQuotient}_{\Omega_t}
\left(
\operatorname{FreeExtend}(L_t,\rho_t)
\right).
}
\]

Here \(\rho_t\) is an exact residual or obstruction demonstrating that the current language cannot adequately express, distinguish, or execute a required protected consequence.

The developmental cycle is therefore:

\[
\boxed{
\text{exact obstruction}
\to
\text{least free extension}
\to
\text{verification}
\to
\text{greatest safe quotient}
\to
\text{compiled executable form}.
}
\]

This is the primary architectural change from earlier versions of the programme.

Universal minimality is preferred over an arbitrary scalar cost objective whenever a universal construction is available.

Operational cost still matters when choosing among concrete implementations of the same abstract extension.

## 5. Residuals earn generators; warrant earns relations

The constitution has two independent admission rules.

### 5.1 Generator admission

A new generator is admitted only when an exact certified residual demonstrates insufficiency of the current generated structure.

\[
\boxed{
\rho
\Rightarrow
\text{candidate generator}
\Rightarrow
\text{verified free extension}.
}
\]

### 5.2 Relation admission

A new equation or identification is admitted only when external warrant establishes that the distinction cannot affect protected consequence.

\[
\boxed{
\Omega
\Rightarrow
p\approx_\Omega q
\Rightarrow
\text{warranted quotient}.
}
\]

The corresponding constitutional rule is:

\[
\boxed{
\textbf{Never store an equation merely because it is convenient.
Relations must be earned by warrant just as generators are earned by residuals.}
}
\]

V0 must keep distinct:

\[
\operatorname{GeneratedCongruence}(\Omega_{\rm earned})
\]

and the full semantic behavioural congruence

\[
\approx_{\rm beh}.
\]

The equality

\[
\operatorname{GeneratedCongruence}(\Omega_{\rm earned})
=
\approx_{\rm beh}
\]

is a stronger completeness theorem and is not assumed by this integration design.

## 6. Search exhaustion is not structural insufficiency

The machine must distinguish:

\[
\boxed{\text{search stopped}\neq\text{language insufficient}.}
\]

Structural growth may be triggered only by a complete or otherwise accepted no-resolution certificate under the frozen search/verifier contract.

An execution failure due merely to:

- timeout;
- heuristic exhaustion;
- budget exhaustion;
- unavailable compute;
- implementation error;

must not silently become a language-growth certificate.

If multiple minimal repairs remain unresolved under the declared order, the machine returns:

\[
\boxed{\texttt{UNKNOWN\_CHOICE}}
\]

rather than inventing a narrative of inevitability.

## 7. “Forced” has an exact technical meaning

A developmental extension \(e\) is **forced relative to contract \(C\)** only when:

1. the current structure is certified inadequate under \(C\);
2. \(e\) resolves the certified obstruction;
3. \(e\) passes the independent verifier;
4. \(e\) is universal/minimal under the declared structural order, or is the unique minimum admissible concrete implementation under the declared implementation order;
5. no unresolved tie remains.

Two levels are distinguished:

### Structural forcing

\[
\rho
\Rightarrow
\operatorname{FreeExtend}(L,\rho)
\]

when the residual determines the universal attachment type.

### Implementation selection

Among concrete realizations of the same structural extension, cost, runtime, trusted-base size, or other frozen criteria may select an implementation.

Do not conflate these.

## 8. Immutable history and active consequential form

The system has two fundamentally different stores.

### 8.1 Immutable certified lineage

Call it \(\Gamma_t\).

It contains append-only or explicitly superseding records of:

\[
\Gamma_t=
\text{events}
+\text{certificates}
+\text{dependencies}
+\text{authority snapshots}
+\text{revocations}
+\text{provenance}
+\text{promotion lineage}.
\]

Historical events are never silently rewritten merely because the active representation changes.

### 8.2 Active consequential world

Call it \(M_t\).

\[
\boxed{
M_t=\Pi_{Q_t,\Omega_t}(\Gamma_t).
}
\]

It contains the smallest currently warranted operational representation needed for:

- protected queries;
- executable capabilities;
- current support;
- active repair rules;
- the current quotient/presentation.

The governing architecture is:

\[
\boxed{\textbf{remember deep; execute shallow}.}
\]

Historical lineage may be large.

Active state should be as small as safely possible.

## 9. Current state of the machine

The integrated developmental machine is modeled conceptually as:

\[
\boxed{
\mathcal S_t=
(\Gamma_t,P_t,M_t,\Omega_t,L_t).
}
\]

Where:

- \(\Gamma_t\): immutable certified lineage/evidence graph;
- \(P_t\): current warranted presentation of generators and relations;
- \(M_t\): active minimum sufficient memory/projection;
- \(\Omega_t\): authority/verifier snapshot;
- \(L_t\): current executable capability language.

\(P_t\) need not necessarily be a separate serialized runtime object if \(L_t\) and \(M_t\) encode it faithfully, but it is mathematically explicit because development changes both generators and equations.

## 10. Generated capability and active language are not the same thing

Do not assert:

\[
L_0\subseteq L_1\subseteq L_2\subseteq\cdots
\]

for the active executable language.

Instead distinguish:

\[
G_t=\text{accumulated generated capability structure}
\]

from:

\[
L_t=\text{current executable presentation}.
\]

Generated structure may grow monotonically:

\[
G_0\to G_1\to G_2\to\cdots
\]

while the active language may:

- gain instructions;
- collapse equivalent instructions;
- change representation;
- revoke capabilities;
- split/refine after a new query;
- recompile into a smaller equivalent form.

Thus:

\[
\boxed{
\text{deep capability accumulation}
\neq
\text{monotone active syntax growth}.
}
\]

## 11. Tiny trusted operation family

The V0 runtime should expose the smallest practical trusted operation family:

\[
\boxed{
\operatorname{Observe},
\operatorname{Execute},
\operatorname{Verify},
\operatorname{Promote},
\operatorname{Revoke},
\operatorname{Project}.
}
\]

Other operations should be derived where possible.

- **Grow** derives from \(\operatorname{Promote}\) plus free completion.
- **Dissolve** derives from \(\operatorname{Project}\) plus warranted congruence.
- **Regrow** derives from a newly certified distinction that invalidates a prior active quotient.
- **Reclose** derives from dependency propagation over newly verified consequence.

A program execution returns more than a value:

\[
\boxed{
(\mathcal S,P)
\longrightarrow
(\mathcal S',v,\kappa,\rho).
}
\]

Where:

- \(v\): result;
- \(\kappa\): certificate/warrant;
- \(\rho\): unresolved residual/obstruction;
- \(\mathcal S'\): resulting developmental state.

## 12. Capability promotion: the language learns instructions

A verified reusable program \(c\) may be promoted into the operational vocabulary:

\[
\operatorname{verify}(c)
\Rightarrow
\operatorname{promote}(c)
\Rightarrow
c\in G_{t+1}.
\]

The promoted capability may execute through a compiled shallow form while preserving a transparent expansion or certified lineage back to its trusted substrate.

The design target is:

\[
\boxed{
\text{deep proof lineage}
+
\text{shallow executable call}.
}
\]

This preserves the main lesson of the DIR/Whakapapa experiments: long genealogical warrant can be useful even when long genealogical execution is inefficient.

## 13. Query-relative compression and regrowth

No generic similarity-based merge is permitted.

Let \(Q_t\) be the declared protected query language.

Then:

\[
x\sim_{Q_t,\Omega_t}y
\]

only when every required accepted future observation agrees.

At the path level:

\[
p\approx_{Q_t,\Omega_t}q
\]

only when every accepted continuation preserves protected observational equality.

The active representation may therefore be:

\[
M_t=X_t/{\sim_{Q_t,\Omega_t}}
\]

or a corresponding generated presentation/quotient.

If the protected language expands:

\[
Q_t\subsetneq Q_{t+1},
\]

an old equivalence class may split.

This is not considered failure.

It is lawful regrowth:

\[
\boxed{
\text{compress while safe;
restore distinction when newly consequential}.
}
\]

## 14. Nonlinear lineage, support, revocation, and reclosure

CLC and Flash remain applicable as higher-level mechanisms because the active developmental graph is not generally a single linear chain.

The integrated system must support:

- one-to-many development;
- many-to-one recombination;
- many-to-many restructuring;
- alternative support;
- conjunctive support;
- dormant alternatives;
- revocation of live authority;
- system-wide dependent reclosure.

The active representation may dissolve node distinctions only when the declared protected consequences remain preserved under the relevant compatible futures.

The already qualified CLC V0 theorem is an existing formal dependency for this principle.

## 15. Every abstraction carries a falsifier

Every promoted structural concept must have:

\[
\boxed{
\text{positive theorem}
+
\text{negative fixture}
+
\text{ablation}.
}
\]

Examples:

- continuation safety: future-separation fixture;
- path-preserving quotient: spurious quotient-path fixture;
- whole-boundary factorization: joint consequence that componentwise tests cannot recover;
- capability promotion: remove promoted capability and recover cold-search cost/frontier;
- meta-rule reuse: structurally wrong obstruction or authority snapshot must reject reuse;
- warranted relation: remove the warrant and the quotient relation must no longer be accepted;
- fresh generator: ambient-arrow control must fail where only true fresh attachment can express the residual.

An abstraction without a falsifier is not promoted into the constitutional core.

## 16. Convergence is external residual reduction

The system must not declare convergence merely because its internal models agree.

Convergence is evaluated against independent protected tests and frozen external contracts.

Preferred signals include:

\[
\begin{aligned}
&\text{fewer unresolved protected cases},\\
&\text{lower verified executable cost},\\
&\text{smaller active state},\\
&\text{greater held-out reuse},\\
&\text{more exact prediction},\\
&\text{survival under adversarial perturbation},\\
&\text{successful independent verifier checks}.
\end{aligned}
\]

Conceptually:

\[
\boxed{
\rho_{t+1}<\rho_t
}
\]

under a declared residual order.

A more elegant internal story is not itself evidence of progress.

## 17. Lean defines the laws; runtime implementation is replaceable

The trusted mathematical boundary is:

\[
\boxed{
\text{Lean reference semantics}
\leftrightarrow
\text{portable executable runtime}.
}
\]

Lean should define and prove:

- free generation laws;
- warranted quotient laws;
- transport laws;
- lineage/support laws;
- revocation laws;
- reclosure laws;
- promotion/expansion equivalence;
- protected query preservation.

The production runtime should be replaceable.

Python remains useful for synthesis and experimentation.

A lower-level implementation such as Rust is a plausible later production target, but V0 does not commit the project to a runtime language before the reference semantics are fixed.

Every production runtime must pass differential tests of the form:

\[
\operatorname{run}_{Lean}(x)
=
\operatorname{run}_{runtime}(x)
\]

over exhaustive small worlds and fuzzed larger worlds.

## 18. V0 is one complete developmental loop

V0 must be brutally small.

It must not attempt to implement the entire research programme.

The first integrated executable capstone must perform one complete loop without hidden generation-specific dispatch:

\[
\boxed{
\begin{aligned}
&\text{frozen tiny substrate}\\
&\to\text{provably insufficient task}\\
&\to\text{exact obstruction}\\
&\to\text{fresh/free extension}\\
&\to\text{independent verification}\\
&\to\text{promotion}\\
&\to\text{reuse}\\
&\to\text{serialization}\\
&\to\text{restart}\\
&\to\text{warranted compression}\\
&\to\text{same protected answer}\\
&\to\text{new protected query}\\
&\to\text{regrowth/refinement}.
\end{aligned}
}
\]

This single lifecycle is more important than accumulating another collection of isolated theorem packages.

## 19. Integrated capstone statements

The first preservation target is:

\[
\boxed{
\operatorname{Eval}_{\Gamma}
(Q,\operatorname{Develop}(\Gamma,T))
=
\operatorname{Eval}_{M}
(Q,\operatorname{Develop}(M,\Pi(T)))
}
\]

for every \(Q\) in the declared protected language and every certified compatible finite trace \(T\).

Compilation must be included.

For a promoted capability \(c\):

\[
\boxed{
\operatorname{expand}(\operatorname{compiled}(c))
\equiv c.
}
\]

The end-to-end target is:

\[
\boxed{
\operatorname{Eval}_{full}
=
\operatorname{Eval}_{compiled+quotiented}
}
\]

before and after:

- promotion;
- restart;
- revocation;
- nonlinear growth;
- quotient dissolution;
- regrowth.

The exact theorem statement must be specialized to the finite V0 fixture rather than asserted universally.

## 20. First serious external domains

The first external wedges should use hard independent verifiers.

Preferred domains:

\[
\boxed{\text{formal mathematics}}
\qquad
\boxed{\text{software/code transformation}}.
\]

For formal mathematics:

\[
\text{solve}
\to
\text{kernel verify}
\to
\text{compile verified proof pattern}
\to
\text{reuse}.
\]

For code transformation:

\[
\text{repair}
\to
\text{test/formal verify}
\to
\text{compile transformation capability}
\to
\text{reuse}.
\]

These are preferred over weakly verifiable domains because they let the programme measure whether development genuinely improves capability without relying on subjective interpretation.

## 21. Repository architecture

The long-term integration target is one repository rather than a growing constellation.

Proposed eventual layout:

\`\`\`text
spec/
  CONSTITUTION.md
  CLAIM_BOUNDARY.md

formal/Metalogic/
  Quiver.lean
  Free.lean
  Warrant.lean
  Congruence.lean
  Nucleus.lean
  Residual.lean
  Quotient.lean
  Transport.lean
  Lineage.lean
  Support.lean
  Flash.lean
  Growth.lean
  Runtime.lean

runtime/
  core/
  verifier/
  executor/
  compiler/
  memory/

language/
  ast/
  parser/
  repl/
  stdlib/

memory/
  mg/

fixtures/
  future-separation/
  spurious-path/
  factorisation/
  revocation/
  ablation/

benchmarks/
  boolean/
  finite-state/
  lean/
  coding/

evidence/
  manifests/
  qualified-runs/
  hashes/
\`\`\`

Existing projects are imported or frozen by exact source hash where they become dependencies.

Historical repositories are not rewritten to make the final architecture look cleaner than the actual development path.

## 22. Dependency status

### Qualified dependency

CLC Nonlinear Lineage V0:

- branch: \`clc-nonlinear-lineage-v0\`;
- qualified head: \`900a73c1d386ee0eee1205a1cf31d270f3311ef7\`;
- capstone: \`grow_dissolve_preserves_protected_queries\`.

### Existing formal dependencies

The existing repository also contains:

- \`TypedBehaviouralCongruence.lean\`;
- \`DevelopmentalCategory.lean\`;
- \`GeneratedStage.lean\`;
- \`MinimalRepair.lean\`.

These theorem packages are reused by exact source rather than re-described as newly proved results.

### Pending dependency

Nucleus Universal Property V0 is under active development on:

\`nucleus-universal-property-v0\`.

This integration specification treats its universal-property contract as an intended dependency but does not claim it is qualified until its own final gate passes.

## 23. Claim boundary

Passing this integrated V0 would support the bounded statement:

> A finite proof-carrying developmental computer can begin from a small directed generating substrate, use an exact certified residual to justify a minimal free extension, verify and promote the resulting capability, retain its lineage, execute through a compiled shallow form, quotient away distinctions irrelevant to a declared protected future, survive serialization/restart and revocation, and lawfully regrow when a later protected query exposes a distinction that the prior active quotient had hidden.

It would not establish:

- unrestricted self-improvement;
- arbitrary real-world ontology discovery;
- completeness of locally earned equations for full behavioural equivalence;
- universal existence of a unique useful repair;
- automatic discovery of the correct residual endpoints;
- infinite/open-ended productivity;
- metaphysical claims about identity or consciousness;
- that all useful abstractions arise from category theory;
- that one runtime implementation is canonical.

## 24. Deferred theorem programmes

The following are explicitly outside integrated V0:

### Earned-equation completeness

\[
\boxed{
\texttt{generatedCongruence\_eq\_pathBehEq}
}
\]

or equivalently:

\[
\operatorname{GeneratedCongruence}(\Omega_{\rm earned})
=
\approx_{\rm beh}.
\]

### Lyapunov bridge

\[
\boxed{
\texttt{residualAdjoin\_strictLyapunov}
}
\]

showing that a genuinely separating fresh residual extension causes strict descent of the already mechanized developmental potential under the stated hypotheses.

### Higher attachment

- new-object attachment;
- multiple simultaneous generators;
- computads/polygraphs;
- higher categorical cells.

These are V1+ and must not widen V0.

## 25. Build principle

The canonical constitution for the integrated programme is:

\[
\boxed{
\begin{gathered}
\textbf{Start with the weakest executable distinction.}\\
\textbf{Let exact failure force every generator enlargement.}\\
\textbf{Let warrant earn every relation.}\\
\textbf{Promote only independently verified consequence.}\\
\textbf{Preserve every distinction a lawful future can still expose.}\\
\textbf{Collapse everything else.}\\
\textbf{Keep history for warrant, not for execution.}\\
\textbf{Let new consequence reclose the active present globally.}\\
\textbf{When compression becomes insufficient, regrow—not guess.}
\end{gathered}
}
\]

The machine's developmental loop is:

\[
\boxed{
\text{distinguish}
\to
\text{attempt}
\to
\text{fail exactly}
\to
\text{grow minimally}
\to
\text{verify}
\to
\text{compile}
\to
\text{reclose}
\to
\text{compress}
\to
\text{act}
\to
\text{distinguish again}.
}
\]

The core mathematical invariant is:

\[
\boxed{
\textbf{Residuals earn generators.
Warrant earns relations.
Free completion supplies consequences.
Quotient removes irrelevant distinctions.
Compilation turns the resulting presentation into executable capability.}
}
\]
