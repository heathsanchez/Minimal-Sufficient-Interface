# Verifier-driven Lean proof-term genesis — V1

This experiment strengthens PR #8 by removing the supplied `chain3` proof shape.

## Question

Can a bounded proof grammar be exhausted, then expanded by generic typed application search so that the verifier selects the internal proof program, after which the discovered program becomes a reusable Lean-checked operator?

## Frozen initial grammar

The learner receives only local hypotheses and the generic term grammar

```text
term ::= local | term term
```

with ordinary simply-typed arrow matching. It is not given composition, `chain3`, a fusion template, tactic names, or a target proof AST.

Primary world:

```text
f : A -> B
g : C -> D
h : B -> D -> E
a : A
c : C
goal: E
```

The old grammar is exhaustively bounded at AST cost 7. There is no term of type `E` within that bound.

Only after that exhaustion does the same enumerator continue by increasing structural cost. The first verifier-admissible term appears at the minimum larger cost. That term is then frozen and emitted as a Lean theorem `fuse`.

## Anti-template check

The identical synthesizer is run on three dependency topologies:

1. parallel fuse: `h : B -> D -> E`;
2. reversed fuse: `h : D -> B -> E`;
3. lifted fuse: `k : B -> D -> X`, `h : X -> E`.

The system must generate three distinct proof terms. This is the key distinction from PR #8: the internal proof shape is not predeclared as the operator being learned.

## Transfer

The primary discovered proof program is frozen as a reusable Lean operator and checked on 120 held-out theorem declarations with reordered binders and irrelevant local context. The generated alternate-topology programs are also independently checked by Lean.

## Causal/resource ablation

Under a one-node retained-operator budget, removing the synthesized operator closes 0/120 held-out targets; installing it closes 120/120. Cold proof construction still requires rediscovering the larger application tree.

## Claim boundary

This is not unrestricted Lean tactic invention. The meta-language is still the generic simply-typed application grammar over supplied local hypotheses, and the search is bounded. The stronger claim is:

> After a bounded proof grammar is certified insufficient, generic typed term search can discover the internal structure of a missing reusable proof operator without being given its proof template; Lean then verifies the synthesized operator and its held-out reuse.

The next frontier is to drive the same process from naturally occurring Lean proof-state residuals in a non-synthetic theorem corpus, rather than a controlled typed-calculus world.
