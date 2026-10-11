# V4 — critic-constructor genesis falsification gate

Parent: V3 exact qualified commit 837c351df2d69374c3fe4cdeb9eeb5ef57391cd3, CI run 38100307923.
Status: PREREGISTERED. No V4 success or novelty claimed.

## Research objective
Test whether the same developmental mechanism that generated V3 accumulator
proofs can *construct a new repair-plan operator* from a structurally different
induction failure, rather than instantiate its existing monoid/accumulator
schema. The new source family and heldout must be committed before generator
implementation. The source must be independently inspected for proof leakage.

## Old-language boundary
Freeze V3's actual source interpreter and proof compiler, including its
supported operators, patterns, and tactics. This is the old language G3.
Require an exhaustive parser/grammar-relative impossibility certificate for
the new task, not a timeout or a failed invocation.

## New family and controls
Use a branching tree recursion requiring a relation between two recursive
subproblems. The tree fold cannot be solved by V3's linear list-accumulator
induction template alone. A second family must require a different structural
operation, e.g. mutually recursive syntax or dependent-index transport.
Pre-register source SHA, expected truth oracle, negatives and protected split.
Do not embed target theorem statements or proof scripts in the generator.

## New-constructor admission
Construct a typed critic AST whose operational semantics are generated from
the failed residual using generic lower substrate primitives. Record which
semantics are supplied by the substrate and which are newly generated.
Kernel-check emitted Lean proofs. Check preservation of V3 proofs, ablation of
the new constructor, source mutation and forged certificate rejection.

## Strong comparisons
Full stateless proof planning given the same interpreter and budget;
complete executable-memory replay (expected reach tie); existing Lean
induction/simp/aesop tactics; matched search, kernel-check, time and
engineering budgets. No claimed gain from arbitrarily restricting controls.

## Promotion
WARRANTED_BOUNDED only with source-exact Lean CI and complete old-language
obstruction. REUSABLE only after frozen independent transfer. BREAKTHROUGH
only if new constructor semantics were not supplied in advance and the
protected result has a defensible advantage under matched resources.
Otherwise retain UNKNOWN or REJECTED, and preserve negative lineage.
