# ARC-3 Protected-Future Compiler Design

**Status:** design approved in conversation; written specification awaiting review

**Branch:** `arc3-public-protected-future-compiler-v1`

**Scientific base:** `6fd192fc89babbfdfcbc8bbbac891c846ce70070`

**Objective:** assemble one game-independent learner that discovers the smallest legally observable control-response quotient preserving progress, compiles it into an executable ARC capability, and reuses it without rediscovery.

## 1. Current warranted boundary

The implementation begins from the latest local ARC lineage rather than from the older port hypothesis.

- G3 is solved by a temporal path program, `URRRUR`.
- G4 is solved locally by scale-normalized docking, `ILDDDD`.
- G5 is solved locally by a multicolor endpoint transform, `XDDDTS`, including an active middle-port projection.
- G6 has a unique visible route, `RRRRUULLUUUL`, and the four direction controls have been decoded in their local control frames.
- The proposed consecutive-pair decoders OR, AND, XOR, and equality-preserving XOR have all failed to advance G6. Their exact local evidence is retained in `evidence/arc3-public-g6-paired-route/result.json`.
- The G6 branch has no hosted Actions authority yet. G4/G5 remain local unless a later hosted gate supplies exact run, job, artifact, and digest fields.

The exact residual is therefore not “find another rowwise operator.” It is:

> Discover the coarsest grouping and projection of legally observed route/control consequences that preserves the successful future, without naming the grouping in advance.

## 2. Design law

For histories `s` and `t`, boundary `B`, legal action alphabet `A`, and an explicit bounded continuation language `W`:

```text
s ~_B,W t  iff  Obs_B(delta(s, w)) == Obs_B(delta(t, w)) for every w in W
```

The compiler starts maximally coarse and splits a block only when it has a concrete legal continuation witnessing a protected difference. A quotient is executable only when it is a congruence for every retained action/effect: equivalent inputs must lead to equivalent successors, equal protected observations, and the same required control choice.

Finite exhaustion warrants the quotient only on the declared reachable state/action/horizon boundary. Anything outside that boundary is `UNKNOWN`, not inferred equivalent.

## 3. Scope

### In scope for V1

1. A dependency-light finite deterministic transducer learner.
2. Canonical state, action, observation, transition, quotient, and witness identities.
3. Fixed-point partition refinement using protected observation and successor classes.
4. Shortest distinguishing words for every separated state pair.
5. Explicit control/effect congruence checking.
6. Shortest successful program extraction in the learned quotient.
7. An ARC adapter that consumes visible frames and legal click outcomes only.
8. Compilation into the existing `SemanticCapabilityClosure` path instead of a parallel runtime.
9. Fail-closed residuals for incomplete exploration, nondeterminism, non-congruence, or absent terminal evidence.
10. Qualification on synthetic machines, already solved G3–G5 fixtures, exact public tn36 G6, and at least one held-out or metamorphic transfer boundary.

### Explicitly out of scope for V1

- Hidden game-source inspection or hidden answer access.
- Arbitrary target-matrix enumeration.
- Generic unrestricted program synthesis.
- Claims of global Myhill–Nerode minimality outside the explored finite boundary.
- Automatic Kaggle submission before exact local/hosted qualification.
- A new universal ontology for pose, port, direction, color, or geometry.

## 4. Architecture

### 4.1 Generic core: `protected_future.py`

The generic core contains no ARC colors, coordinates, glyph names, or tn36 constants.

It exposes immutable records conceptually equivalent to:

```python
Transition(source, action, target, observation, effect, protected_outcome)
ExplorationBoundary(actions, max_depth, max_states, terminal_labels)
FutureQuotient(classes, transitions, witnesses, boundary, status)
CompiledCapability(interface_id, quotient_id, start_class, accepting_classes, program)
UnknownResidual(missing_interface, reason, evidence)
```

Core operations:

- `refine_partition(...)`: compute the coarsest stable partition on the observed finite graph.
- `shortest_separator(...)`: return the shortest action word that distinguishes two states; lexical action order breaks equal-length ties.
- `check_congruence(...)`: reject a quotient if an action/effect or required control does not factor through it.
- `shortest_accepting_program(...)`: breadth-first search in quotient space.
- `compile_capability(...)`: emit a canonical, content-addressed capability only after congruence and terminal checks pass.

Canonical identity hashes the normalized meaning-bearing payload: ordered action labels, canonical class members, protected observations, transition table, boundary, and preservation interfaces. It never hashes filenames, Python object identity, traversal order, or parenthesization trees.

### 4.2 ARC adapter: `future_arc.py`

The ARC adapter translates legal public interaction into the generic core:

- normalizes the latest visible frame;
- identifies clickable controls through existing geometry routines;
- records every attempted legal action and resulting visible frame;
- extracts only declared protected observations;
- records progress, level change, win, loss, and action rejection as typed effects;
- associates target-panel projections only when the observed control response warrants them;
- returns `UNKNOWN` when the frame lacks an interface needed by the compiler.

The adapter may reuse existing `semantic_path.py` observation functions. It must not import G3/G4/G5/G6 solution strings into the generic learner. Previously compiled programs may be fixtures and regression oracles, but not learner inputs during cold qualification.

### 4.3 Exploration driver

The driver explores lazily and deterministically:

1. Begin at the exact qualified level boundary.
2. Record the protected observation of the start state.
3. Choose the legal probe with maximum current partition-separation value; break ties by canonical action identity.
4. Restart to the same boundary before comparing alternative actions when the environment is not reversibly navigable.
5. Add the observed transition and reclose the quotient.
6. Stop when a successful program is compiled, the action/state budget is exhausted, or the residual identifies a missing observable/interface.

V1 does not claim optimal information gain. It uses a deterministic “largest block split, then shortest probe” policy so qualification can be replayed exactly.

### 4.4 Existing semantic closure integration

`close_path_capabilities` gains one final generic fallback after the earned static recognizers:

```text
static reusable recognizer succeeds -> use it at zero probe cost
static recognizer returns a named residual -> invoke protected-future discovery if allowed
discovery qualifies a quotient -> compile/store capability and execute it
discovery is incomplete -> preserve UNKNOWN residual
```

This ordering enforces “never pay twice”: G3–G5 continue to use their compiled recognizers, while a new level pays intervention cost only until its quotient/interface has been learned.

## 5. Protected observation contract

The default ARC boundary contains only consequential public data:

- normalized visible frame relations, not raw object identity;
- legal action availability and typed response;
- progress/level/terminal outcome;
- target-panel state;
- control geometry and selected/active-port response when visible;
- action cost when the declared boundary protects budget.

Raw pixels may be retained as evidence but do not automatically become state coordinates. A feature enters the live quotient signature only after a separator shows that omitting it merges histories with different protected futures.

## 6. Failure semantics

The compiler fails closed with one exact residual:

- `exploration.incomplete@1`: the bound ended before stability was established;
- `transition.nondeterministic@1`: the same canonical state/action produced incompatible consequences;
- `quotient.control-congruence@1`: merged states require different controls or effects;
- `observation.separator@1`: a protected difference exists but the current observation language cannot express it;
- `target.projection@1`: a program is known but no warranted target-column projection is available;
- `terminal.oracle@1`: no independent progress/terminal consequence was observed.

No residual is silently converted into a guessed target.

## 7. Test and qualification strategy

Implementation is test-first.

### Generic unit gates

1. Exact minimal quotients on small hand-checkable deterministic machines.
2. Exhaustive comparison against full future equivalence for all three-state/two-action machines within a bounded census.
3. Shortest-separator minimality and deterministic tie-breaking.
4. Control-congruence counterexample: output-equivalent states that require different controls must not merge.
5. Parenthesization/traversal invariance of canonical capability identity.
6. Identity transition neutrality.
7. Incomplete graph returns `UNKNOWN` rather than a false quotient.
8. Transition nondeterminism is detected and preserved as a residual.

### ARC regression gates

1. G3–G5 compiled capabilities remain byte-for-byte behaviorally unchanged.
2. Color relocation, board translation, and control relocation preserve the learned quotient when protected relations are unchanged.
3. A metamorphic counterexample that changes the required control must split the quotient.
4. Ablating the learned separator restores the prior residual.

### G6 promotion gate

The cold learner receives no G6 semantic labels and no preselected 12→6 grouping. Promotion requires:

1. a stable six-column executable compression discovered from legal observations;
2. actual G6 progress;
3. two independent exact replays from the qualified boundary;
4. a hard-restart G1→G6 replay;
5. zero model calls and no source inspection;
6. an exact action budget and full evidence artifact;
7. one held-out or metamorphic transfer using the frozen learner with no new semantic code.

G6 progress without the held-out gate is `WARRANTED POSITIVE` for tn36 only, not `REUSABLE`.

## 8. Evidence and promotion

The qualification artifact records:

- parent SHA and exact head SHA;
- branch, workflow, run, job, artifact, and SHA-256 digest;
- explored states/transitions and declared bounds;
- final partition and canonical quotient ID;
- shortest separator for every non-equivalent pair;
- congruence result;
- compiled program and target projection;
- replay results and action counts;
- retained UNKNOWNs and ablation result.

The local branch remains `CANDIDATE` until the exact-head hosted workflow succeeds. A tn36-only success is not merged into the competition solver as a general capability. Promotion to `REUSABLE` requires frozen held-out transfer.

## 9. First implementation slice

The smallest meaningful slice is:

1. generic finite transducer records;
2. fixed-point refinement;
3. shortest separators;
4. control-congruence validation;
5. canonical capability identity;
6. exhaustive synthetic tests;
7. a read-only adapter that reconstructs the already observed G6 route-state graph and reports the exact remaining ambiguity.

Only after that slice passes will the live legal-intervention driver be allowed to write a G6 target. This separates correctness of quotient discovery from correctness of ARC actuation and prevents another target hypothesis from being disguised as a compiler.

## 10. Success criterion

V1 succeeds scientifically when one unchanged generic loop performs:

```text
observe -> quotient -> find shortest separator -> intervene -> reclose
        -> compile shortest successful program -> replay -> cache capability
```

and the frozen capability transports beyond the level that produced it. The implementation earns generality through held-out consequential equivalence, not through generic naming.
