from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess

from metalogic_arc3.consequence_arc import (
    EffectClass,
    EffectProjectionAdapter,
    compile_projection,
)
from metalogic_arc3.future_arc import macro_effect
from metalogic_arc3.protected_future import UnknownResidual, canonical_digest
from metalogic_arc3.semantic_path import (
    _bar_rows,
    _matrix,
    _selector_controls,
    _submit,
)


SCHEMA = "arc3.g6-consequence-projection@1"
ROUTE = "RRRRUULLUUUL"
PAIRS = ("RR", "RR", "UU", "LL", "UU", "UL")
IDENTITY_FIELDS = (
    "adapter_id",
    "warrant_id",
    "effect_classes",
    "columns",
    "controls",
    "terminal",
)


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


class PublicSession:
    def __init__(self, env, click):
        self.env = env
        self._click = click

    def click(self, x, y):
        return self._click(self.env, (y, x))


def pair_route(route):
    if len(route) % 2 or len(route) // 2 != 6:
        raise ValueError("route_pair_arity")
    return tuple(route[index:index + 2] for index in range(0, len(route), 2))


def freeze_frame(frame):
    return tuple(tuple(int(cell) for cell in row) for row in _matrix(frame))


def _public_field(frame, name):
    return frame[name] if isinstance(frame, dict) else getattr(frame, name)


def public_terminal_signature(frame):
    return [
        int(_public_field(frame, "levels_completed")),
        str(_public_field(frame, "state")),
    ]


def did_progress(before, after):
    return int(_public_field(after, "levels_completed")) > int(
        _public_field(before, "levels_completed")
    )


def enter_public_g6():
    import arc3_public_all_blue_to_gray_g2 as ab
    from arc3_public_g6_paired_route import enter_g6

    env, frame = enter_g6()
    visible = _matrix(frame)
    control_points = {
        label: point
        for point, label in _selector_controls(visible)
    }
    target_rows = _bar_rows(visible, "right")
    target_cells = tuple(
        tuple(target_rows[row][column] for row in range(len(target_rows)))
        for column in range(len(target_rows[0]))
    )
    initial_columns = tuple(
        tuple(1 if visible[y][x] == 5 else 0 for x, y in column)
        for column in target_cells
    )
    boundary = G6Boundary(
        control_points=control_points,
        target_cells=target_cells,
        initial_columns=initial_columns,
        submit=_submit(visible),
    )
    return PublicSession(env, ab.click), frame, boundary


def observe_macro_from_restart(enter_g6, controls):
    session, frame, boundary = enter_g6()
    frames = [freeze_frame(frame)]
    for control in controls:
        if control not in boundary.control_points:
            raise ValueError(f"missing_control:{control}")
        frame = session.click(*boundary.control_points[control])
        frames.append(freeze_frame(frame))
    return MacroTrace(tuple(frames), tuple(controls))


def _class_id(adapter, effect):
    signature = effect.project(adapter.families)
    for block in adapter.classes:
        if signature == block.signature:
            return block.class_id
    raise ValueError(f"unclassified_effect:{effect.effect_id}")


def residual_result(residual, effects, adapter):
    unknown_slots = tuple(
        index
        for index, effect in enumerate(effects)
        if isinstance(adapter.project(effect), UnknownResidual)
    )
    return {
        "status": "RESIDUAL",
        "classification": "EXACT_RESIDUAL",
        "adapter_id": adapter.adapter_id,
        "warrant_id": adapter.warrant_id,
        "effect_ids": [effect.effect_id for effect in effects],
        "unknown_slots": list(unknown_slots),
        "residual": asdict(residual),
        "target_writes": 0,
    }


def execute_columns_and_submit(
    enter_g6,
    columns,
    *,
    adapter_id,
    warrant_id,
    effect_classes,
    effect_ids,
):
    session, start_frame, boundary = enter_g6()
    frame = start_frame
    writes = 0
    if len(columns) != len(boundary.target_cells):
        raise ValueError("target_column_count")
    for column_index, column in enumerate(columns):
        if len(column) != len(boundary.target_rows):
            raise ValueError("target_column_arity")
        for row_index, bit in enumerate(column):
            if bit != boundary.initial_columns[column_index][row_index]:
                frame = session.click(
                    *boundary.target_cells[column_index][row_index]
                )
                writes += 1
    terminal = session.click(*boundary.submit)
    return {
        "adapter_id": adapter_id,
        "warrant_id": warrant_id,
        "effect_classes": list(effect_classes),
        "effect_ids": list(effect_ids),
        "columns": [list(column) for column in columns],
        "controls": list(PAIRS),
        "terminal": public_terminal_signature(terminal),
        "progressed": did_progress(start_frame, terminal),
        "target_writes": writes,
    }


def compile_g6_projection(enter_g6, adapter):
    traces = tuple(
        observe_macro_from_restart(enter_g6, controls)
        for controls in PAIRS
    )
    effects = tuple(
        macro_effect(trace.frames, trace.controls).effect
        for trace in traces
    )
    projection = compile_projection(effects, adapter)
    if isinstance(projection, UnknownResidual):
        return residual_result(projection, effects, adapter)
    effect_classes = tuple(_class_id(adapter, effect) for effect in effects)
    return execute_columns_and_submit(
        enter_g6,
        projection,
        adapter_id=adapter.adapter_id,
        warrant_id=adapter.warrant_id,
        effect_classes=effect_classes,
        effect_ids=tuple(effect.effect_id for effect in effects),
    )


def _tupleize(value):
    if isinstance(value, list):
        return tuple(_tupleize(item) for item in value)
    if isinstance(value, dict):
        return {key: _tupleize(item) for key, item in value.items()}
    return value


def load_adapter(training):
    payload = training["adapter"]
    classes = tuple(
        EffectClass(
            class_id=block["class_id"],
            signature=_tupleize(block["signature"]),
            effect_ids=tuple(block["effect_ids"]),
            output=tuple(block["output"]),
            evidence_ids=tuple(block["evidence_ids"]),
            source_levels=tuple(block["source_levels"]),
        )
        for block in payload["classes"]
    )
    adapter = EffectProjectionAdapter(
        interface_id=payload["interface_id"],
        families=tuple(payload["families"]),
        classes=classes,
        preserves=tuple(payload["preserves"]),
        evidence_ids=tuple(payload["evidence_ids"]),
        adapter_id=payload["adapter_id"],
        warrant_id=payload["warrant_id"],
    )
    semantic_classes = tuple(
        (block.class_id, block.signature, block.output)
        for block in classes
    )
    expected_adapter = canonical_digest(
        (
            "effect-projection-adapter@1",
            adapter.families,
            semantic_classes,
            adapter.preserves,
        )
    )
    expected_warrant = canonical_digest(
        (
            "effect-projection-warrant@1",
            expected_adapter,
            adapter.evidence_ids,
            tuple(
                (
                    block.class_id,
                    block.evidence_ids,
                    block.source_levels,
                )
                for block in classes
            ),
        )
    )
    if adapter.adapter_id != expected_adapter:
        raise ValueError("stale_adapter_id")
    if adapter.warrant_id != expected_warrant:
        raise ValueError("stale_warrant_id")
    if training["adapter_id"] != adapter.adapter_id:
        raise ValueError("training_adapter_id_mismatch")
    if training["warrant_id"] != adapter.warrant_id:
        raise ValueError("training_warrant_id_mismatch")
    return adapter


def _identity(row):
    return tuple(canonical_digest(row[key]) for key in IDENTITY_FIELDS)


def validate_g6_result(result, *, executing_head):
    if result.get("schema") != SCHEMA:
        raise ValueError("g6_projection_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    if result.get("model_calls") != 0:
        raise ValueError("model_calls_forbidden")
    if result.get("source_inspection") is not False:
        raise ValueError("source_inspection_forbidden")
    status = result.get("status")
    if status == "RESIDUAL":
        if result.get("target_writes") != 0:
            raise ValueError("residual_target_write")
        if result.get("classification") != "EXACT_RESIDUAL":
            raise ValueError("residual_classification")
        if result.get("residual", {}).get("missing_interface") != "target.projection@1":
            raise ValueError("residual_interface")
        return result
    candidate = result.get("candidate", {})
    if status == "REJECTED":
        if result.get("classification") != "WARRANTED_NEGATIVE":
            raise ValueError("negative_classification")
        if candidate.get("progressed") is not False:
            raise ValueError("negative_progress")
        return result
    if status != "PROMOTED":
        raise ValueError("g6_projection_status")
    if result.get("classification") != "WARRANTED_POSITIVE":
        raise ValueError("positive_classification")
    verification = result.get("verification", [])
    if len(verification) != 2:
        raise ValueError("verification_replay_count")
    expected = _identity(candidate)
    if any(_identity(replay) != expected for replay in verification):
        raise ValueError("replay_identity_mismatch")
    if not candidate.get("progressed") or not all(
        replay.get("progressed") for replay in verification
    ):
        raise ValueError("verification_no_progress")
    if result.get("ablation", {}).get("without_adapter") not in {
        "RESIDUAL",
        "NO_PROGRESS",
    }:
        raise ValueError("adapter_ablation")
    return result


def _source_head():
    configured = os.environ.get("GITHUB_SHA")
    if configured:
        return configured
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        text=True,
    ).strip()


def main():
    head = _source_head()
    training_path = Path(
        os.environ.get(
            "TRAINING_RESULT",
            "evidence/arc3-public-consequence-training/result.json",
        )
    )
    training = json.loads(training_path.read_text())
    if training["head"] != head:
        raise ValueError("stale_training_head")
    adapter = load_adapter(training)
    candidate = compile_g6_projection(enter_public_g6, adapter)
    base = {
        "schema": SCHEMA,
        "head": head,
        "adapter_id": adapter.adapter_id,
        "warrant_id": adapter.warrant_id,
        "model_calls": 0,
        "source_inspection": False,
        "route": ROUTE,
        "controls": list(pair_route(ROUTE)),
    }
    if candidate.get("status") == "RESIDUAL":
        result = {**base, **candidate}
    elif not candidate["progressed"]:
        result = {
            **base,
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "candidate": candidate,
            "verification": [],
            "ablation": {"without_adapter": "RESIDUAL"},
            "target_writes": candidate["target_writes"],
        }
    else:
        verification = [
            execute_columns_and_submit(
                enter_public_g6,
                candidate["columns"],
                adapter_id=candidate["adapter_id"],
                warrant_id=candidate["warrant_id"],
                effect_classes=candidate["effect_classes"],
                effect_ids=candidate["effect_ids"],
            )
            for _ in range(2)
        ]
        result = {
            **base,
            "status": "PROMOTED",
            "classification": "WARRANTED_POSITIVE",
            "candidate": candidate,
            "verification": verification,
            "ablation": {"without_adapter": "RESIDUAL"},
            "target_writes": candidate["target_writes"],
        }
    validate_g6_result(result, executing_head=head)
    out = Path(
        os.environ.get(
            "OUTDIR",
            "evidence/arc3-public-g6-consequence-projection",
        )
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(f"ARC3_PUBLIC_G6_CONSEQUENCE_PROJECTION={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
