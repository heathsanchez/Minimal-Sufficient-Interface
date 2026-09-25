from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from metalogic_arc3.consequence_arc import (
    EffectProjectionAdapter,
    SemanticAction,
    TerminalWarrant,
    WarrantedEffectExample,
)
from metalogic_arc3.future_arc import relational_effect, relational_observation
from metalogic_arc3.protected_future import UnknownResidual, canonical_digest
from metalogic_arc3.semantic_path import SemanticPathSession, _matrix


SCHEMA = "arc3.consequence-training@1"


def freeze_frame(frame):
    return tuple(tuple(int(cell) for cell in row) for row in _matrix(frame))


def record_warranted_level(
    *,
    level,
    path,
    probe_traces,
    codes,
    warrant_ref,
):
    if len(path) != 6:
        raise ValueError("successful_slot_arity")
    for operator in path:
        if operator not in probe_traces:
            raise ValueError(f"missing_probe_trace:{operator}")
        if operator not in codes:
            raise ValueError(f"missing_probe_code:{operator}")

    warrant = TerminalWarrant("PROGRESS", warrant_ref)
    examples = []
    for index, operator in enumerate(path):
        frames = tuple(probe_traces[operator])
        if len(frames) < 2:
            raise ValueError(f"probe_trace_arity:{operator}")
        examples.append(
            WarrantedEffectExample.build(
                before=relational_observation(frames[0]),
                intervention=SemanticAction("program-slot", (operator,)),
                intermediates=tuple(
                    relational_observation(frame)
                    for frame in frames[1:-1]
                ),
                after=relational_observation(frames[-1]),
                effect=relational_effect(frames),
                output=tuple(codes[operator]),
                slot_index=index,
                terminal_warrant=warrant,
                lineage=(f"tn36:G{level}", warrant_ref),
            )
        )
    return tuple(examples)


def serialize_example(example):
    return {
        "example_id": example.example_id,
        "slot_index": example.slot_index,
        "action": {
            "family": example.intervention.family,
            "controls": list(example.intervention.controls),
        },
        "before_id": example.before.observation_id,
        "intermediate_ids": [
            observation.observation_id
            for observation in example.intermediates
        ],
        "after_id": example.after.observation_id,
        "effect_id": example.effect.effect_id,
        "features": [list(feature) for feature in example.effect.features],
        "output": list(example.output),
        "lineage": list(example.lineage),
    }


def serialize_adapter(adapter):
    return {
        "interface_id": adapter.interface_id,
        "families": list(adapter.families),
        "classes": [
            {
                "class_id": block.class_id,
                "signature": [list(feature) for feature in block.signature],
                "effect_ids": list(block.effect_ids),
                "output": list(block.output),
                "evidence_ids": list(block.evidence_ids),
                "source_levels": list(block.source_levels),
            }
            for block in adapter.classes
        ],
        "preserves": list(adapter.preserves),
        "evidence_ids": list(adapter.evidence_ids),
        "adapter_id": adapter.adapter_id,
        "warrant_id": adapter.warrant_id,
    }


def validate_training_result(result, *, executing_head):
    if result.get("schema") != SCHEMA:
        raise ValueError("training_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    levels = result.get("levels", [])
    if [level.get("level") for level in levels] != [3, 4, 5]:
        raise ValueError("training_level_boundary")
    for level in levels:
        warrant = level.get("terminal_warrant", {})
        if warrant.get("consequence") not in {"PROGRESS", "WIN"}:
            raise ValueError("terminal_warrant_required")
        examples = level.get("examples", [])
        if len(examples) != 6:
            raise ValueError("successful_slot_arity")
        if [item.get("slot_index") for item in examples] != list(range(6)):
            raise ValueError("slot_order")
    if result.get("model_calls") != 0:
        raise ValueError("model_calls_forbidden")
    if result.get("source_inspection") is not False:
        raise ValueError("source_inspection_forbidden")
    for key in ("corpus_id", "adapter_id", "warrant_id"):
        if not result.get(key):
            raise ValueError(f"missing_{key}")
    return result


def execute_session_with_probe_traces(env, frame, click, *, max_actions=40):
    session = SemanticPathSession.start(frame)
    actions = []
    probe_traces = {}
    while session.phase != "done" and len(actions) < max_actions:
        before = freeze_frame(frame)
        x, y = session.next_action(frame)
        kind = session.last_action_kind
        label = session.pending_probe if kind == "probe" else None
        frame = click(env, (y, x))
        after = freeze_frame(frame)
        if label is not None:
            probe_traces[label] = (before, after)
        actions.append(
            {
                "xy": [x, y],
                "kind": kind,
                "label": label,
                "level": int(frame.levels_completed),
                "state": str(frame.state),
            }
        )
    if session.phase != "done":
        raise AssertionError("semantic_session_action_budget")
    return frame, session, tuple(actions), probe_traces


def replay_training_once(*, warrant_ref):
    from arcengine import GameState
    import arc3_public_all_blue_to_gray_g2 as ab
    import arc3_public_panel_correspondence_g3 as g3

    env, _ = g3.enter_level3()
    frame = env.observation_space
    levels = []
    all_examples = []
    for level in (3, 4, 5):
        start_level = int(frame.levels_completed)
        frame, session, actions, traces = execute_session_with_probe_traces(
            env,
            frame,
            ab.click,
        )
        progressed = (
            int(frame.levels_completed) > start_level
            or frame.state == GameState.WIN
        )
        if not progressed:
            raise AssertionError(f"level_did_not_progress:G{level}")
        examples = record_warranted_level(
            level=level,
            path=session.plan.path,
            probe_traces=traces,
            codes=session.codes,
            warrant_ref=warrant_ref,
        )
        all_examples.extend(examples)
        levels.append(
            {
                "level": level,
                "path": session.plan.path,
                "action_count": len(actions),
                "terminal_warrant": {
                    "consequence": "PROGRESS",
                    "evidence_ref": warrant_ref,
                },
                "examples": [serialize_example(item) for item in examples],
            }
        )

    adapter = EffectProjectionAdapter.build(all_examples)
    if isinstance(adapter, UnknownResidual):
        raise AssertionError(
            f"adapter_residual:{adapter.reason}:{','.join(adapter.evidence)}"
        )
    corpus_id = canonical_digest(
        (
            "arc3.consequence-corpus@1",
            tuple(item.example_id for item in all_examples),
        )
    )
    return {
        "levels": levels,
        "corpus_id": corpus_id,
        "adapter": serialize_adapter(adapter),
        "adapter_id": adapter.adapter_id,
        "warrant_id": adapter.warrant_id,
    }


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
    warrant_ref = f"github:{os.environ.get('GITHUB_RUN_ID', 'local')}:{head}"
    first = replay_training_once(warrant_ref=warrant_ref)
    second = replay_training_once(warrant_ref=warrant_ref)
    stable = (
        first["corpus_id"],
        first["adapter_id"],
        first["warrant_id"],
    ) == (
        second["corpus_id"],
        second["adapter_id"],
        second["warrant_id"],
    )
    if not stable:
        raise AssertionError("independent_corpus_identity_mismatch")
    result = {
        "schema": SCHEMA,
        "head": head,
        "status": "WARRANTED_POSITIVE",
        "classification": "WARRANTED POSITIVE",
        "levels": first["levels"],
        "corpus_id": first["corpus_id"],
        "adapter": first["adapter"],
        "adapter_id": first["adapter_id"],
        "warrant_id": first["warrant_id"],
        "independent_replay_count": 2,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "public tn36 G3-G5 successful semantic sessions; local visible "
            "probe effects and terminally warranted target columns"
        ),
    }
    validate_training_result(result, executing_head=head)
    out = Path(
        os.environ.get(
            "OUTDIR",
            "evidence/arc3-public-consequence-training",
        )
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print("ARC3_PUBLIC_CONSEQUENCE_TRAINING=PASS")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
