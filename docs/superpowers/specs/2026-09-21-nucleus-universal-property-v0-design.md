# Nucleus Universal Property V0 — Design Specification

**Status:** Draft for user review  
**Repository:** heathsanchez/Minimal-Sufficient-Interface  
**Feature branch:** nucleus-universal-property-v0  
**Base commit:** 900a73c1d386ee0eee1205a1cf31d270f3311ef7

## 1. Purpose

This development formalizes the mathematical shape

\[
\boxed{
\text{directed generators}
\;\xrightarrow{\text{free completion}}\;
\text{all compositional paths}
\;\xrightarrow{\text{warranted quotient}}\;
\text{minimal consequential structure}
}
\]

and connects it to residual-driven development.

The intended nucleus is not a particular Boolean operation and not DMI by itself. It is a warranted category presentation:

1. start with a quiver of references and directed distinctions;
2. freely generate all finite compositional paths;
3. quotient parallel paths by a verifier-backed behavioural congruence;
4. when a certified residual requires a new arrow, adjoin exactly that generator by the universal free extension;
5. impose exactly the verifier-earned equations;
6. repeat.

The central object is

\[
\boxed{
\mathsf{Nuc}(G,\Omega)=F(G)/{\approx_\Omega}
}
\]

where G is a quiver, F(G) is its free category, and \approx_\Omega is a warranted congruence on parallel paths.

V0 must prove the universal factorization property of this quotient and a least residual-induced arrow extension. It must also state, but not overclaim, the stagewise relation between generator growth and behavioural refinement.

## 2. Existing formal results this development must reuse

This programme is a completion of existing mechanized results, not a replacement for them.

### 2.1 Behavioural congruence on states

lean/TypedBehaviouralCongruence.lean already proves contextual behavioural equivalence over typed states, observation compatibility, categorical congruence under every typed continuation, maximality as the greatest observation-compatible congruence family, quotient actions, and unique descended maps via qmap_unique.

This V0 does not reinterpret that result as a morphism quotient. Instead it introduces the missing morphism-level path congruence needed to form an actual quotient category.

### 2.2 Least generated stage inside a fixed ambient category

lean/GeneratedStage.lean already proves adjoinStage is the least identity/composition-closed stage extending the old stage and containing a newly licensed morphism.

Its limitation is explicit: the new morphism already exists in a fixed ambient category.

Nucleus Universal Property V0 strengthens this from "make an ambient morphism accessible" to "freely create a new arrow with specified endpoints and no additional relations."

### 2.3 Developmental quotient refinement

lean/DevelopmentalCategory.lean proves that enlarging the accessible continuation family can refine behavioural identity, and supplies a canonical map from the finer new quotient back to the coarser old quotient via forgetGrowth.

This means the raw generated side and behavioural quotient side evolve in opposite directions:

\[
F_t\to F_{t+1},
\qquad
Q_{t+1}\to Q_t.
\]

V0 must preserve this distinction.

### 2.4 Minimal justified repair

lean/MinimalRepair.lean proves the meet update is the unique coarsest common refinement satisfying the old interface and the new verified constraint.

This provides an existing universal-property analogue on the quotient/refinement side.

### 2.5 CLC nonlinear lineage

The green clc-nonlinear-lineage-v0 development proves that admissible nonlinear quotienting preserves the declared protected query language across every finite source-certified, quotient-compatible trace.

This V0 may use that as a later bridge, but it must not depend on CLC machinery merely to establish the basic free-category / quotient-category universal property.

## 3. Scope

V0 includes:

1. finite quivers with explicit vertices, edges, source, and target;
2. a free-category construction whose morphisms are finite directed paths;
3. the free-category universal property;
4. a path-level warranted behavioural relation on parallel paths;
5. proof that the path relation is an equivalence and a two-sided categorical congruence;
6. construction of the quotient category by that congruence;
7. the quotient-category factorization/uniqueness theorem;
8. a ValidGen characterization in terms of generator interpretations that respect all warranted path equations;
9. a free extension adjoining one fresh arrow X→Y;
10. the universal property of that fresh-arrow extension;
11. a verifier-earned congruence imposed after the free extension;
12. a stage theorem expressing one residual step as free attachment followed by warranted quotient;
13. explicit separation of forward generated growth from backward behavioural refinement;
14. negative fixtures showing why path congruence must quantify over both source states and future continuations.

V0 excludes general computads/polygraphs, automatic addition of new object types, higher cells, infinite path syntax, general small-colimit construction for arbitrary developmental diagrams, a theorem that behavioural quotient stages form a forward colimit, cryptographic warrant, automatic discovery of residual endpoints, automatic discovery of warranted equations, and universal claims about open-ended development.

## 4. Primitive directed generators

A primitive nucleus presentation is a finite quiver

\[
G=(V,E,s,t).
\]

The Lean layer should expose a finite vertex type, finite edge type, decidable equality, and source/target maps.

The use of a multigraph is essential: distinct generating distinctions may have the same source and target while remaining different generators with different provenance.

V0 keeps vertices explicit. It does not claim that references are eliminable in general, because isolated vertices cannot be reconstructed from edge incidence alone.

The safe interpretation is

\[
\boxed{
\text{Reference + Directed Difference}
=
\text{underlying quiver data}.
}
\]

## 5. Free completion

For every quiver G, define or reuse the free category F(G).

Its morphisms are finite composable edge paths.

- identity is the empty path;
- composition is path concatenation;
- associativity follows from path concatenation;
- no additional equations between distinct paths are imposed.

The preferred implementation should reuse Mathlib's quiver/path-category infrastructure where it reduces proof burden without changing the mathematical contract. A local minimal wrapper is permitted if it makes the universal property easier to audit.

### 5.1 Required theorem: free lift

For every category D, a quiver interpretation

\[
\phi:G\to U D
\]

extends to a functor

\[
\widehat\phi:F(G)\to D.
\]

Required theorem name: freeNucleus_lift.

### 5.2 Required theorem: uniqueness

If two functors F(G)→D agree on every generating edge and vertex, they agree on every path.

Required theorem name: freeNucleus_lift_unique.

The public mathematical statement is

\[
\boxed{
\operatorname{Fun}(F(G),D)
\cong
\operatorname{QuiverHom}(G,U D).
}
\]

V0 need not package this as a full categorical adjunction object if the two directions and mutual inverse laws are proved explicitly.

## 6. Warranted path behaviour

The quotient must live on parallel morphisms, not only on states.

Let A be an action of F(G) on typed state spaces and let protected observations be assigned at each object.

For parallel paths p,q:X→Y, define

\[
p\approx_\Omega q
\]

iff for every source state x in A(X), every accepted protected future continuation r:Y→Z, the protected observations after r∘p and r∘q agree:

\[
\boxed{
p\approx_\Omega q
\iff
\forall x,\forall Z,\forall r:Y\to Z,\;
\operatorname{Obs}_Z(A(r\circ p)x)
=
\operatorname{Obs}_Z(A(r\circ q)x).
}
\]

If warrant is stage-relative, the quantified future continuations are exactly those accepted by the declared stage/snapshot.

The use of both quantifiers is deliberate.

- Quantification over every future continuation gives postcomposition stability.
- Quantification over every source state gives precomposition stability.

A weaker relation that omits either side must be tested by a negative fixture and must not be used as the quotient congruence.

## 7. Path congruence theorem

V0 must prove reflexivity, symmetry, transitivity, right/postcomposition congruence, and left/precomposition congruence.

The central theorem is pathBehEq_congruence:

\[
p\approx_\Omega q
\Longrightarrow
a\circ p\circ b
\approx_\Omega
a\circ q\circ b
\]

for every composable a and b.

The resulting relation is therefore a categorical congruence on each hom-set.

## 8. Quotient category

Construct

\[
\mathsf{Nuc}(G,\Omega)=F(G)/{\approx_\Omega}
\]

as a category with the same objects as F(G), hom-sets given by equivalence classes of parallel paths, identity induced by empty paths, and composition induced by concatenation.

Well-definedness of composition must use the two-sided congruence theorem.

The quotient projection is a functor

\[
\pi:F(G)\to\mathsf{Nuc}(G,\Omega).
\]

Public theorem names should include nucleusCategory, nucleusProjection, and a representative-surjectivity theorem for quotient homs.

## 9. Universal property of the warranted quotient

Let D be any category.

A functor

\[
H:F(G)\to D
\]

is warrant-respecting when

\[
p\approx_\Omega q\Longrightarrow H(p)=H(q).
\]

Then H factors uniquely through the quotient:

\[
F(G)\xrightarrow{\pi}\mathsf{Nuc}(G,\Omega)
\xrightarrow{\bar H}D.
\]

Required theorem names:

- nucleus_descend;
- nucleus_descend_comp_projection;
- nucleus_descend_unique.

The target category does not need a special "fully consequentially extensional" property. The exact requirement is on the interpretation: it must equalize every warranted path relation.

## 10. Generator-level universal property

Define ValidGen(G,Ω,D) to be quiver interpretations

\[
\phi:G\to U D
\]

whose unique free extension respects \approx_\Omega.

Then prove

\[
\boxed{
\operatorname{Fun}
(\mathsf{Nuc}(G,\Omega),D)
\cong
\operatorname{ValidGen}(G,\Omega,D).
}
\]

Required headline theorem: nucleus_universal.

The equivalence must contain explicit forward/backward maps and inverse laws. ValidGen must not be defined by existence of a functor out of Nuc, because that would make the theorem circular.

## 11. Fresh-arrow residual extension

Let C be the current category and let a certified residual identify two existing endpoints X,Y.

The residual requires a genuinely new arrow

\[
\rho:X\to Y
\]

that is not assumed already present in C.

Construct the least category C[ρ] extending C with one fresh arrow X→Y and no additional relations beyond the category laws.

Mathematically:

\[
\boxed{
C[\rho]
=
C\amalg_{\partial[1]}[1].
}
\]

V0 may implement an equivalent explicit syntax of alternating old morphisms and the fresh generator if proving the pushout through Mathlib infrastructure is materially harder. In either implementation, the universal property is the normative contract.

## 12. Universal property of residual attachment

Given any category D, functor

\[
F:C\to D,
\]

and any arrow

\[
a:F(X)\to F(Y),
\]

there is a unique extension

\[
\bar F:C[\rho]\to D
\]

that agrees with F on C and sends ρ to a.

Required theorem names: residualAdjoin_universal and residualAdjoin_unique.

This is the categorical strengthening of the existing GeneratedStage.adjoin_least theorem.

The required distinction is:

\[
\boxed{
\text{GeneratedStage.adjoinStage}
:
\text{license existing ambient arrow}
}
\]

versus

\[
\boxed{
\text{ResidualAdjoin}
:
\text{freely create a new arrow}.
}
\]

## 13. Warrant after residual attachment

After C[ρ] is created, the verifier may establish equations between newly generated paths.

Let \sim_\Omega^+ be the resulting warranted path congruence.

Define

\[
\boxed{
C_{t+1}
=
C_t[\rho_t]/\sim_{\Omega_t}^+.
}
\]

Required composite construction: developmentStep.

Its theorem surface must expose two universal stages:

1. free minimal attachment;
2. quotient by exactly the supplied warranted congruence.

No theorem may claim that the verifier automatically discovers the complete congruence. The congruence is input evidence.

## 14. DMI interpretation

Under this construction:

\[
\begin{aligned}
D &: \text{identify the certified residual and endpoints},\\
M &: \text{freely adjoin the required generator},\\
V &: \text{establish warranted path equations},\\
I &: \text{install the quotient extension}.
\end{aligned}
\]

DMI is therefore not the foundational algebra. It is a developmental mechanism that repeatedly constructs universal extensions.

The formal development should treat this as an interpretation layer rather than bake D/M/V/I into core categorical definitions.

## 15. Temporal architecture: direct and inverse directions

V0 must explicitly reject the oversimplified statement

\[
C_\infty=\operatorname*{colim}_t C_t
\]

for quotient stages without further hypotheses.

There are two different temporal diagrams.

### 15.1 Generated structure

Free generator attachment gives forward maps

\[
F_0\to F_1\to F_2\to\cdots.
\]

Under suitable hypotheses, accumulated raw generated structure may later be described by a direct colimit.

### 15.2 Behavioural interfaces

When the protected future language only grows, behavioural equivalence becomes finer, producing canonical forgetful maps

\[
\cdots\to Q_2\to Q_1\to Q_0.
\]

This is inverse-direction refinement, matching DevelopmentalCategory.forgetGrowth.

V0 should prove a finite-stage compatibility theorem between these directions where feasible, but it does not need to construct an infinite inverse limit or direct colimit.

When CLC-style revocation/policy changes are admitted, even monotone quotient refinement can fail; the appropriate object is then a snapshot-indexed diagram over immutable certified lineage. That is deferred.

## 16. Mandatory negative fixtures

### 16.1 No future-context quantification

Construct parallel paths p,q:X→Y that agree immediately but are separated by a continuation r:Y→Z. Show immediate endpoint agreement is not postcomposition-stable.

### 16.2 No source-state quantification

Construct paths that agree on one source state but not another and show the relation is not safe under input variation/precomposition.

### 16.3 Free completion without quotient

Give two syntactically distinct paths that warrant identifies. Show F(G) alone is not consequentially minimal.

### 16.4 Quotient without congruence

Supply a relation on paths that is an equivalence but fails whiskering stability. Show composition on equivalence classes is not well defined.

### 16.5 Ambient-arrow versus fresh-arrow distinction

Construct a current category with no morphism X→Y satisfying the residual requirement. Show GeneratedStage.adjoinStage cannot express the new arrow because it assumes an ambient morphism, while ResidualAdjoin can.

## 17. Lean module boundaries

New modules live under qcklean/Nucleus and do not modify the green CLC V0 theorem surface or frozen QCK theorem files.

| Module | Responsibility |
|---|---|
| qcklean/Nucleus/Quiver.lean | finite quiver definitions and generator maps |
| qcklean/Nucleus/Free.lean | free paths/category and free-lift universal property |
| qcklean/Nucleus/PathBehavior.lean | warranted path relation and two-sided congruence |
| qcklean/Nucleus/Quotient.lean | quotient category and projection |
| qcklean/Nucleus/Universal.lean | quotient factorization and nucleus_universal |
| qcklean/Nucleus/ResidualAdjoin.lean | fresh-arrow extension and universal property |
| qcklean/Nucleus/Development.lean | free-attachment then warranted-quotient developmental step |
| qcklean/Nucleus/Fixtures.lean | positive and negative finite fixtures |
| qcklean/Nucleus/Audit.lean | axiom and theorem-surface audit |
| qcklean/Nucleus/*Test.lean | interface and executable fixture tests |

Existing qcklean/CLC/** and qcklean/QCK*.lean files remain unchanged.

## 18. Qualification requirements

A passing V0 must establish all of the following at one committed branch head:

- free paths/category compile;
- every quiver map extends to a functor;
- that extension is unique;
- warranted path equivalence is an equivalence;
- warranted path equivalence is stable under both pre- and postcomposition;
- quotient composition is well defined;
- the quotient projection is functorial;
- every warrant-respecting free functor descends uniquely;
- nucleus_universal is proved non-circularly;
- one genuinely fresh arrow can be adjoined without assuming it exists in an ambient category;
- the fresh-arrow extension satisfies its universal property;
- the existing ambient-arrow GeneratedStage result is not silently substituted for fresh-arrow genesis;
- mandatory negative fixtures fail exactly where expected;
- CLC V0 remains green and unchanged;
- frozen QCK theorem sources remain unchanged;
- no sorry, admit, project-local axiom, constant, or unsafe declaration appears in new Nucleus modules;
- the public theorem axiom surface contains only foundations already accepted by repository policy.

## 19. Claim boundary

Passing V0 would establish:

> A finite directed-generator presentation admits a canonical free compositional completion; any verifier-backed two-sided congruence on generated paths yields a quotient category with the expected generators-and-relations universal property; and a certified residual between existing endpoints can be realized by the least fresh-arrow extension before verifier-earned equations are imposed.

Equivalently:

\[
\boxed{
\text{free generation}
+
\text{warranted congruence}
=
\text{universal consequential presentation}.
}
\]

It would not establish that the warrant relation is complete for reality, that residuals always identify the right endpoints, that every useful repair is an arrow rather than a new object/type, that the system autonomously discovers all category laws, that quotient stages form a direct colimit, that infinite/open-ended development exists, that references can always be recovered from edge incidence, or that arbitrary real-world representation learning is captured by this mechanism.

## 20. Deferred V1 extensions

After V0:

1. object attachment \(\varnothing\to[0]\);
2. multiple simultaneous arrow attachments;
3. finite computads/polygraphs;
4. integration with CLC nonlinear lineage and snapshot-relative warrant;
5. explicit direct-system / inverse-system compatibility;
6. executable developmental-language integration, where learned capabilities are generators and compiled equivalences are warranted relations.

The V0 stopping point is deliberate: prove the arrow-level universal property before generalizing the cell language.
