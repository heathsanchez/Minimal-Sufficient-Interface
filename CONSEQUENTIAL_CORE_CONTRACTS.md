# Consequential Core Contracts

This note is a pre-refactor constraint. It is intentionally stronger than an implementation sketch: the shared kernel must preserve the semantic distinctions already present in the experiments rather than erase them behind a generic `update(state)` interface.

## 1. Shared state

The smallest common developmental state that honestly covers the Difference Test, recursive developmental compounding, and meta-becoming is

\[
S = (E, C),
\]

where:

- `E` is the current observational equivalence / representation kernel on the carrier;
- `C` is the current executable interaction / constructor language.

Neither component is reducible to the other in general. A representation refinement changes which states are identified. A language extension changes which future distinctions/consequences are executable and may induce a later refinement of `E`.

## 2. Five required contracts

### Representation

```text
Representation[X] := EquivalenceRelation[X]
```

Required laws:

1. reflexive, symmetric, transitive;
2. operationally extensional: outcome labels may be renamed without changing the relation;
3. refinements preserve previously licensed separations:
   `refines(E_new, E_old)` means `E_new ⊆ E_old` as relations.

A Boolean column is admitted only through its kernel:

```text
kernel : Observation[X,O] -> Representation[X]
```

so the shared object is not "a Boolean vector" but the equivalence relation it induces.

### Residual

```text
Residual[X] := {
    left: X,
    right: X,
    represented_same: E(left,right),
    certified_consequence_distinguishes: V(left,right)
}
```

A residual is therefore a witnessed failure of current identification under protected consequence. It is not a generic error string or unsolved task.

### Closure

```text
Closure[X] : Language[X] -> Set[Interaction[X]]
```

with a declared resource regime when closure is bounded. A search-failure claim is licensed only relative to this closure and its completeness statement.

### Repair

`Repair` is deliberately a tagged sum, not one homogeneous mutation:

```text
Repair[X] :=
    | RefineRepresentation(new_E: Representation[X])
    | ExtendLanguage(delta: LanguageExtension[X])
    | Coupled(new_E: Representation[X], delta: LanguageExtension[X])
```

This is the minimum signature that covers both representation change and machinery change without identifying them by fiat.

A candidate is a lawful repair only if it satisfies all applicable constraints:

```text
lawful_repair(S, residual, repair) :=
    conservative(repair, S)
    and resolves(residual, apply(repair,S))
    and attaches(repair, residual)
    and verifier_licensed(repair)
```

`conservative` means, at minimum:

- representation updates cannot merge states already separated by `E`;
- language updates cannot delete existing licensed operators unless provenance explicitly withdraws authority;
- coupled updates obey both conditions.

Examples of non-repairs under this signature:

- an arbitrary merge that erases a previously licensed distinction;
- a new operator that does not resolve or attach to the motivating residual;
- an unverified state mutation;
- a language extension whose only effect is outside the protected consequence boundary;
- a representation split with no certified consequential witness.

Thus the interface is general enough to contain both update kinds but restrictive enough to exclude meaningful counterexamples.

### compile / ablate

```text
compile : (S, LawfulRepair) -> S'
ablate  : (S', ProvenanceToken) -> S_counterfactual
```

`compile` must preserve the repair's tag and provenance. `ablate` removes exactly the retained contribution named by that provenance token; it is not permitted to reset unrelated state.

## 3. Compatibility audit without changing existing code

### A. `tests/test_difference_test.py`

Current objects:

- `Representation`: explicit partition / `eq_from_partition`;
- `Residual`: pair `(x,y)` such that current partition merges them and a protected target separates them;
- `Closure`: `action_closure(g)`;
- `Repair`: representation refinement generated from residual orbits;
- `compile`: combine old observation with generated separator to induce `new_p`;
- `ablate`: conceptually remove that separator and recover the old quotient.

Result: **fits `RefineRepresentation` directly.**

### B. `tests/test_recursive_developmental_compounding.py`

Current objects:

- `Representation`: relation induced by chosen query columns;
- `Residual`: first differently labelled pair still merged by chosen observations;
- `Closure`: finite supplied query language under the episode budget;
- `Repair`: learned query-selection policy changes which interaction is acquired next;
- `compile`: retain the policy from source residual history;
- `ablate`: replace retained policy with the cold empty policy;
- downstream capability: `quotient_admissible` on the resulting relation.

Result: **does not fit pure `RefineRepresentation`. It fits machinery change only if policy retention is modelled as an `ExtendLanguage`-like developmental capability or, more accurately, as a policy component above `C`.**

This exposes a possible further state component `D` (developmental policy). If `D` cannot be represented extensionally as executable interactions in `C`, then the honest common state is `(E,C,D)`, not `(E,C)`.

### C. `tests/test_golden_law_meta_becoming.py`

Current objects:

- `Representation`: `kernel(column)` genuinely yields an equivalence relation;
- `Residual`: target kernel absent from the current base language;
- `Closure`: columns constructible from atoms and currently available operator tables under the tested depth;
- `Repair`: retained behavioural class of binary operator;
- `compile`: add a target-domain realizer of that behavioural class to the executable generator;
- `ablate`: remove the learned class and recover base-language failure.

Result: **fits `ExtendLanguage`, not `RefineRepresentation`.** The resulting operator can later induce new representation kernels, but the repair object itself is machinery.

## 4. Refactor-or-redesign decision

The contracts survive, but the audit reveals one load-bearing seam:

- Difference Test: update acts directly on `E`.
- Meta-becoming: update acts directly on `C` and only indirectly on future `E`.
- Recursive developmental compounding: update may act on a policy `D` controlling acquisition from `C` rather than on `C` itself.

Therefore a two-component `(E,C)` kernel is sufficient only if the developmental policy can be compiled extensionally into the executable language. That must be tested, not assumed.

The next implementation should therefore use

```text
DevelopmentState[X] = (E, C, D)
```

with `D` optional/trivial for first-order cases, unless we formally prove a compilation map

```text
compile_policy_into_language : D -> C_extension
```

that preserves target behaviour and ablation.

## 5. Required invariants for a single-chain experiment

A future single-chain test counts as one formal machine only if:

1. every representation is the same `EquivalenceRelation` type;
2. every residual is the same witnessed identification failure type;
3. every closure claim names the same closure interface plus resource regime;
4. every repair is one of the tagged repair constructors above;
5. every compilation produces the same `DevelopmentState` type;
6. every ablation is provenance-exact;
7. source-distinct transfer changes domain adapters only, not the core contracts;
8. second-order development changes `D` or compiles `D` into `C` through an explicit, tested map.

If any existing experiment cannot satisfy these without weakening one of its original claims, the shared-kernel effort is a redesign and must be reported as such.
