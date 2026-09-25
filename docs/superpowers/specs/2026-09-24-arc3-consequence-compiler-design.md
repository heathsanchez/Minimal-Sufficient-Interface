# ARC Consequence Compiler V1 Design

## Objective

Build the smallest general ARC-3 capability that converts terminally warranted
interaction traces into reusable mappings from visible semantic effects to
output encodings.  The first qualification target is public tn36 G6, but the
promotion target is a reusable solver capability and measurable competition
coverage, not a G6-specific matrix.

The governing representation is:

```text
visible relation/effect -> protected output encoding
```

The compiler must discover this relation from successful interaction and keep
`UNKNOWN` explicit when a future effect has no warranted projection.

## Durable Starting Boundary

The implementation descends from
`arc3-public-protected-future-compiler-v1@d5d5c8607ccae497192fff2be95eb8423750a607`.
Its local boundary is 89 passing tests and deterministic standalone-agent digest
`sha256:2a9bce5637d3876ae5c48393f81f640a2f6dd682bbc4202f4302bb1bfad1769a`.
Hosted authority for that head is absent because the originating runtime could
not authenticate to GitHub.

The following evidence is input authority, each only on its declared boundary:

- G3 visible program induction: `URRRUR`, exact head
  `f5dbed6632ecacf15b5bd7df393cf5ed04ee5333`, run `35972752042`, two
  terminal replays.
- G4 scale-normalized docking: `ILDDDD`, local promoted evidence with two
  replays; hosted authority remains pending.
- G5 multicolor endpoint transform: `XDDDTS`, local promoted evidence with two
  replays; hosted authority remains pending.
- G6 direction roles and unique low-level route `RRRRUULLUUUL`.
- G6 negatives: OR, AND, XOR, equality-preserving cancellation, simple
  before/after selection, marker pre/post state, marker delta, stutter trace,
  waypoint suffix, and same-control port-role continuation.
- Generic protected-future compiler: canonical machines, bounded partition
  refinement, shortest separators, executable control retention, and typed
  residuals.

ROS is a discovery and coordination surface, not truth authority.  A ROS claim
may propose an adapter or experiment, but promotion requires the pinned source
and verifier evidence above.

## Central Diagnosis

The current solver compiles each solved level into a recognizer and final
program, then discards most of the successful semantic correspondence that made
the program work.  G3-G5 therefore contain supervised examples of the exact
relation G6 lacks, but those examples are not stored in a reusable form.

The G6 navigation quotient was computed relative to reaching the docking cell.
That recovers navigation correctly but does not answer the protected output
question.  The relevant boundary is successful target construction and submit
progress.

## Semantic Objects

### WarrantedEffectExample

Each successful output slot produces an immutable record:

```python
@dataclass(frozen=True)
class WarrantedEffectExample:
    before: RelationalObservation
    intervention: SemanticAction
    after: RelationalObservation
    effect: RelationalEffect
    output: tuple[int, ...]
    slot_index: int
    terminal_warrant: TerminalWarrant
    lineage: tuple[str, ...]
    example_id: str
```

`example_id` hashes canonical meaning-bearing fields.  Screen coordinates,
color names, filenames, insertion order, and Python object identity are not
semantic identity.

### RelationalObservation

The observation is a canonical, translation- and color-role-relative account
of visible objects and their relations.  It may include:

- normalized connected-component shapes and role indices;
- containment, adjacency, overlap, alignment and relative displacement;
- board-cell support and local legal-action structure;
- selector/control pose and active port;
- target-panel shape and slot ordering;
- stage-marker/event boundary;
- progress, terminal and available-action observations.

No coordinate is admitted merely because it is visible.  A coordinate remains
only when an existing warrant or a response separator shows that removing it
changes a protected output or continuation.

### RelationalEffect

An effect is the canonical difference between before and after relational
observations, including intermediate observations when an action is compiled
from multiple low-level controls.  It preserves object correspondences and
relations, rather than raw pixel subtraction.

### EffectProjectionAdapter

```python
@dataclass(frozen=True)
class EffectProjectionAdapter:
    interface_id: str
    classes: tuple[EffectClass, ...]
    outputs: tuple[tuple[str, tuple[int, ...]], ...]
    preserves: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    adapter_id: str
```

The adapter is partial.  A new effect that cannot be assigned to exactly one
warranted class returns:

```text
UNKNOWN(target.projection@1, unseen_or_ambiguous_effect_class)
```

It never falls back to nearest-neighbour guessing.

## Compiler Pipeline

### 1. Extract successful traces

Replay qualified G3-G5 paths in the public environment.  For every target slot,
record the full before/intermediate/after public observation, semantic action,
written output column, and terminal lineage.  Previously committed summary JSON
is not sufficient when it omits the frames required to reconstruct an effect.

### 2. Canonicalize effects

Convert frames into relational observations and effects.  Produce explicit
ablation variants that remove one feature family at a time.  Features survive
only when their removal merges examples with different warranted outputs or
breaks transport across solved levels.

### 3. Discover the coarsest output-preserving partition

Start from output equality and refine only when effect congruence or a protected
future response separates members.  The result is the coarsest witnessed
partition of effects that factors the solved output relation.

The discovery gate must report:

- number of examples and source levels;
- initial and final class counts;
- shortest separator for every rejected merge;
- ambiguous or unsupported effects as typed residuals;
- canonical adapter identity independent of example insertion order.

### 4. Compile a level plan

Existing board, goal, route, control-role and submit capabilities produce a
semantic plan.  The consequence compiler assigns one warranted effect class and
one output codeword to every target slot.  Compilation succeeds only if:

- target slot order is observable;
- every slot has exactly one effect class;
- every effect class has exactly one warranted output;
- the adapter preservation contract covers the current observation boundary;
- the compiled plan and executable controls are content-bound.

### 5. Select the next separator

When compilation returns `UNKNOWN`, enumerate only legal probes that distinguish
live adapter candidates.  Rank probes by the number of consequential candidate
classes they split, then by action cost.  Do not extend a probe bank merely
because a shallow search failed.

Before inventing a new feature, primitive or experiment, perform a targeted ROS
and repository reconciliation for the named residual:

1. search Canonical State, Checkpoints, Campaign Registry, Runbooks and Papers;
2. inspect exact source branches, runs and artifacts for matching positive or
   negative evidence;
3. reuse a qualified capability if its assumptions transport;
4. otherwise record why existing evidence does not close the residual;
5. run the cheapest remaining separator.

This consultation loop is part of experiment selection, not runtime dependence
of the Kaggle agent.

### 6. Verify and promote

A candidate mapping advances only after actual terminal progress.  A tn36 G6
promotion requires two independent exact hard-restart replays through G1-G6.
The adapter is then ablated; removal must restore the prior residual or failure.
The frozen adapter is evaluated on held-out/metamorphic traces and integrated
into the standalone agent only after those gates pass.

## G6 First Vertical Slice

The qualified low-level route has twelve moves and the target has six columns.
The first bounded factorization uses the six visible two-step/event boundaries:

```text
RR | RR | UU | LL | UU | UL
```

For each pair, construct:

```text
M_k = relational_effect(O_2k-2, O_2k-1, O_2k)
```

The experiment does not assume that a pair output is OR, AND, XOR, the first
control, the second control, or a named geometric pose.  It asks whether each
`M_k` belongs to an effect class already warranted by successful G3-G5 traces.

Outcomes are classified as follows:

- all six effects uniquely project and G6 progresses: `WARRANTED_POSITIVE`,
  pending two replays and ablation;
- an effect is novel or ambiguous: `UNKNOWN(target.projection@1, ...)` with the
  smallest live separator;
- the adapter uniquely projects all six but terminal progress fails:
  `WARRANTED_NEGATIVE` for that adapter boundary, while the generic effect
  representation survives unless independently falsified;
- harness or environment failure: `NON_EVIDENCE`.

## Evidence Integrity

- An evidence artifact must embed its exact source head, experiment digest,
  boundary, action count, target-write count and scientific classification.
- The workflow must regenerate live evidence rather than load static negatives
  and call them current qualification.
- A result whose embedded head, schema or capability ID differs from the
  executing source is stale and fails the seal.
- Replay equality covers adapter ID, effect classes, compiled outputs,
  executable controls and terminal consequence—not merely an optional program
  field.
- Unknown semantics and historical failures survive transport losslessly.

## Competition Integration

The standalone agent contains the frozen adapter and relational recognizer, not
the ROS corpus or hosted experiment machinery.  At runtime it follows:

```text
observe -> close known interfaces -> compile -> execute
       -> typed residual -> bounded legal separator -> reclose
```

Every newly qualified adapter is measured against the current public/regression
suite.  A Kaggle submission is produced only when local or hosted evaluation
shows a non-regressing coverage gain.  If authenticated submission is
unavailable, the exact artifact and SHA-256 digest are preserved for upload.

## Non-Goals

- arbitrary target-matrix search;
- unrestricted action BFS or program synthesis;
- treating ROS prose as training truth;
- a universal ARC ontology;
- adding time, geometry, ownership or history to the core without a separator;
- claiming leaderboard improvement from tn36 progress alone.

## Success Criteria

The first implementation milestone is complete when it:

1. deterministically reconstructs warranted slot examples from G3-G5;
2. discovers a canonical output-preserving effect quotient;
3. returns a unique G6 projection or a smaller typed residual;
4. preserves all current tests and standalone build determinism;
5. regenerates its evidence under workflow control;
6. records exact lineage and ROS state without overstating hosted authority.

The campaign milestone is G6 progress reproduced twice.  The competition
milestone is a verified non-regressing submission artifact with measurable
coverage gain.  The objective remains first place on the ARC-3 Kaggle
leaderboard.
