# Consequence–Distinction Duality

**Status:** proposed authoritative semantic core for Minimal-Sufficient-Interface.

This document isolates the smallest mathematical object currently shared by MSI's quotient theorems, residual repair, capability descent, developmental categories, and the RealityGraph consequence compiler.

It is deliberately narrower than a universal theory of learning. The constitution, verifier authority, admissible consequence universe, repair grammar, and resource regime remain explicit external parameters.

## 1. Fixed boundary

Fix a developmental boundary `kappa` supplying:

- a state space `X`;
- a type `A` of admissible consequence tokens;
- for each `a : A`, a kernel relation `K_a` on `X` describing which states the consequence treats identically;
- verifier/authority, scope, and resource conditions determining which consequence tokens are admissible;
- protected objectives deciding which consequences currently matter.

For an ordinary observation `c : X -> Y`, the familiar concrete kernel is

```text
K_c(x,y)  iff  c(x) = c(y).
```

The abstract kernel-token formulation is intentional: different consequences may have different codomains while still participating in the same theory.

A representation is a relation `E` on `X`. In MSI applications `E` is normally an equivalence relation or behavioural congruence; the core polarity below requires only relation inclusion.

## 2. The two maps

For a family `C` of protected consequences, define its common consequential kernel

```math
\Phi(C)=\bigcap_{a\in C}K_a.
```

For a representation `E`, define the consequences that lawfully descend through it

```math
\Psi(E)=\{a\in A:E\subseteq K_a\}.
```

`Phi` asks:

> Which distinctions must be preserved for this consequence family?

`Psi` asks:

> Which declared consequences remain well-defined after this representation has forgotten its distinctions?

## 3. Core theorem: the antitone Galois law

For every consequence family `C` and representation `E`,

```math
\boxed{
C\subseteq\Psi(E)
\iff
E\subseteq\Phi(C).
}
```

Proof: `C subseteq Psi(E)` means `E subseteq K_a` for every `a in C`, which is exactly `E subseteq intersection_{a in C} K_a`.

Thus `Phi` and `Psi` are order reversing:

```math
C\subseteq D \Longrightarrow \Phi(D)\subseteq\Phi(C),
```

```math
E\subseteq F \Longrightarrow \Psi(F)\subseteq\Psi(E).
```

The Lean target `lean/ConsequenceDistinctionDuality.lean` machine-checks this law directly.

## 4. The two closure operators

The polarity induces two closures.

### Consequence closure

```math
\operatorname{Cl}_C(C)=\Psi(\Phi(C)).
```

This is every declared consequence already supported by the distinctions forced by `C`.

It is extensive and idempotent:

```math
C\subseteq\operatorname{Cl}_C(C),
\qquad
\operatorname{Cl}_C(\operatorname{Cl}_C(C))=\operatorname{Cl}_C(C).
```

### Representation closure / verified forgetting

```math
\operatorname{Cl}_E(E)=\Phi(\Psi(E)).
```

Because relations are ordered by inclusion, this closure is coarser than `E`:

```math
E\subseteq\operatorname{Cl}_E(E).
```

It forgets distinctions that no admissible consequence descending through `E` requires. It is likewise idempotent.

This is the exact semantic form of:

> SPLIT where consequence requires; MERGE where consequence permits.

## 5. Closed pairs: consequential fixed points

A semantically closed consequence/representation pair satisfies

```math
C=\Psi(E),
\qquad
E=\Phi(C).
```

Equivalently, each side is closed under the corresponding closure operator.

A closed pair says:

- every retained distinction is licensed by the closed consequence family;
- every declared consequence compatible with those distinctions is already in the closed consequence family.

This is a **semantic fixed point relative to the declared boundary**. It is not a claim that open-ended development is globally complete.

## 6. MSI is recovered as the `Phi` side

When consequence tokens are ordinary observations/decisions `c : X -> Y_c` with equality kernels,

```math
\Phi(C)=\bigcap_{c\in C}\ker(c).
```

Therefore the MSI quotient

```math
Q_C=X/\Phi(C)
```

is exactly the quotient induced by the consequence–distinction polarity.

The existing MSI coarsest-sufficiency theorem is therefore not a parallel construction: it is the representation half of this duality.

## 7. Residual = failure of the Galois relation for one consequence

For a desired consequence `d`, a residual is a witness

```math
\rho=(d,x,y),
\qquad
E(x,y),
\qquad
\neg K_d(x,y).
```

Equivalently,

```math
\boxed{
\operatorname{Residual}(E,d)
\iff
d\notin\Psi(E).
}
```

For ordinary function kernels this is exactly

```math
E(x,y) \land d(x)\ne d(y).
```

A residual therefore says something stronger than "search failed": the desired consequence cannot be well-defined on the current quotient.

## 8. Least representational repair

The canonical repair is

```math
\boxed{
E^+=E\cap K_d.
}
```

It has three properties:

1. `E+ subseteq E`: it never merges states that the old representation distinguished;
2. `E+ subseteq K_d`: the desired consequence now descends;
3. for every `R` with `R subseteq E` and `R subseteq K_d`, `R subseteq E+`.

So `E+` is the unique coarsest semantic refinement that preserves the old distinctions and makes `d` lawful.

If a residual exists, the refinement is strict. Exact ablation back to `E` restores the descent obstruction.

## 9. Keep representation, capability, and consequence distinct

The duality is between distinctions and consequences. Executable capabilities are a separate generator layer.

Let

```math
\Gamma_B(L)
```

be the verifier-accepted consequence family reachable from executable language `L` under resource regime `B`.

The load-bearing consistency invariant is

```math
\boxed{
\Gamma_B(L)\subseteq\Psi(E).
}
```

Anything advertised as executable through the active representation must actually descend through that representation.

This yields a precise diagnostic hierarchy for a desired consequence `d`.

### Representation failure

```math
d\notin\Psi(E).
```

The active representation has forgotten a distinction required by `d`. More search in the same quotient cannot fix this.

### Capability/language failure

```math
d\in\Psi(E)
\quad\text{but}\quad
d\notin\Gamma_B(L).
```

The representation is sufficient, but the current bounded executable language cannot realize the consequence.

### Search failure

```math
d\in\Gamma_B(L)
```

but the current search procedure has not found the reachable consequence.

### Solved

The consequence has been found and independently admitted under the declared verifier boundary.

Under `Gamma_B(L) subseteq Psi(E)` and `Found subseteq Gamma_B(L)`, these cases form the intended non-overlapping hierarchy. The Python oracle and Lean file both encode this boundary.

## 10. Developmental coupling

Capability acquisition can expose new verified consequences. New consequences can force finer representations. Finer representations can make further consequences lawful.

Schematic loop:

```math
L_t
\to
\Gamma_B(L_t)
\to
C_t
\to
E_t=\Phi(C_t)
\to
\Psi(E_t)
\to
L_{t+1}.
```

The existing MSI developmental-category theorem proves one direction in categorical form: enlarging the accessible continuation subcategory can only refine stage-relative behavioural identity.

The present duality supplies the converse semantic pressure: changing what can be distinguished changes what can lawfully descend through the active representation.

This is the mathematical core of the recursive slogan:

> distinctions determine lawful capability; capability exposes consequences; consequences determine distinctions.

## 11. Semantic fixed point vs developmental fixed point

Do not conflate two stopping notions.

A **semantic fixed point** is closed under `Phi` and `Psi` for the current declared consequence universe.

A **developmental fixed point** is stronger and relative to an admissible repair/extension grammar and resource regime: no certified residual can be resolved by any available lawful representation or capability extension under that boundary.

Failure to find a repair under incomplete coverage remains `UNKNOWN`, not a fixed point or impossibility theorem.

## 12. What compression optimizes

Compression does not define semantic truth or sufficiency.

First determine the closed semantic object. Then, among implementations/presentations that regenerate the same verified closure, minimize cost:

```math
M^*\in\arg\min_M \operatorname{Cost}(M)
\quad\text{subject to}\quad
\operatorname{Closure}(M)=\mathfrak C.
```

This is where description length, execution cost, restart cost, and future search cost belong.

In the intended stack:

- MSI owns the semantic theorem;
- RealityGraph discovers and verifies moves between consequential states;
- `.mg` stores a compact verified presentation/generating basis of retained active memory;
- MathGraph indexes and queries the resulting verified consequential closure.

## 13. Explicit non-claims

This core does **not** derive:

- which objectives or consequences deserve protection;
- verifier authority;
- arbitrary new consequence types;
- an unrestricted repair grammar;
- arbitrary constructor-language genesis;
- a universal optimum over all representations;
- an unqualified theory of all human, biological, or machine learning.

All closure and fixed-point claims are relative to their declared consequence universe, authority, scope, and resource boundary.

## 14. Executable witnesses

The branch carries three mutually checking layers:

- `consequence_distinction.py` — finite executable oracle;
- `tests/test_consequence_distinction_duality.py` — finite duality/residual/diagnostic tests;
- `lean/ConsequenceDistinctionDuality.lean` — theorem package independent of the finite implementation.

The dedicated GitHub Actions gate is `.github/workflows/consequence-distinction-duality.yml`.
