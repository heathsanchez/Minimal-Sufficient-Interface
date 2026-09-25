# ARC Consequence Compiler V1 Implementation Plan

> **For implementers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended for these tightly coupled interfaces), or use superpowers:subagent-driven-development only after explicit user approval. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Learn a canonical partial mapping from terminally warranted relational effects to ARC target columns, apply it to the six G6 macro-effects, and either progress G6 or return the smallest typed projection residual.

**Architecture:** A new dependency-free `consequence_arc.py` owns effect examples, output-preserving partitions, projection adapters, and compilation. `future_arc.py` converts public frames into relational observations/effects; public experiments regenerate supervised G3-G5 traces and qualify the G6 projection. The static semantic solver remains the fast path, while the compiled adapter is vendored into the standalone agent only after terminal qualification.

**Tech Stack:** Python 3.12 standard library, immutable dataclasses, `unittest`, existing `metalogic_arc3` canonical encoding, public `arcengine` only in hosted qualification experiments, GitHub Actions evidence sealing.

**Spec:** `docs/superpowers/specs/2026-09-24-arc3-consequence-compiler-design.md`

## Global Constraints

- Descend from `arc3-public-protected-future-compiler-v1@d5d5c8607ccae497192fff2be95eb8423750a607` without rewriting historical evidence.
- No game-source inspection, hidden-answer access, arbitrary target matrices, unrestricted action BFS, or model calls inside deterministic qualification.
- ROS prose may suggest experiments but cannot supply training truth or promote a capability.
- All unknown or ambiguous effects return typed `UNKNOWN(target.projection@1, ...)`; never use nearest-neighbour fallback.
- G6 promotion requires actual progress, two independent G1-G6 hard-restart replays, adapter ablation, exact evidence identity, and zero regressions.
- Before inventing a feature or experiment for a named residual, reconcile Canonical State, Checkpoints, Campaign Registry, Runbooks, Papers, exact branches, runs, artifacts, and preserved negatives.
- Standalone Kaggle output must be deterministic, self-contained, offline and CPU-only.

## Review Focus

- Two examples with byte-different frames but identical relational meaning must share an effect ID; Task 2 pins translation/color-role invariance.
- One effect class mapped to two different warranted outputs must fail closed rather than select one; Task 3 pins `conflicting_warranted_outputs`.
- An unseen G6 macro-effect must remain `UNKNOWN` and cause zero target writes; Tasks 3 and 5 pin this boundary.
- Stale evidence whose embedded head or adapter ID differs from the executing source must fail the workflow seal; Task 5 pins both mismatches.
- Replays that agree only on program text but differ in adapter identity, classes, outputs or controls must not promote; Task 5 pins full replay equality.
- Adding equivalent evidence may change `warrant_id` but must not change semantic `adapter_id`; Task 3 keeps description separate from authority.

---

### Task 1: Canonical effect and warrant objects

**Files:**
- Create: `kaggle/src/metalogic_arc3/consequence_arc.py`
- Create: `kaggle/tests/test_consequence_arc.py`
- Modify: `kaggle/src/metalogic_arc3/__init__.py`

**Interfaces:**
- Consumes: `canonical_digest(value)` and `UnknownResidual` from `protected_future.py`.
- Produces: `RelationalObservation`, `SemanticAction`, `RelationalEffect`, `TerminalWarrant`, `WarrantedEffectExample`, and canonical `.build(...)` constructors.

- [ ] **Step 1: Write failing object-identity and validation tests**

```python
class ConsequenceObjects(unittest.TestCase):
    def test_example_identity_ignores_construction_order(self):
        before = RelationalObservation.build(objects={"b", "a"}, relations={("a", "left", "b")})
        after = RelationalObservation.build(objects={"a", "b"}, relations={("a", "aligned", "b")})
        left = WarrantedEffectExample.build(
            before=before,
            intervention=SemanticAction("move", ("R",)),
            after=after,
            effect=RelationalEffect.build({"trace.occupancy@1": ((0, 0), (0, 1))}),
            intermediates=(), output=(0, 1, 0, 0, 0, 0), slot_index=0,
            terminal_warrant=TerminalWarrant("PROGRESS", "run:1"), lineage=("G3",),
        )
        right = WarrantedEffectExample.build(
            before=before,
            intervention=SemanticAction("move", ("R",)),
            after=after,
            effect=RelationalEffect.build({"trace.occupancy@1": ((0, 0), (0, 1))}),
            intermediates=(), output=(0, 1, 0, 0, 0, 0), slot_index=0,
            terminal_warrant=TerminalWarrant("PROGRESS", "run:1"), lineage=("G3",),
        )
        self.assertEqual(left.example_id, right.example_id)

    def test_unwarranted_example_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "terminal_warrant_required"):
            WarrantedEffectExample.build(
                before=fixture_observation(), intervention=SemanticAction("move", ("R",)),
                after=fixture_observation(),
                effect=RelationalEffect.build({"trace.occupancy@1": ()}),
                intermediates=(), output=(0,), slot_index=0,
                terminal_warrant=TerminalWarrant("UNKNOWN", "none"), lineage=("G3",),
            )
```

- [ ] **Step 2: Run the tests and confirm missing imports**

Run: `PYTHONPATH=kaggle/src python -m unittest kaggle.tests.test_consequence_arc.ConsequenceObjects -v`

Expected: FAIL because `metalogic_arc3.consequence_arc` does not exist.

- [ ] **Step 3: Implement immutable canonical objects**

```python
@dataclass(frozen=True)
class RelationalObservation:
    objects: tuple[Hashable, ...]
    relations: tuple[Hashable, ...]
    observation_id: str

    @classmethod
    def build(cls, *, objects, relations):
        objects = tuple(sorted(set(objects), key=canonical_digest))
        relations = tuple(sorted(set(relations), key=canonical_digest))
        return cls(objects, relations, canonical_digest(("relational-observation@1", objects, relations)))

@dataclass(frozen=True)
class SemanticAction:
    family: str
    controls: tuple[Hashable, ...]

@dataclass(frozen=True)
class RelationalEffect:
    features: tuple[tuple[str, Hashable], ...]
    effect_id: str

    @classmethod
    def build(cls, features):
        normalized = tuple(sorted(features.items()))
        return cls(normalized, canonical_digest(("relational-effect@1", normalized)))

    def project(self, families):
        selected = set(families)
        return tuple((name, value) for name, value in self.features if name in selected)

@dataclass(frozen=True)
class TerminalWarrant:
    consequence: str
    evidence_ref: str

@dataclass(frozen=True)
class WarrantedEffectExample:
    before: RelationalObservation
    intervention: SemanticAction
    intermediates: tuple[RelationalObservation, ...]
    after: RelationalObservation
    effect: RelationalEffect
    output: tuple[int, ...]
    slot_index: int
    terminal_warrant: TerminalWarrant
    lineage: tuple[str, ...]
    example_id: str

    @classmethod
    def build(
        cls, *, before, intervention, after, effect, intermediates, output,
        slot_index, terminal_warrant, lineage,
    ):
        if terminal_warrant.consequence not in {"PROGRESS", "WIN"}:
            raise ValueError("terminal_warrant_required")
        intermediates = tuple(intermediates)
        output = tuple(output)
        lineage = tuple(lineage)
        meaning = (
            "warranted-effect-example@1", before, intervention, intermediates,
            after, effect, output, slot_index, terminal_warrant, lineage,
        )
        return cls(
            before, intervention, intermediates, after, effect, output,
            slot_index, terminal_warrant, lineage, canonical_digest(meaning),
        )
```

Reuse `canonical_digest`; do not duplicate the canonical encoder.  Observation
IDs remain in example provenance, while `effect_id` hashes only the local,
translation/color-role invariant feature families.  This separation is a hard
transport requirement: two levels may have different whole boards but the same
local effect.

- [ ] **Step 4: Run object tests and the existing canonical tests**

Run: `PYTHONPATH=kaggle/src python -m unittest kaggle.tests.test_consequence_arc.ConsequenceObjects kaggle.tests.test_protected_future.ProtectedFutureObjects -v`

Expected: PASS.

- [ ] **Step 5: Commit the semantic object boundary**

```bash
git add kaggle/src/metalogic_arc3/consequence_arc.py kaggle/src/metalogic_arc3/__init__.py kaggle/tests/test_consequence_arc.py
git commit -m "Add canonical ARC consequence objects"
```

### Task 2: Frame-relative effect extraction

**Files:**
- Modify: `kaggle/src/metalogic_arc3/future_arc.py`
- Modify: `kaggle/tests/test_future_arc.py`
- Modify: `kaggle/src/metalogic_arc3/consequence_arc.py`
- Modify: `kaggle/tests/test_consequence_arc.py`

**Interfaces:**
- Consumes: public frame arrays, `relational_signature(frame)`, and Task 1 objects.
- Produces: `relational_observation(frame)`, `relational_effect(frames)`, and `macro_effect(frames, controls)`.

- [ ] **Step 1: Write failing invariance and intermediate-separator tests**

```python
class RelationalEffects(unittest.TestCase):
    def test_translation_and_color_relabel_preserve_effect_identity(self):
        left = macro_effect(
            (object_frame(1, 1, foreground=7), object_frame(1, 2, foreground=7)),
            ("R",),
        )
        right = macro_effect(
            (object_frame(4, 6, background=4, foreground=2),
             object_frame(4, 7, background=4, foreground=2)),
            ("R",),
        )
        self.assertEqual(left.effect.effect_id, right.effect.effect_id)

    def test_intermediate_relation_separates_equal_endpoints(self):
        clockwise = macro_effect((frame_a(), frame_top(), frame_a()), ("U", "D"))
        horizontal = macro_effect((frame_a(), frame_right(), frame_a()), ("R", "L"))
        self.assertNotEqual(clockwise.effect.effect_id, horizontal.effect.effect_id)
```

- [ ] **Step 2: Run tests and confirm the extractor is absent**

Run: `PYTHONPATH=kaggle/src python -m unittest kaggle.tests.test_future_arc.ArcFutureAdapterContracts.test_translation_and_color_relabel_preserve_effect_identity kaggle.tests.test_consequence_arc.RelationalEffects -v`

Expected: FAIL on missing `macro_effect`/`relational_observation`.

- [ ] **Step 3: Implement effect extraction without raw coordinates**

```python
def relational_observation(frame) -> RelationalObservation:
    _, cells, roles = relational_signature(frame)
    objects = tuple(("role", index, role) for index, role in enumerate(roles))
    relations = tuple(("cell", row, col, role) for row, col, role in cells)
    return RelationalObservation.build(objects=objects, relations=relations)

@dataclass(frozen=True)
class MacroEffect:
    action: SemanticAction
    observations: tuple[RelationalObservation, ...]
    effect: RelationalEffect

def _without_stutter(values):
    result = []
    for value in values:
        if not result or value != result[-1]:
            result.append(value)
    return tuple(result)

def local_effect_features(frames):
    grids = tuple(_matrix(frame) for frame in frames)
    if len(grids) < 2 or len({(len(grid), len(grid[0])) for grid in grids}) != 1:
        raise ValueError("effect_frame_shape")
    backgrounds = tuple(
        min(Counter(cell for row in grid for cell in row).items(), key=lambda item: (-item[1], repr(item[0])))[0]
        for grid in grids
    )
    colors = set().union(*(
        {cell for row in grid for cell in row if cell != background}
        for grid, background in zip(grids, backgrounds)
    ))
    foreground = [
        {(row, col): cell for row, line in enumerate(grid) for col, cell in enumerate(line)
         if cell != background}
        for grid, background in zip(grids, backgrounds)
    ]
    if not colors:
        return {"trace.empty@1": True, "action.arity@1": len(grids) - 1}
    all_cells = set().union(*(set(snapshot) for snapshot in foreground))
    origin = min(row for row, _ in all_cells), min(col for _, col in all_cells)
    descriptors = {
        color: tuple(
            tuple(sorted((row - origin[0], col - origin[1])
                         for (row, col), value in snapshot.items() if value == color))
            for snapshot in foreground
        )
        for color in colors
    }
    ordered_colors = tuple(sorted(colors, key=lambda color: canonical_digest(descriptors[color])))
    role = {color: index for index, color in enumerate(ordered_colors)}
    role_snapshots = tuple(
        {(row, col): role[color] for (row, col), color in snapshot.items()}
        for snapshot in foreground
    )
    dynamic = {
        cell for cell in all_cells
        if len({snapshot.get(cell) for snapshot in role_snapshots}) > 1
    }
    if not dynamic:
        dynamic = all_cells
    context = dynamic | {
        neighbor
        for row, col in dynamic
        for neighbor in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
        if neighbor in all_cells
    }
    local_origin = min(row for row, _ in context), min(col for _, col in context)
    roles = tuple(
        tuple(sorted((row - local_origin[0], col - local_origin[1], snapshot[(row, col)])
                     for row, col in context if (row, col) in snapshot))
        for snapshot in role_snapshots
    )
    occupancy = tuple(tuple((row, col) for row, col, _ in snapshot) for snapshot in roles)
    return {
        "action.arity@1": len(grids) - 1,
        "support.context@1": tuple(sorted((row - local_origin[0], col - local_origin[1]) for row, col in context)),
        "trace.occupancy@1": occupancy,
        "trace.roles@1": roles,
        "trace.stutter@1": _without_stutter(roles),
    }

def relational_effect(frames) -> RelationalEffect:
    return RelationalEffect.build(local_effect_features(frames))

def macro_effect(frames, controls) -> MacroEffect:
    observations = tuple(relational_observation(frame) for frame in frames)
    controls = tuple(controls)
    if len(observations) != len(controls) + 1:
        raise ValueError("macro_frame_control_arity")
    return MacroEffect(
        SemanticAction("macro", controls), observations,
        relational_effect(frames),
    )
```

Represent cell locations relative to the canonical non-background origin already established by `relational_signature`; do not retain absolute screen coordinates.

- [ ] **Step 4: Run all adapter/effect tests**

Run: `PYTHONPATH=kaggle/src python -m unittest kaggle.tests.test_future_arc kaggle.tests.test_consequence_arc -v`

Expected: PASS.

- [ ] **Step 5: Commit relational effect extraction**

```bash
git add kaggle/src/metalogic_arc3/future_arc.py kaggle/src/metalogic_arc3/consequence_arc.py kaggle/tests/test_future_arc.py kaggle/tests/test_consequence_arc.py
git commit -m "Extract canonical ARC relational effects"
```

### Task 3: Output-preserving effect quotient and partial adapter

**Files:**
- Modify: `kaggle/src/metalogic_arc3/consequence_arc.py`
- Modify: `kaggle/tests/test_consequence_arc.py`

**Interfaces:**
- Consumes: `Iterable[WarrantedEffectExample]` and unseen `RelationalEffect` values.
- Produces: `EffectClass`, `EffectProjectionAdapter.build(examples)`, `project(effect)`, `compile_projection(effects, adapter)`.

- [ ] **Step 1: Write failing partition, conflict and unseen-effect tests**

```python
class EffectProjectionContracts(unittest.TestCase):
    def test_equal_effects_with_equal_outputs_share_one_class(self):
        adapter = EffectProjectionAdapter.build((example("G3", "R", CODE_R), example("G4", "R", CODE_R)))
        self.assertEqual(len(adapter.classes), 1)
        self.assertEqual(adapter.project(example("G3", "R", CODE_R).effect), CODE_R)

    def test_conflicting_warranted_outputs_fail_closed(self):
        result = EffectProjectionAdapter.build((example("G3", "R", CODE_R), example("G4", "R", CODE_U)))
        self.assertIsInstance(result, UnknownResidual)
        self.assertEqual(result.reason, "conflicting_warranted_outputs")

    def test_unseen_effect_is_unknown(self):
        adapter = EffectProjectionAdapter.build((example("G3", "R", CODE_R),))
        result = adapter.project(example("G6", "novel", CODE_U).effect)
        self.assertEqual(result.missing_interface, "target.projection@1")

    def test_single_level_class_is_not_transport_authority(self):
        witnessed = example("G3", "R", CODE_R)
        adapter = EffectProjectionAdapter.build((witnessed,))
        result = adapter.project(witnessed.effect)
        self.assertEqual(result.reason, "untransported_effect_class")

    def test_nuisance_feature_does_not_block_cross_level_projection(self):
        g3_r = example_with_features(
            "G3", {"trace.occupancy@1": ("right",), "support.context@1": ("wide",)}, CODE_R
        )
        g4_r = example_with_features(
            "G4", {"trace.occupancy@1": ("right",), "support.context@1": ("tall",)}, CODE_R
        )
        g3_u = example_with_features(
            "G3", {"trace.occupancy@1": ("up",), "support.context@1": ("wide",)}, CODE_U
        )
        g4_u = example_with_features(
            "G4", {"trace.occupancy@1": ("up",), "support.context@1": ("tall",)}, CODE_U
        )
        adapter = EffectProjectionAdapter.build((g3_r, g4_r, g3_u, g4_u))
        transported = RelationalEffect.build(
            {"trace.occupancy@1": ("right",), "support.context@1": ("novel",)}
        )
        self.assertEqual(adapter.project(transported), CODE_R)

    def test_example_order_does_not_change_adapter_identity(self):
        examples = (example("G3", "R", CODE_R), example("G4", "U", CODE_U))
        self.assertEqual(
            EffectProjectionAdapter.build(examples).adapter_id,
            EffectProjectionAdapter.build(tuple(reversed(examples))).adapter_id,
        )

    def test_new_equivalent_evidence_changes_warrant_not_semantics(self):
        first = EffectProjectionAdapter.build((example("G3", "R", CODE_R),))
        reinforced = EffectProjectionAdapter.build(
            (example("G3", "R", CODE_R), example("G4", "R", CODE_R))
        )
        self.assertEqual(first.adapter_id, reinforced.adapter_id)
        self.assertNotEqual(first.warrant_id, reinforced.warrant_id)
```

- [ ] **Step 2: Run tests and confirm adapter methods are absent**

Run: `PYTHONPATH=kaggle/src python -m unittest kaggle.tests.test_consequence_arc.EffectProjectionContracts -v`

Expected: FAIL on missing `EffectProjectionAdapter`.

- [ ] **Step 3: Implement the coarsest witnessed output-preserving projection**

```python
from itertools import combinations

@dataclass(frozen=True)
class EffectClass:
    class_id: str
    signature: tuple[tuple[str, Hashable], ...]
    effect_ids: tuple[str, ...]
    output: tuple[int, ...]
    evidence_ids: tuple[str, ...]
    source_levels: tuple[str, ...]

@dataclass(frozen=True)
class EffectProjectionAdapter:
    interface_id: str
    families: tuple[str, ...]
    classes: tuple[EffectClass, ...]
    preserves: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    adapter_id: str
    warrant_id: str

    @classmethod
    def build(cls, examples):
        examples = tuple(examples)
        if not examples:
            return UnknownResidual("target.projection@1", "empty_training_set")
        by_effect: dict[str, list[WarrantedEffectExample]] = {}
        for example in examples:
            by_effect.setdefault(example.effect.effect_id, []).append(example)
        for group in by_effect.values():
            if len({item.output for item in group}) != 1:
                return UnknownResidual(
                    "target.projection@1", "conflicting_warranted_outputs",
                    tuple(sorted(item.example_id for item in group)),
                )
        available = tuple(sorted(set.intersection(*(
            {name for name, _ in example.effect.features} for example in examples
        ))))
        candidates = []
        for size in range(len(available) + 1):
            for families in combinations(available, size):
                grouped = {}
                for example in examples:
                    grouped.setdefault(example.effect.project(families), []).append(example)
                if all(len({item.output for item in group}) == 1 for group in grouped.values()):
                    partition = tuple(sorted(
                        tuple(sorted(item.example_id for item in group))
                        for group in grouped.values()
                    ))
                    candidates.append((len(grouped), size, partition, families, grouped))
        if not candidates:
            return UnknownResidual("target.projection@1", "no_output_preserving_interface")
        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        class_count, family_count, partition, families, grouped = candidates[0]
        tied_partitions = {
            item[2] for item in candidates
            if (item[0], item[1]) == (class_count, family_count)
        }
        if len(tied_partitions) != 1:
            return UnknownResidual(
                "target.projection@1", "ambiguous_minimal_preserving_interface",
                tuple(canonical_digest(item) for item in sorted(tied_partitions)),
            )
        classes = tuple(
            EffectClass(
                class_id=canonical_digest(
                    ("effect-class@1", signature, group[0].output)
                ),
                signature=signature,
                effect_ids=tuple(sorted({item.effect.effect_id for item in group})),
                output=group[0].output,
                evidence_ids=tuple(sorted(item.example_id for item in group)),
                source_levels=tuple(sorted({item.lineage[0] for item in group})),
            )
            for signature, group in sorted(grouped.items(), key=lambda item: canonical_digest(item[0]))
        )
        preserves = ("effect.relational@1", "target.column@1")
        evidence_ids = tuple(sorted(item.example_id for item in examples))
        semantic_classes = tuple(
            (block.class_id, block.signature, block.output) for block in classes
        )
        meaning = ("effect-projection-adapter@1", families, semantic_classes, preserves)
        adapter_id = canonical_digest(meaning)
        warrant_id = canonical_digest((
            "effect-projection-warrant@1", adapter_id, evidence_ids,
            tuple((block.class_id, block.evidence_ids, block.source_levels) for block in classes),
        ))
        return cls(
            "target.projection@1", families, classes, preserves, evidence_ids,
            adapter_id, warrant_id,
        )

    def project(self, effect):
        signature = effect.project(self.families)
        for block in self.classes:
            if signature == block.signature:
                if len(block.source_levels) < 2:
                    return UnknownResidual(
                        "target.projection@1", "untransported_effect_class",
                        (block.class_id,),
                    )
                return block.output
        return UnknownResidual("target.projection@1", "unseen_effect_class", (effect.effect_id,))

def compile_projection(effects, adapter):
    outputs = []
    unknown_ids = []
    for effect in effects:
        result = adapter.project(effect)
        if isinstance(result, UnknownResidual):
            unknown_ids.extend(result.evidence or (effect.effect_id,))
        else:
            outputs.append(result)
    if unknown_ids:
        return UnknownResidual(
            "target.projection@1", "unseen_or_ambiguous_effect_class",
            tuple(unknown_ids),
        )
    return tuple(outputs)
```

- [ ] **Step 4: Add and pass six-slot fail-closed compilation test**

```python
def test_compile_projection_writes_nothing_when_one_slot_is_unknown(self):
    adapter = EffectProjectionAdapter.build((example("G3", "R", CODE_R),))
    result = compile_projection((known_r_effect(), novel_effect()), adapter)
    self.assertIsInstance(result, UnknownResidual)
    self.assertEqual(result.evidence, (novel_effect().effect_id,))
```

Run: `PYTHONPATH=kaggle/src python -m unittest kaggle.tests.test_consequence_arc -v`

Expected: PASS.

- [ ] **Step 5: Commit the projection adapter**

```bash
git add kaggle/src/metalogic_arc3/consequence_arc.py kaggle/tests/test_consequence_arc.py
git commit -m "Compile partial ARC effect projections"
```

### Task 4: Regenerate terminally supervised G3-G5 trace corpus

**Files:**
- Create: `experiments/arc3_public_consequence_training.py`
- Create: `kaggle/tests/test_consequence_training_schema.py`
- Create at runtime: `evidence/arc3-public-consequence-training/result.json`
- Modify: `experiments/arc3_public_online_path_capability_g3.py`
- Modify: `experiments/arc3_public_online_scale_normalized_g4.py`
- Modify: `experiments/arc3_public_online_multicolor_g5.py`

**Interfaces:**
- Consumes: qualified G1-G5 replay helpers, exact successful paths and public frames.
- Produces: `record_warranted_level(level, path, frames, codes, warrant_ref)`, canonical examples, corpus ID, and frozen adapter JSON.

- [ ] **Step 1: Write failing schema and stale-lineage tests**

```python
class ConsequenceTrainingSchema(unittest.TestCase):
    def test_corpus_contains_six_warranted_slots_per_level(self):
        result = fixture_training_result()
        validate_training_result(result, executing_head="abc")
        self.assertEqual([len(level["examples"]) for level in result["levels"]], [6, 6, 6])

    def test_stale_head_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stale_evidence_head"):
            validate_training_result(fixture_training_result(), executing_head="other")

    def test_nonprogressing_trace_cannot_train_adapter(self):
        result = fixture_training_result()
        result["levels"][1]["terminal_warrant"]["consequence"] = "CONTINUE"
        with self.assertRaisesRegex(ValueError, "terminal_warrant_required"):
            validate_training_result(result, executing_head="abc")
```

- [ ] **Step 2: Run the schema tests and confirm experiment imports fail**

Run: `PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_consequence_training_schema -v`

Expected: FAIL because `arc3_public_consequence_training` does not exist.

- [ ] **Step 3: Implement trace recording around existing sessions**

```python
def record_warranted_level(*, level, path, slot_frames, codes, warrant_ref):
    if len(path) != 6 or len(slot_frames) != 6:
        raise ValueError("successful_slot_arity")
    warrant = TerminalWarrant("PROGRESS", warrant_ref)
    return tuple(
        WarrantedEffectExample.build(
            before=relational_observation(frames[0]),
            intervention=SemanticAction("program-slot", (operator,)),
            intermediates=tuple(relational_observation(frame) for frame in frames[1:-1]),
            after=relational_observation(frames[-1]),
            effect=relational_effect(frames),
            output=tuple(codes[operator]), slot_index=index,
            terminal_warrant=warrant, lineage=(f"tn36:G{level}", warrant_ref),
        )
        for index, (operator, frames) in enumerate(zip(path, slot_frames))
    )
```

Capture frames during legal selector probes and successful writes.  Do not synthesize frames from the known codebook.

- [ ] **Step 4: Run the exact public corpus generator**

Run from pinned Duck harness:

```bash
ENVROOT="$GITHUB_WORKSPACE/public-env" \
PYTHONPATH="$GITHUB_WORKSPACE/kaggle/src:$GITHUB_WORKSPACE/experiments" \
OUTDIR="$GITHUB_WORKSPACE/evidence/arc3-public-consequence-training" \
uv run python "$GITHUB_WORKSPACE/experiments/arc3_public_consequence_training.py"
```

Expected: `ARC3_PUBLIC_CONSEQUENCE_TRAINING=PASS`, G3/G4/G5 each progress, 18 warranted examples are emitted, and two independent corpus generations have identical corpus and adapter IDs.

- [ ] **Step 5: Run schema, ARC and full regression tests**

Run: `PYTHONPATH=kaggle/src:experiments python -m unittest discover -s kaggle/tests -v`

Expected: all tests pass.

- [ ] **Step 6: Commit corpus generation without claiming hosted authority**

```bash
git add experiments/arc3_public_consequence_training.py experiments/arc3_public_online_path_capability_g3.py experiments/arc3_public_online_scale_normalized_g4.py experiments/arc3_public_online_multicolor_g5.py kaggle/tests/test_consequence_training_schema.py
test ! -f evidence/arc3-public-consequence-training/result.json || git add evidence/arc3-public-consequence-training/result.json
git commit -m "Regenerate warranted ARC consequence traces"
```

If the public environment is unavailable, commit code/tests only and classify corpus evidence `UNKNOWN / EXTERNAL_BLOCKER`; do not fabricate `result.json`.

### Task 5: Compile and qualify the G6 macro-effect projection

**Files:**
- Create: `experiments/arc3_public_g6_consequence_projection.py`
- Create: `kaggle/tests/test_g6_consequence_projection_schema.py`
- Create: `.github/workflows/arc3-public-g6-consequence-projection.yml`
- Create at runtime: `evidence/arc3-public-g6-consequence-projection/result.json`
- Modify: `kaggle/src/metalogic_arc3/consequence_arc.py`

**Interfaces:**
- Consumes: frozen Task 4 adapter, exact G6 boundary, route `RRRRUULLUUUL`, and six three-frame macro traces.
- Produces: compiled six columns or `UnknownResidual`, full replay identity, terminal result, ablation and transfer evidence.

- [ ] **Step 1: Write failing macro-boundary and zero-write residual tests**

```python
class G6ConsequenceProjectionSchema(unittest.TestCase):
    def test_route_is_partitioned_into_six_ordered_macro_effects(self):
        self.assertEqual(pair_route("RRRRUULLUUUL"), ("RR", "RR", "UU", "LL", "UU", "UL"))

    def test_unknown_macro_effect_performs_zero_target_writes(self):
        result = fixture_g6_result(status="RESIDUAL", unknown_slots=(5,))
        validate_g6_result(result, executing_head="abc")
        self.assertEqual(result["target_writes"], 0)

    def test_replay_identity_includes_adapter_classes_outputs_and_controls(self):
        result = fixture_g6_result(status="PROMOTED")
        result["verification"][1]["adapter_id"] = "different"
        with self.assertRaisesRegex(ValueError, "replay_identity_mismatch"):
            validate_g6_result(result, executing_head="abc")
```

- [ ] **Step 2: Run tests and confirm the experiment is absent**

Run: `PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_consequence_projection_schema -v`

Expected: FAIL on missing experiment import.

- [ ] **Step 3: Implement bounded six-effect compilation**

```python
PAIRS = ("RR", "RR", "UU", "LL", "UU", "UL")

@dataclass(frozen=True)
class MacroTrace:
    frames: tuple[tuple[tuple[int, ...], ...], ...]
    controls: tuple[str, ...]

@dataclass(frozen=True)
class G6Boundary:
    control_points: dict[str, tuple[int, int]]
    target_cells: tuple[tuple[tuple[int, int], ...], ...]
    initial_columns: tuple[tuple[int, ...], ...]
    submit: tuple[int, int]

    @property
    def target_rows(self):
        return tuple(range(len(self.target_cells[0])))

def freeze_frame(frame):
    return tuple(tuple(int(cell) for cell in row) for row in _matrix(frame))

def observe_macro_from_restart(enter_g6, controls):
    session, frame, boundary = enter_g6()
    frames = [freeze_frame(frame)]
    for control in controls:
        if control not in boundary.control_points:
            raise ValueError(f"missing_control:{control}")
        frame = session.click(*boundary.control_points[control])
        frames.append(freeze_frame(frame))
    return MacroTrace(tuple(frames), tuple(controls))

def _public_field(frame, name):
    return frame[name] if isinstance(frame, dict) else getattr(frame, name)

def public_terminal_signature(frame):
    return (
        int(_public_field(frame, "levels_completed")),
        str(_public_field(frame, "state")),
    )

def did_progress(before, after):
    return int(_public_field(after, "levels_completed")) > int(
        _public_field(before, "levels_completed")
    )

def residual_result(residual, effects, *, adapter_id, warrant_id):
    return {
        "status": "RESIDUAL",
        "classification": "EXACT_RESIDUAL",
        "adapter_id": adapter_id,
        "warrant_id": warrant_id,
        "effect_ids": [effect.effect_id for effect in effects],
        "residual": asdict(residual),
        "target_writes": 0,
    }

def execute_columns_and_submit(enter_g6, columns, adapter_id, warrant_id, effects):
    session, frame, boundary = enter_g6()
    writes = 0
    for column_index, column in enumerate(columns):
        if len(column) != len(boundary.target_rows):
            raise ValueError("target_column_arity")
        for row_index, bit in enumerate(column):
            if bit != boundary.initial_columns[column_index][row_index]:
                frame = session.click(*boundary.target_cells[column_index][row_index])
                writes += 1
    terminal = session.click(*boundary.submit)
    return {
        "status": "CANDIDATE",
        "classification": "DIAGNOSTIC",
        "adapter_id": adapter_id,
        "warrant_id": warrant_id,
        "effect_classes": [effect.effect_id for effect in effects],
        "columns": [list(column) for column in columns],
        "controls": list(PAIRS),
        "terminal": public_terminal_signature(terminal),
        "progressed": did_progress(frame, terminal),
        "target_writes": writes,
    }

def compile_g6_projection(enter_g6, adapter):
    traces = tuple(observe_macro_from_restart(enter_g6, controls) for controls in PAIRS)
    effects = tuple(macro_effect(trace.frames, trace.controls).effect for trace in traces)
    projection = compile_projection(effects, adapter)
    if isinstance(projection, UnknownResidual):
        return residual_result(
            projection, effects,
            adapter_id=adapter.adapter_id, warrant_id=adapter.warrant_id,
        )
    return execute_columns_and_submit(
        enter_g6, projection, adapter.adapter_id, adapter.warrant_id, effects
    )
```

Each macro trace begins at the same qualified G6 boundary and records initial,
intermediate and final public frames.  No result may use the target oracle until
all six effects project uniquely.

- [ ] **Step 4: Add evidence seals for stale IDs and full replay equality**

The workflow seal must assert:

```python
assert result["head"] == os.environ["GITHUB_SHA"]
assert result["adapter_id"] == training["adapter_id"]
assert result["warrant_id"] == training["warrant_id"]
assert result["model_calls"] == 0
assert result["source_inspection"] is False
if result["status"] == "RESIDUAL":
    assert result["target_writes"] == 0
    assert result["residual"]["missing_interface"] == "target.projection@1"
else:
    assert result["classification"] == "WARRANTED_POSITIVE"
    assert len(result["verification"]) == 2
    identity = ("adapter_id", "warrant_id", "effect_classes", "columns", "controls", "terminal")
    assert all(tuple(replay[k] for k in identity) == tuple(result["candidate"][k] for k in identity)
               for replay in result["verification"])
    assert all(replay["progressed"] for replay in result["verification"])
    assert result["ablation"]["without_adapter"] in {"RESIDUAL", "NO_PROGRESS"}
```

- [ ] **Step 5: Run exact public qualification**

Run via `.github/workflows/arc3-public-g6-consequence-projection.yml` on branch `arc3-consequence-compiler-v1`.

Expected outcome is one of:

- `PROMOTED` with two exact replays, ablation and matching identities; or
- `RESIDUAL` with zero writes and the exact unseen/ambiguous effect IDs.

- [ ] **Step 6: Consult ROS on a residual before designing another probe**

For each returned effect ID, search the five canonical ROS pages for its observed relation family and inspect exact linked branches/artifacts.  Add `ros_reconciliation` to the evidence with page IDs, matched claims, authority boundaries, rejected duplicates and the smallest remaining separator.  This step must not change the scientific classification of the run that produced the residual.

- [ ] **Step 7: Commit G6 qualification code and regenerated evidence**

```bash
git add experiments/arc3_public_g6_consequence_projection.py kaggle/tests/test_g6_consequence_projection_schema.py .github/workflows/arc3-public-g6-consequence-projection.yml
test ! -f evidence/arc3-public-g6-consequence-projection/result.json || git add evidence/arc3-public-g6-consequence-projection/result.json
git commit -m "Qualify ARC G6 consequence projection"
```

### Task 6: Freeze reusable capability and integrate the standalone agent

**Files:**
- Modify: `kaggle/src/metalogic_arc3/semantic_path.py`
- Modify: `kaggle/src/metalogic_arc3/memory_controller.py`
- Modify: `kaggle/scripts/build_agent.py`
- Modify: `kaggle/tests/test_semantic_path.py`
- Modify: `kaggle/tests/test_build_agent.py`
- Modify: `kaggle/provenance/sources.json`

**Interfaces:**
- Consumes: promoted frozen adapter and G6 plan, or retains `UNKNOWN` when Task 5 is residual.
- Produces: production-reachable `ConsequenceDiscovery.close(grid, residual)`, self-contained agent build and competition evaluation artifact.

- [ ] **Step 1: Write failing production-reachability and standalone tests**

```python
def test_controller_reaches_frozen_consequence_discovery():
    discovery = FrozenConsequenceDiscovery(
        fixture_adapter(), lambda grid, adapter: fixture_discovery_result(adapter)
    )
    controller = MemoryGraphController((6,), archived_capabilities=(), semantic_discovery=discovery)
    token = controller.observe_and_choose({
        "frame": [g6_control_fixture()],
        "levels_completed": 5,
        "state": "NOT_FINISHED",
        "available_actions": [6],
    })
    self.assertEqual(token.source, "semantic_path")
    self.assertTrue(discovery.called)

def test_generated_agent_contains_consequence_adapter_without_relative_imports():
    source = build_agent.render()
    self.assertIn("class EffectProjectionAdapter", source)
    self.assertIn("class FrozenConsequenceDiscovery", source)
    self.assertFalse(any(node.level for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)))
```

- [ ] **Step 2: Run tests and verify the new module is not vendored**

Run: `PYTHONPATH=kaggle/src python -m unittest kaggle.tests.test_semantic_path kaggle.tests.test_build_agent -v`

Expected: FAIL because `consequence_arc.py` is absent from the standalone build.

- [ ] **Step 3: Bind the frozen adapter to semantic discovery**

```python
class FrozenConsequenceDiscovery:
    def __init__(self, adapter, plan_factory):
        self.adapter = adapter
        self.plan_factory = plan_factory
        self.called = False

    def close(self, grid, residual):
        self.called = True
        result = self.plan_factory(grid, self.adapter)
        if isinstance(result, UnknownResidual):
            return result
        capability, plan = result
        return SemanticDiscoveryResult.bind(capability, plan)
```

Only register this discovery in the default controller if Task 5 is promoted.  A residual experiment must not silently add speculative runtime behavior.

- [ ] **Step 4: Vendor the module deterministically**

Add `CONSEQUENCE_ARC` to `build_agent.py`, clean its relative imports alongside `protected_future.py` and `semantic_path.py`, and insert it before consumers.  Update `sources.json` with exact capability/evidence lineage.

- [ ] **Step 5: Run full verification and deterministic build**

```bash
PYTHONPATH=kaggle/src:experiments python -m unittest discover -s kaggle/tests -v
a=$(mktemp)
b=$(mktemp)
python kaggle/scripts/build_agent.py --output "$a"
python kaggle/scripts/build_agent.py --output "$b"
cmp "$a" "$b"
sha256sum "$a"
```

Expected: all tests pass; `cmp` exits zero; one artifact digest is printed.

- [ ] **Step 6: Run competition boundary and preserve the artifact**

Run the existing official/local competition evaluation workflow against the generated agent.  Record exact solved/regressed games, score, runtime, action budget and artifact digest.  Submit to Kaggle only if authenticated access exists and the result is a non-regressing gain; otherwise retain the ready-to-upload artifact.

- [ ] **Step 7: Commit the frozen integration**

```bash
git add kaggle/src/metalogic_arc3/semantic_path.py kaggle/src/metalogic_arc3/memory_controller.py kaggle/scripts/build_agent.py kaggle/tests/test_semantic_path.py kaggle/tests/test_build_agent.py kaggle/provenance/sources.json
git commit -m "Integrate warranted ARC consequence capability"
```

### Task 7: Evidence audit and ROS synchronization

**Files:**
- Create: `.superpowers/sdd/2026-09-24-arc3-consequence-compiler/progress.md`
- Modify through Notion: Canonical Research State, Research Checkpoints, Campaign Registry, Cold-Start Runbooks, and Papers & Formal Ideas when a programme-level law is earned.

**Interfaces:**
- Consumes: exact branch head, hosted run/job/artifact/digest, evidence JSON, test count, agent digest, replay and ablation results.
- Produces: one reconciled scientific boundary and an exact restart command.

- [ ] **Step 1: Audit every material claim against evidence**

Create a table with `claim`, `status`, `source head`, `run`, `artifact`, `digest`, `boundary`, `negative lineage`, and `remaining unknown`.  Any missing hosted field is written as `UNKNOWN`, never inferred from local success.

- [ ] **Step 2: Reconcile stale and superseded evidence**

Explicitly mark `evidence/arc3-public-g6-future-quotient/result.json` stale if its embedded claim/head does not match the demoted experiment source.  Preserve it as historical evidence; do not overwrite it with a different experiment.

- [ ] **Step 3: Update ROS with the exact outcome**

Record date, hypothesis, branch/head, run/job/artifact/digest, result, interpretation, falsified family, remaining `UNKNOWN`, next smallest residual and exact restart command.  Update Papers only if the effect-to-output law transports beyond its training level or earns a programme-level principle.

- [ ] **Step 4: Final branch verification**

Run:

```bash
git diff --check
git status --short
PYTHONPATH=kaggle/src:experiments python -m unittest discover -s kaggle/tests -v
git log --oneline --decorate -12
```

Expected: no whitespace errors; only intentional evidence/ledger changes before the final commit; all tests pass.

- [ ] **Step 5: Commit the audit and report the exact boundary**

```bash
git add .superpowers/sdd/2026-09-24-arc3-consequence-compiler/progress.md
git commit -m "Record ARC consequence compiler qualification"
```

Report one of `G6 SOLVED`, `EXACT RESIDUAL`, or `EXTERNAL BLOCKER`, followed by the exact evidence identity and the next smallest experiment.
