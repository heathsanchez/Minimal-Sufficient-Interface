# Golden Law Exhaustive Result — 2026-08-29

## Target

Test the candidate Law of Minimal Consequential Structure in the smallest nontrivial setting where the entire space can be exhausted rather than sampled.

For a finite state set `X` and protected continuation family `C`, define

`E_C = ⋂_{c ∈ C} ker(c)`

or equivalently

`x E_C y  iff  ∀ c ∈ C, c(x) = c(y)`.

The developmental update under a new verified continuation `c` is

`E_{C ∪ {c}} = E_C ∩ ker(c)`.

The experiment also asks whether the law self-applies when observation languages themselves become the objects being quotiented.

## Frozen exhaustive universe

- `|X| = 4` states.
- Every Boolean continuation `c : X -> {0,1}` is included: `2^4 = 16` possible continuations.
- Every protected continuation family is included: `2^16 = 65,536` families.
- Every possible one-step continuation addition is checked: `65,536 × 16 = 1,048,576` transitions.
- Every finite representation map `r : X -> {0,1,2,3}` is covered through its induced kernel; these realize all 15 equivalence relations on four points.
- All 24 permutations of state coordinates are checked on representatives of every induced behavioural quotient.

Source: `tests/test_golden_law_exhaustive.py`

Deciding workflow: GitHub Actions run `33218201279`, job `99006457163`.

## Result

All four preregistered gates passed.

### 1. Developmental law

Across all `1,048,576` possible family-plus-new-continuation transitions,

`E_{C ∪ {c}} = E_C ∩ ker(c)`

held exactly.

Counts:

- strict refinements: `11,432`
- consequence-inert additions: `1,037,144`
- failures: `0`

A strict refinement never introduced a previously absent equality; it only removed identifications that the new continuation could separate.

### 2. Unique coarsest sufficient quotient

The `65,536` raw continuation families induce exactly `15` distinct consequential equivalence relations, equal to the Bell number `B_4`.

For every induced `E_C`, exhaustive comparison against all 15 possible representation kernels showed:

- `E_C` is realizable as a representation kernel;
- every sufficient representation kernel is contained in `E_C`;
- no strictly coarser sufficient equivalence exists.

Thus, in this finite universe, `X / E_C` is exactly the unique coarsest sufficient quotient up to relabelling of quotient classes.

### 3. Self-application

The objects were then changed from states to observation languages themselves.

The `65,536` raw continuation families were judged only by six anonymous meta-consequences: whether the family can separate each unordered pair of states.

The same consequential-quotient construction collapsed those `65,536` syntactically different languages to exactly the same `15` behavioural structures.

Counts:

- raw languages: `65,536`
- meta-level quotient classes: `15`
- largest raw-language equivalence class: `64,152`
- smallest: `4`
- failures: `0`

This is a bounded exact self-application result: the law can take representations/observation languages as its own objects without changing mathematical form.

### 4. Presentation invariance

Every one of the 15 quotient structures was tested under all 24 permutations of the four state coordinates.

- checks: `360`
- failures: `0`

The induced consequential structure changes equivariantly with relabelling; coordinate names carry no semantic authority.

## Classification

`GOLDEN_LAW_FINITE_EXHAUSTIVE_POSITIVE`

Within the complete four-state / Boolean-continuation universe:

`consequence -> indistinguishability -> quotient -> verified separator -> least refinement`

is exact, presentation-invariant, uniquely minimal at the quotient level, and self-applicable to the observation languages that generate the distinctions.

## What this establishes

This is stronger than another constructed positive example because there is no held-out case inside the frozen universe. Every Boolean continuation family and every possible one-step developmental update is included.

It establishes a finite exact theorem-by-exhaustion companion to the existing Lean algebra:

1. identity relative to a continuation family is exactly consequential indistinguishability;
2. adding consequence refines identity by intersection and never by unrelated change;
3. the resulting quotient is the maximal lawful forgetting / unique coarsest sufficient representation;
4. the same construction can be lifted one meta-level by making observation languages themselves the objects.

## What this does not establish

It does **not** prove that the law is a fundamental law of physical reality, nor that every scientific domain has a correct deterministic Boolean continuation interface.

It does **not** solve operational admission, probabilistic/graded outcomes, temporal/contextual judges, open-ended generation of new continuation languages, or natural-domain external validity.

The strongest remaining test is therefore not a larger finite census. It is cross-domain developmental self-application where the system must generate the next useful continuation/representation family rather than receive the complete Boolean family in advance.
