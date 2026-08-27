# Formal specification

## 1. Primitive data

Let `X` be a set of situations, `C` a set of protected continuations, `O` a set of verifier-visible outcomes, and

\[
P:X\times C\to O.
\]

For each `c ∈ C`, write `P_c(x)=P(x,c)` and define

\[
\operatorname{Sep}_c(x,y) \iff P_c(x)\neq P_c(y).
\]

For any retained continuation family `B ⊆ C`, define

\[
\boxed{x\sim_B y \iff \forall c\in B,\;P_c(x)=P_c(y).}
\]

Equivalently,

\[
\sim_B=\bigcap_{c\in B}\ker P_c.
\]

This relation is the kernel's only state-identification primitive.

## 2. Elementary laws

### L1 — equivalence

For fixed `B`, `~_B` is reflexive, symmetric, and transitive.

### L2 — monotone refinement

If `B ⊆ B'`, then

\[
\sim_{B'}\subseteq\sim_B.
\]

Adding protected continuations may split an existing class; it cannot merge a pair already distinguished.

### L3 — one-step update

For `c ∈ C`,

\[
\boxed{\sim_{B\cup\{c\}}=\sim_B\cap\ker P_c.}
\]

### L4 — residual

Let the full protected relation be `~_C`. A live residual is

\[
\rho_B(x,y) \iff x\sim_B y \land x\not\sim_C y.
\]

Equivalently,

\[
\rho_B(x,y)
\iff
\exists c\in C\setminus B:\;x\sim_B y\land\operatorname{Sep}_c(x,y).
\]

### L5 — separator strictness

If `ρ_B(x,y)` and `c` separates that pair, then with `B'=B∪{c}`,

\[
\sim_{B'}\subsetneq\sim_B.
\]

### L6 — exact stopping criterion

Define

\[
\operatorname{Residual}(B)
\iff
\exists x,y,c\in C\setminus B:\;x\sim_B y\land\operatorname{Sep}_c(x,y).
\]

Then

\[
\boxed{\neg\operatorname{Residual}(B)\iff\sim_B=\sim_C.}
\]

Thus silence of one continuation is local evidence only. Certified sufficiency requires coverage of every still-relevant separator or a theorem/certificate equivalent to that coverage.

### L7 — finite convergence

Assume `C` finite. Start with any `B_0 ⊆ C`. While a live residual exists, add any continuation that separates a witnessed residual pair. Every step is strict refinement and adds a previously absent continuation. Therefore the process terminates after at most `|C\B_0|` additions at some `B_T` satisfying

\[
\sim_{B_T}=\sim_C.
\]

This proves correctness of lawful residual repair, not minimum-cardinality discovery.

## 3. Sufficient bases

A family `B ⊆ C` is sufficient iff

\[
\sim_B=\sim_C.
\]

Its minimum cardinality is

\[
m(P,C)=\min\{|B|:B\subseteq C,\;\sim_B=\sim_C\}.
\]

Lawful repair need not return a basis of size `m(P,C)`. Correct convergence and efficient convergence are distinct problems.

## 4. Capability descent

Let `f:X→X` be a transformation. It induces a well-defined quotient map

\[
\bar f:X/{\sim_B}\to X/{\sim_B},\qquad \bar f([x])=[f(x)]
\]

iff

\[
\boxed{x\sim_B y\Rightarrow f(x)\sim_B f(y).}
\]

This is the congruence condition. Without it, acting on the quotient is undefined because one equivalence class can be mapped to multiple quotient classes.

If every generator in a transformation family preserves `~_B`, compositions preserve `~_B` as well, so raw reachability may be quotiented consistently.

## 5. Capability-induced interface refinement

If acquiring a transformation `f` makes a new protected continuation available, for example `c_f(x)=v(f(x))` for a protected observation `v`, then the retained family grows from `B` to `B∪{c_f}` and therefore

\[
\sim_{B\cup\{c_f\}}\subseteq\sim_B.
\]

In some finite worlds this refinement changes a second transformation `g` from non-congruent to congruent. Hence a causal bridge of the form

\[
f\to\text{new continuation}\to\text{finer interface}\to g\text{ becomes quotient-admissible}
\]

is possible and testable. This does not by itself prove autonomous discovery of `f` or `g`.

## 6. Claim boundary

The kernel establishes relational facts about protected continuation semantics. It does not assume or establish that:

- the protected continuation family is complete for reality;
- separators are cheap to find;
- one silent test certifies global sufficiency;
- lawful repair is basis-minimal;
- every useful transformation descends to the current quotient;
- arbitrary intelligence is reducible to this kernel.

Those are application-level or stronger research claims and must be established separately.
