# ARC-3 Protected-Future Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a game-independent finite transducer learner that discovers the coarsest protected-future quotient, compiles a shortest successful program, integrates it behind the existing ARC semantic closure, and qualifies the frozen learner on G6 plus a held-out/metamorphic transfer.

**Architecture:** A dependency-free `protected_future.py` owns canonical finite-machine semantics, refinement, separators, congruence, program extraction, and capability identity. A separate `future_arc.py` converts public visible ARC observations and legal responses into that core. `semantic_path.py` remains the static zero-probe fast path and invokes discovery only at a named residual.

**Tech Stack:** Python 3.12 standard library, immutable dataclasses, `unittest`, existing `metalogic_arc3` geometry functions, public `arcengine` only in qualification experiments.

**Spec:** `docs/superpowers/specs/2026-09-24-arc3-protected-future-compiler-design.md`

## Global Constraints

- No game-source inspection, hidden answer access, arbitrary 36-bit search, or model calls inside deterministic qualification.
- Generic compiler code contains no ARC colors, coordinates, glyph names, level names, or tn36 route/program constants.
- Finite results are warranted only on their explicit reachable-state/action/horizon boundary.
- Incomplete exploration, nondeterminism, failed congruence, absent projection, and absent terminal evidence return typed `UNKNOWN` residuals.
- Static compiled G3–G5 recognizers remain the zero-probe path and must not regress.
- G6 promotion requires progress, two independent exact replays, hard-restart G1→G6 replay, full evidence, ablation, and frozen held-out/metamorphic transfer.

## Review Focus

- Duplicate transitions arriving in different insertion orders must produce the same quotient and content ID; Task 1 pins canonical ordering.
- A partial transition table must never be reported as a total stable quotient; Task 2 pins `exploration.incomplete@1`.
- Output-equivalent states requiring different controls/effects must remain separated; Task 2 pins typed control congruence.
- Cycles and unreachable accepting states must terminate deterministically and return a residual rather than loop; Task 3 pins both cases.
- Array-backed/current-frame wrappers and relocated ARC geometry must normalize without importing level-specific constants; Task 4 pins both forms.

---

### Task 1: Canonical finite-machine objects

**Files:**
- Create: `kaggle/src/metalogic_arc3/protected_future.py`
- Create: `kaggle/tests/test_protected_future.py`

**Interfaces:**
- Consumes: Python hashable state/action/observation/effect values.
- Produces: `Transition`, `ExplorationBoundary`, `UnknownResidual`, `FiniteMachine`, `canonical_digest(value)`, and `FiniteMachine.build(...)`.

- [ ] **Step 1: Write failing canonicalization tests**

```python
class ProtectedFutureObjects(unittest.TestCase):
    def test_transition_insertion_order_is_identity_neutral(self):
        transitions = (
            Transition("s0", "a", "s1", "open", "move"),
            Transition("s1", "a", "s1", "win", "terminal"),
        )
        left = FiniteMachine.build(
            states=("s1", "s0"), actions=("a",), transitions=transitions,
            observations={"s0": "open", "s1": "win"},
            accepting={"s1"}, boundary=ExplorationBoundary(("a",), 2, 2),
        )
        right = FiniteMachine.build(
            states=("s0", "s1"), actions=("a",), transitions=tuple(reversed(transitions)),
            observations={"s1": "win", "s0": "open"},
            accepting={"s1"}, boundary=ExplorationBoundary(("a",), 2, 2),
        )
        self.assertEqual(left.content_id, right.content_id)

    def test_conflicting_duplicate_transition_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "nondeterministic_transition"):
            FiniteMachine.build(
                states=("s0", "s1", "s2"), actions=("a",),
                transitions=(
                    Transition("s0", "a", "s1", 0, "move"),
                    Transition("s0", "a", "s2", 0, "move"),
                ),
                observations={"s0": 0, "s1": 0, "s2": 0}, accepting=set(),
                boundary=ExplorationBoundary(("a",), 1, 3),
            )
```

- [ ] **Step 2: Run the new tests and confirm the import fails**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_protected_future -v`

Expected: `ModuleNotFoundError: No module named 'metalogic_arc3.protected_future'`.

- [ ] **Step 3: Implement immutable records and canonical encoding**

Implement sorted, tagged JSON encoding with compact separators and SHA-256. `FiniteMachine.build` must validate referenced states/actions, collapse identical duplicate transitions, reject conflicting duplicates, sort every set/map by canonical encoding, and compute `content_id` from semantic fields only.

```python
@dataclass(frozen=True)
class Transition:
    source: Hashable
    action: Hashable
    target: Hashable
    observation: Hashable
    effect: Hashable
    required_control: Hashable | None = None

@dataclass(frozen=True)
class ExplorationBoundary:
    actions: tuple[Hashable, ...]
    max_depth: int
    max_states: int

@dataclass(frozen=True)
class UnknownResidual:
    missing_interface: str
    reason: str
    evidence: tuple[str, ...] = ()
```

- [ ] **Step 4: Run the object tests**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_protected_future.ProtectedFutureObjects -v`

Expected: both tests pass.

- [ ] **Step 5: Commit the canonical object boundary**

```bash
git add kaggle/src/metalogic_arc3/protected_future.py kaggle/tests/test_protected_future.py
git commit -m "Add canonical protected-future machine objects"
```

### Task 2: Fixed-point quotient, shortest separators, and congruence

**Files:**
- Modify: `kaggle/src/metalogic_arc3/protected_future.py`
- Modify: `kaggle/tests/test_protected_future.py`

**Interfaces:**
- Consumes: `FiniteMachine` from Task 1.
- Produces: `FutureQuotient`, `refine_partition(machine)`, `shortest_separator(machine, left, right)`, and `check_congruence(machine, classes)`.

- [ ] **Step 1: Add failing refinement and separator tests**

```python
class ProtectedFutureRefinement(unittest.TestCase):
    def test_refinement_finds_coarsest_future_classes_and_shortest_witness(self):
        machine = binary_counter_machine()
        quotient = refine_partition(machine)
        self.assertEqual(quotient.classes, (("dead0", "dead1"), ("live0",), ("live1",)))
        self.assertEqual(shortest_separator(machine, "live0", "live1"), ("tick",))
        self.assertTrue(quotient.congruent)

    def test_required_control_prevents_output_only_merge(self):
        machine = control_counterexample_machine()
        quotient = refine_partition(machine)
        self.assertNotEqual(quotient.class_of("left"), quotient.class_of("right"))

    def test_partial_machine_returns_incomplete_residual(self):
        result = refine_partition(partial_machine())
        self.assertEqual(result.residual.missing_interface, "exploration.incomplete@1")
```

Define `binary_counter_machine`, `control_counterexample_machine`, and `partial_machine` as explicit two- to four-state fixtures in the same test file.

- [ ] **Step 2: Run and confirm missing API failures**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_protected_future.ProtectedFutureRefinement -v`

Expected: import or attribute failures for the refinement API.

- [ ] **Step 3: Implement refinement and witness extraction**

Start from blocks keyed by `(observation, accepting, outgoing_effects, required_controls)`. Repeatedly split each block by the tuple of successor block IDs in canonical action order. Refuse a final quotient when any reachable state lacks a transition for an action declared total by the boundary. Compute distinguishing words by breadth-first search over state pairs; include the empty word when protected observations already differ.

```python
@dataclass(frozen=True)
class FutureQuotient:
    classes: tuple[tuple[Hashable, ...], ...]
    transition_classes: tuple[tuple[int, Hashable, int], ...]
    witnesses: tuple[tuple[Hashable, Hashable, tuple[Hashable, ...]], ...]
    congruent: bool
    quotient_id: str
    residual: UnknownResidual | None = None

    def class_of(self, state: Hashable) -> int:
        for index, block in enumerate(self.classes):
            if state in block:
                return index
        raise KeyError(state)
```

- [ ] **Step 4: Add exhaustive three-state/two-action equivalence census**

Enumerate every deterministic transition table on three states for two actions and every nonconstant binary observation. For every state pair, compare `shortest_separator` against exhaustive closure of the generated transition monoid. Assert exact agreement and print `machines_checked`, `pairs_checked`, and maximum separator depth.

- [ ] **Step 5: Run focused and exhaustive gates**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_protected_future.ProtectedFutureRefinement -v`

Expected: all focused and exhaustive tests pass with zero mismatches.

- [ ] **Step 6: Commit the quotient kernel**

```bash
git add kaggle/src/metalogic_arc3/protected_future.py kaggle/tests/test_protected_future.py
git commit -m "Compile protected-future quotients and separators"
```

### Task 3: Program extraction, residuals, and capability identity

**Files:**
- Modify: `kaggle/src/metalogic_arc3/protected_future.py`
- Modify: `kaggle/tests/test_protected_future.py`

**Interfaces:**
- Consumes: a congruent `FutureQuotient`, start state, accepting states, preservation interfaces.
- Produces: `CompiledCapability`, `shortest_accepting_program(...)`, and `compile_capability(...)`.

- [ ] **Step 1: Add failing program/capability tests**

```python
class ProtectedFutureCompilation(unittest.TestCase):
    def test_shortest_program_terminates_on_cycles(self):
        capability = compile_capability(cyclic_success_machine(), "start", ("obs@1", "control@1"))
        self.assertEqual(capability.program, ("right", "submit"))

    def test_unreachable_terminal_is_unknown(self):
        result = compile_capability(unreachable_machine(), "start", ("obs@1",))
        self.assertEqual(result.missing_interface, "terminal.oracle@1")

    def test_parenthesization_metadata_does_not_change_identity(self):
        left = compile_capability(success_machine(), "start", ("a@1", "b@1"), lineage=(("A", "B"), "C"))
        right = compile_capability(success_machine(), "start", ("a@1", "b@1"), lineage=("A", ("B", "C")))
        self.assertEqual(left.capability_id, right.capability_id)
```

- [ ] **Step 2: Run and confirm missing compilation failures**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_protected_future.ProtectedFutureCompilation -v`

Expected: failures for undefined compilation functions/types.

- [ ] **Step 3: Implement shortest-program extraction and compilation guards**

Use BFS over quotient classes with canonical action ordering and a visited set. Flatten lineage to ordered semantic leaves before hashing. Compile only when refinement is complete, congruence passes, and an accepting class is reachable.

```python
@dataclass(frozen=True)
class CompiledCapability:
    interface_id: str
    capability_id: str
    quotient_id: str
    start_class: int
    accepting_classes: tuple[int, ...]
    program: tuple[Hashable, ...]
    preserves: tuple[str, ...]
    lineage: tuple[str, ...]
```

- [ ] **Step 4: Run Task 3 and full generic-core tests**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_protected_future -v`

Expected: all pass; cycles terminate; unreachable terminal returns `UNKNOWN`.

- [ ] **Step 5: Commit executable capability compilation**

```bash
git add kaggle/src/metalogic_arc3/protected_future.py kaggle/tests/test_protected_future.py
git commit -m "Compile shortest programs from future quotients"
```

### Task 4: ARC visible-transition adapter

**Files:**
- Create: `kaggle/src/metalogic_arc3/future_arc.py`
- Create: `kaggle/tests/test_future_arc.py`
- Reuse without changing behavior: `kaggle/src/metalogic_arc3/semantic_path.py`

**Interfaces:**
- Consumes: visible frames, public action labels/click points, returned frames, progress/level/state metadata.
- Produces: `ArcObservation`, `ArcTraceBuilder.record(...)`, `ArcTraceBuilder.machine(...)`, and `relational_signature(frame)`.

- [ ] **Step 1: Add failing normalization and relocation tests**

```python
class ArcFutureAdapterContracts(unittest.TestCase):
    def test_array_backed_latest_frame_normalizes(self):
        trace = ArcTraceBuilder(actions=("U", "D", "L", "R"), max_depth=4, max_states=16)
        state = trace.observe(ArrayBackedFrame(g6_control_fixture()), level=5, terminal=False)
        self.assertEqual(state.signature, relational_signature(g6_control_fixture()))

    def test_translation_and_color_relabel_preserve_relational_signature(self):
        original = relational_signature(g3_fixture(alternating_bars=True))
        transformed = relational_signature(relocate_and_recolor(g3_fixture(alternating_bars=True)))
        self.assertEqual(original, transformed)

    def test_incompatible_repeated_response_is_typed_unknown(self):
        trace = contradictory_trace()
        result = trace.machine()
        self.assertEqual(result.missing_interface, "transition.nondeterministic@1")
```

- [ ] **Step 2: Run and confirm adapter import failure**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_future_arc -v`

Expected: import failure for `metalogic_arc3.future_arc`.

- [ ] **Step 3: Implement relational observation and trace construction**

`relational_signature` must use normalized component geometry, board-relative positions, control-local geometry, target-panel bits, progress/terminal metadata, and optional active-port observations. It must exclude absolute colors and global translation where existing relations are preserved. `ArcTraceBuilder` assigns content identities to observed signatures and emits `FiniteMachine` only when the declared boundary is complete; otherwise it emits the exact residual.

- [ ] **Step 4: Add a control-choice metamorphic counterexample**

Create two relocated fixtures with identical protected panel output but swapped local control roles. Assert their output-only signatures would merge, while `ArcTraceBuilder.machine()` retains distinct required-control effects and the quotient separates them.

- [ ] **Step 5: Run adapter and existing semantic-path regressions**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_future_arc tests.test_semantic_path -v`

Expected: all tests pass and G3–G5 expected programs remain unchanged.

- [ ] **Step 6: Commit the ARC adapter**

```bash
git add kaggle/src/metalogic_arc3/future_arc.py kaggle/tests/test_future_arc.py
git commit -m "Adapt visible ARC traces to future quotients"
```

### Task 5: Integrate discovery behind semantic closure

**Files:**
- Modify: `kaggle/src/metalogic_arc3/semantic_path.py`
- Modify: `kaggle/tests/test_semantic_path.py`
- Modify: `kaggle/src/metalogic_arc3/__init__.py`

**Interfaces:**
- Consumes: existing static closure result plus optional `ArcTraceBuilder`/compiled capability.
- Produces: `close_path_capabilities(grid, discovery=None)` with static-first, fail-closed discovery fallback.

- [ ] **Step 1: Add failing static-first/fallback tests**

```python
def test_static_g3_capability_does_not_invoke_discovery(self):
    discovery = ExplodingDiscovery()
    closure = close_path_capabilities(g3_fixture(alternating_bars=True), discovery=discovery)
    self.assertEqual(closure.plan.path, "URRRUR")
    self.assertFalse(discovery.called)

def test_named_residual_can_be_closed_by_compiled_capability(self):
    capability = fixture_compiled_capability(program=("R", "U"))
    closure = close_path_capabilities(unknown_fixture(), discovery=FrozenDiscovery(capability))
    self.assertEqual(closure.plan.path, "RU")
    self.assertIn("program.protected-future-quotient@1", closure.closed_interfaces)

def test_incomplete_discovery_preserves_unknown(self):
    closure = close_path_capabilities(unknown_fixture(), discovery=IncompleteDiscovery())
    self.assertEqual(closure.residual.missing_interface, "exploration.incomplete@1")
```

- [ ] **Step 2: Run and verify the old signature rejects discovery**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_semantic_path.SemanticPathContracts -v`

Expected: failures showing `close_path_capabilities` does not accept `discovery`.

- [ ] **Step 3: Add the optional fallback without changing static branches**

The existing G3–G5 recognizer flow remains byte-for-byte behaviorally equivalent. Invoke discovery only after static closure returns a named residual, convert a compiled action tuple into `SemanticPathPlan`, append `program.protected-future-quotient@1`, and preserve discovery residuals unchanged.

- [ ] **Step 4: Run the full Kaggle suite and deterministic build**

Run: `cd kaggle && PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v`

Run twice: `cd kaggle && PYTHONPATH=src python scripts/build_agent.py && sha256sum agent/my_agent.py`

Expected: all tests pass; both generated-agent digests are identical.

- [ ] **Step 5: Commit semantic-closure integration**

```bash
git add kaggle/src/metalogic_arc3/semantic_path.py kaggle/src/metalogic_arc3/__init__.py kaggle/tests/test_semantic_path.py
git commit -m "Close ARC residuals through protected-future discovery"
```

### Task 6: Read-only G6 quotient diagnostic

**Files:**
- Create: `experiments/arc3_public_g6_future_quotient.py`
- Create: `.github/workflows/arc3-public-g6-future-quotient.yml`
- Create at runtime: `evidence/arc3-public-g6-future-quotient/result.json`

**Interfaces:**
- Consumes: the exact qualified G6 entry routine, legal public actions, visible consequences, generic learner.
- Produces: a bounded diagnostic artifact containing route-state graph, quotient, separators, exact residual, and no target write.

- [ ] **Step 1: Write a local offline contract test for artifact schema**

Add `kaggle/tests/test_g6_evidence_schema.py` with a fixture artifact and assert required fields: parent/head, boundary, states, transitions, classes, witnesses, congruence, residual, action count, model calls, source inspection, and target writes.

- [ ] **Step 2: Run schema test and confirm the experiment module is absent**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_g6_evidence_schema -v`

Expected: failure importing or locating `arc3_public_g6_future_quotient`.

- [ ] **Step 3: Implement deterministic public G6 observation**

Enter G6 through existing qualified G1–G5 routines. Reproduce the unique route only as an external qualification oracle, record all 13 route positions and locally legal responses, and call the generic learner. The script must set `target_writes=0`, `model_calls=0`, and `source_inspection=false`. It reports `DIAGNOSTIC` unless the graph itself establishes a compiled target projection.

- [ ] **Step 4: Run the diagnostic with a strict action budget**

Run using the pinned public environment with `ENVROOT`, `OUTDIR`, repository `experiments`, and `kaggle/src` on `PYTHONPATH`.

Expected: `ARC3_PUBLIC_G6_FUTURE_QUOTIENT=DIAGNOSTIC` or `ARC3_PUBLIC_G6_FUTURE_QUOTIENT=CANDIDATE`; never `PROMOTED` without target progress and replays.

- [ ] **Step 5: Validate artifact and regressions**

Run: `cd kaggle && PYTHONPATH=src python -m unittest tests.test_g6_evidence_schema tests.test_protected_future tests.test_future_arc tests.test_semantic_path -v`

Expected: all pass; artifact identifies either a stable quotient or one exact missing separator/interface.

- [ ] **Step 6: Commit the diagnostic boundary**

```bash
git add experiments/arc3_public_g6_future_quotient.py .github/workflows/arc3-public-g6-future-quotient.yml evidence/arc3-public-g6-future-quotient/result.json kaggle/tests/test_g6_evidence_schema.py
git commit -m "Diagnose G6 through protected-future quotienting"
```

### Task 7: Live G6 compilation, replay, ablation, and transfer

**Files:**
- Modify: `experiments/arc3_public_g6_future_quotient.py`
- Modify: `.github/workflows/arc3-public-g6-future-quotient.yml`
- Modify only if compiler discovers a lawful interface: `kaggle/src/metalogic_arc3/future_arc.py`
- Modify only if integration is required: `kaggle/src/metalogic_arc3/semantic_path.py`
- Update at runtime: `evidence/arc3-public-g6-future-quotient/result.json`

**Interfaces:**
- Consumes: the frozen generic compiler and diagnostic residual from Task 6.
- Produces: either a replayed G6 capability plus transfer evidence, or one smaller exact `UNKNOWN` residual.

- [ ] **Step 1: Convert only the diagnostic’s exact residual into one legal separator probe**

Add the minimum public observation or action suffix named by Task 6. Do not add a G6 route grouping, target matrix, Boolean operator family, or level-specific output constant. Record the before/after version space in the artifact.

- [ ] **Step 2: Run the separator and reclose the quotient**

Expected: the quotient strictly refines, compiles a target projection, or returns a smaller named residual. A no-change probe is classified `RESPONSE_SEPARATOR_ONLY` or `WARRANTED NEGATIVE`, not silently replaced.

- [ ] **Step 3: If compiled, execute one G6 candidate and inspect terminal progress**

Expected promotion precondition: `levels_completed` increases or state becomes `WIN`. Otherwise preserve the candidate as `WARRANTED NEGATIVE` and stop target writes until another earned separator exists.

- [ ] **Step 4: Replay successful semantics twice from the declared G6 boundary**

Record exact action sequences, target columns, starting frame IDs, ending progress, and action counts. Both replays must agree.

- [ ] **Step 5: Run hard-restart G1→G6 and exact ablation**

Hard restart must reproduce G1–G5 and the compiled G6 result. Removing the newly learned separator/interface must restore the Task 6 residual or eliminate G6 progress.

- [ ] **Step 6: Run a frozen held-out/metamorphic transfer**

Apply only relation-preserving color/control/board relocation first. Then run the frozen compiler on the next untouched public residual available without changing generic code. Report tn36-only success as `WARRANTED POSITIVE`; report `REUSABLE` only if frozen transfer passes.

- [ ] **Step 7: Run full regression and deterministic artifact build**

Run: `cd kaggle && PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v`

Run the G6 experiment twice and compare semantic artifact fields after excluding timestamps/run IDs.

Expected: all tests pass; semantic evidence is identical across replays.

- [ ] **Step 8: Commit the qualified result**

```bash
git add experiments/arc3_public_g6_future_quotient.py .github/workflows/arc3-public-g6-future-quotient.yml evidence/arc3-public-g6-future-quotient/result.json kaggle/src/metalogic_arc3 kaggle/tests
git commit -m "Qualify ARC3 protected-future capability"
```

### Task 8: Hosted evidence, ROS synchronization, and competition artifact

**Files:**
- Modify only after qualification: `kaggle/provenance/sources.json`
- Create through existing build: `kaggle/agent/my_agent.py`
- Create through existing build: `kaggle/notebooks/submission.ipynb`
- Update externally: Research Checkpoints, Campaign Registry, Cold-Start Runbooks; update Canonical Research State if frontier changes.

**Interfaces:**
- Consumes: exact qualified head and hosted workflow result.
- Produces: hosted evidence identity, ROS lineage, deterministic Kaggle-ready artifact and digest.

- [ ] **Step 1: Push the exact branch and run the hosted workflow**

Capture branch, head SHA, run ID, job ID, artifact ID, artifact SHA-256, test count, classification, and claim boundary. A failed workflow is `NON-EVIDENCE`.

- [ ] **Step 2: Verify hosted artifact digest and replay fields**

Download the artifact, hash it independently, and compare its semantic result fields against the committed local evidence.

- [ ] **Step 3: Update ROS with exact epistemic status**

Record hypothesis, branch/head, run/job/artifact/digest, result, interpretation, falsified family, retained UNKNOWNs, and next smallest residual. Do not label tn36-only progress `REUSABLE`.

- [ ] **Step 4: Build and hash the Kaggle notebook only after reusable transfer**

Run: `cd kaggle && make test && make notebook && sha256sum agent/my_agent.py notebooks/submission.ipynb`

Expected: tests pass and exact artifact hashes are recorded. Do not submit unless local/hosted evidence predicts a material score gain.

- [ ] **Step 5: Commit provenance metadata**

```bash
git add kaggle/provenance/sources.json
git commit -m "Record protected-future compiler qualification"
```
