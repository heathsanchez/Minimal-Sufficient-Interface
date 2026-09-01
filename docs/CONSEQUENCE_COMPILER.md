# Consequence Compiler

Status: executable finite reference implementation.

## Purpose

The Consequence Compiler is a domain-independent layer over `consequential_core.py`.
It takes a finite specification

\[
(X,I,D,\mathcal H,Q,\kappa)
\]

where:

- `X` is the carrier;
- `I` is the declared current observation/interface family;
- `D` is the protected consequence family;
- `H` is a declared candidate realization family;
- `Q` is an optional family of future queries;
- `kappa` is an optional externally declared operational cost model.

No constitutional, IRL, graph, reward, proof, or other domain-specific repair rule is present in the compiler.

## Derived objects

From the same generic specification the compiler computes:

1. current representation
   \[
   E_I=\bigcap_{i\in I}\ker i;
   \]
2. all pair residual witnesses for protected consequences;
3. canonical protected repair
   \[
   E^+=E_I\cap\bigcap_{d\in D}\ker d;
   \]
4. whether the repair is strict;
5. factorization status of each protected and future query before and after repair;
6. candidate realizers `h in H` satisfying
   \[
   \ker(I,h)=E^+;
   \]
7. operational profiles for lawful realizers when a cost model is declared;
8. one verifier-licensed compiled state transition using `consequential_core.certify_repair` and `compile_repair`;
9. exact provenance ablation back to the pre-repair state.

If no residual exists, the compiler returns a fixed point and does not manufacture a repair.

## What is derived versus declared

The quotient, residuals, canonical meet repair, factorization checks, lawful-realizer membership, and fixed-point status are derived from the supplied finite functions.

The candidate language `H` and operational cost model `kappa` are **declared structure**. The compiler does not infer a representation language or complexity semantics from equivalence relations alone. This preserves the existing distinction

\[
\underbrace{E^+}_{\text{what must be distinguished}}
\neq
\underbrace{\Delta\in\mathcal V(E^+;\mathcal H)}_{\text{how it is realized}}.
\]

## Cross-domain acceptance test

`tests/test_consequence_compiler_cross_domain.py` submits three specifications to the same `compile_consequences` function.

### Constitutional

Carrier `Bool x Bool`, current interface `authority`, protected consequence `audit`, candidate realizers `audit` and `xor`.

Expected generic outputs:

- 2 residual pairs;
- strict canonical repair;
- 2 lawful realizers;
- opposite declared cost profiles `(1,2)` and `(2,1)`;
- protected and future queries factor after repair;
- exact provenance ablation succeeds.

### IRL exact-gap control

Carrier `{-2,-1,0,1,2}^2`, current interface `r1-r0`, protected consequence `r0`, candidate realizers `r0` and `r1`.

Expected generic outputs:

- 30 residual pairs;
- strict canonical repair to reward identity;
- 2 lawful realizers;
- optimal-action query already factors through the old policy-gap quotient;
- absolute-coordinate queries require the repaired quotient;
- exact provenance ablation succeeds.

### Already-sufficient fixed point

Identity interface with parity protected.

Expected generic outputs:

- zero residuals;
- no strict repair;
- no certified transition manufactured;
- before and after states identical.

## Scientific claim boundary

Passing the cross-domain test supports this limited statement:

> The same executable finite calculus can recover residuals, canonical consequence-sufficient quotient repair, lawful realization candidates, factorization/stopping status, and a provenance-bearing compiled transition in two semantically different domains without domain-specific repair logic.

It does **not** yet establish:

- unrestricted open-ended representation-language genesis;
- automatic invention of candidate realizers;
- automatic discovery of the protected consequence family;
- automatic cost-model discovery;
- scaling beyond finite enumerated carriers;
- universal optimality of any chosen realization.

Those are separate developmental layers rather than facts to hide inside the compiler.
