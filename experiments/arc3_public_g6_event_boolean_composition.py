from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
import os
from pathlib import Path
import subprocess

from metalogic_arc3.protected_future import canonical_digest
from metalogic_arc3.semantic_path import (
    _bar_rows,
    _find_board,
    _matrix,
    _selector_controls,
    _source_bits,
    _submit,
)


SCHEMA = "arc3.g6-event-boolean-composition@1"
ROUTE = "RRRRUULLUUUL"
EVENT_SIGNATURES = ("000", "100", "101", "110", "111")
ACTION_BUDGET = 50
RUN_FIELDS = frozenset(
    {
        "signature",
        "segments",
        "event_positions",
        "event_trace",
        "codes",
        "columns",
        "start_level",
        "terminal",
        "progressed",
        "target_writes",
        "writes",
        "action_count",
        "semantic_id",
    }
)


def _bits(value: Sequence[int]) -> tuple[int, ...]:
    result = tuple(int(bit) for bit in value)
    if len(result) != 6 or any(bit not in (0, 1) for bit in result):
        raise ValueError("control_code_arity")
    return result


def event_segments(
    route: str,
    events: Iterable[tuple[int, tuple[int, int]]],
) -> tuple[tuple[str, tuple[int, int]], ...]:
    observed = tuple((int(step), tuple(position)) for step, position in events)
    steps = tuple(step for step, _ in observed)
    positions = tuple(position for _, position in observed)
    if (
        len(observed) != 6
        or any(len(position) != 2 for position in positions)
        or steps != tuple(sorted(set(steps)))
        or len(set(positions)) != len(positions)
        or not steps
        or steps[-1] != len(route)
        or steps[0] < 1
    ):
        raise ValueError("marker_event_partition")
    starts = (0,) + steps[:-1]
    segments = tuple(
        (route[start:stop], position)
        for start, (stop, position) in zip(starts, observed)
    )
    if any(len(segment) != 2 for segment, _ in segments):
        raise ValueError("marker_event_segment_arity")
    return segments


def collect_stable_codes(
    observations: Iterable[tuple[str, Sequence[int]]],
) -> dict[str, tuple[int, ...]]:
    codes: dict[str, tuple[int, ...]] = {}
    for control, value in observations:
        code = _bits(value)
        previous = codes.get(control)
        if previous is not None and previous != code:
            raise ValueError("inconsistent_control_code")
        codes[control] = code
    return codes


def compose_bits(
    signature: str,
    left: Sequence[int],
    right: Sequence[int],
) -> tuple[int, ...]:
    if signature not in EVENT_SIGNATURES:
        raise ValueError("unknown_boolean_signature")
    left_bits = _bits(left)
    right_bits = _bits(right)
    truth = {
        (0, 0): int(signature[0]),
        (1, 0): int(signature[1]),
        (0, 1): int(signature[1]),
        (1, 1): int(signature[2]),
    }
    return tuple(truth[pair] for pair in zip(left_bits, right_bits))


def spatial_columns(
    segments: Iterable[tuple[str, tuple[int, int]]],
    codes: Mapping[str, Sequence[int]],
    signature: str,
) -> tuple[tuple[int, ...], ...]:
    ordered = tuple(sorted(segments, key=lambda item: item[1]))
    if len(ordered) != 6 or len({position for _, position in ordered}) != 6:
        raise ValueError("marker_spatial_alignment")
    columns = []
    for controls, _ in ordered:
        if len(controls) != 2 or any(control not in codes for control in controls):
            raise ValueError("missing_segment_control_code")
        columns.append(
            compose_bits(signature, codes[controls[0]], codes[controls[1]])
        )
    return tuple(columns)


def _public_field(frame, name):
    return frame[name] if isinstance(frame, dict) else getattr(frame, name)


def _terminal(frame) -> list[object]:
    return [
        int(_public_field(frame, "levels_completed")),
        str(_public_field(frame, "state")),
    ]


def _progressed(before, after) -> bool:
    return int(_public_field(after, "levels_completed")) > int(
        _public_field(before, "levels_completed")
    ) or str(_public_field(after, "state")).endswith("WIN")


def _semantic_id(row: Mapping[str, object]) -> str:
    return canonical_digest(
        (
            "g6-event-boolean-candidate@1",
            row["signature"],
            row["segments"],
            row["event_positions"],
            row["codes"],
            row["columns"],
        )
    )


def run_candidate(signature: str, enter_g6=None) -> dict[str, object]:
    import arc3_public_all_blue_to_gray_g2 as ab

    if enter_g6 is None:
        from arc3_public_g6_paired_route import enter_g6 as public_enter_g6

        enter_g6 = public_enter_g6
    env, frame = enter_g6()
    start_frame = frame
    visible = _matrix(frame)
    board_top, _ = _find_board(visible)
    controls = {
        label: (y, x)
        for (x, y), label in _selector_controls(visible)
    }
    targets = _bar_rows(visible, "right")
    events = []
    code_observations = []
    actions = 0
    for step, control in enumerate(ROUTE, start=1):
        if control not in controls:
            raise ValueError(f"missing_control:{control}")
        before = _matrix(frame)
        frame = ab.click(env, controls[control])
        actions += 1
        after = _matrix(frame)
        code_observations.append((control, _source_bits(after)))
        marker_changes = tuple(
            (row, col)
            for row in range(board_top)
            for col in range(len(after[0]))
            if before[row][col] != after[row][col]
        )
        if len(marker_changes) > 1:
            raise ValueError("non_singleton_marker_response")
        if marker_changes:
            events.append((step, marker_changes[0]))

    segments = event_segments(ROUTE, events)
    codes = collect_stable_codes(code_observations)
    columns = spatial_columns(segments, codes, signature)
    writes = []
    for row_index, target_row in enumerate(targets):
        for column_index, (x, y) in enumerate(target_row):
            desired = columns[column_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions += 1
                writes.append(
                    {
                        "row": row_index,
                        "column": column_index,
                        "value": desired,
                    }
                )
    submit = _submit(_matrix(frame))
    terminal = ab.click(env, (submit[1], submit[0]))
    actions += 1
    if actions > ACTION_BUDGET:
        raise ValueError("action_budget")
    row = {
        "signature": signature,
        "segments": [segment for segment, _ in sorted(segments, key=lambda item: item[1])],
        "event_positions": [list(position) for _, position in sorted(segments, key=lambda item: item[1])],
        "event_trace": [
            {"step": step, "position": list(position)}
            for step, position in events
        ],
        "codes": {control: list(code) for control, code in sorted(codes.items())},
        "columns": [list(column) for column in columns],
        "start_level": int(_public_field(start_frame, "levels_completed")),
        "terminal": _terminal(terminal),
        "progressed": _progressed(start_frame, terminal),
        "target_writes": len(writes),
        "writes": writes,
        "action_count": actions,
    }
    row["semantic_id"] = _semantic_id(row)
    return row


def _validate_run(row: Mapping[str, object]):
    if not RUN_FIELDS.issubset(row):
        raise ValueError("run_evidence_missing")
    signature = row["signature"]
    if signature not in EVENT_SIGNATURES:
        raise ValueError("run_evidence_signature")
    try:
        trace = tuple(
            (int(event["step"]), tuple(event["position"]))
            for event in row["event_trace"]
        )
        chronological = event_segments(ROUTE, trace)
        spatial = tuple(sorted(chronological, key=lambda item: item[1]))
        segments = tuple(str(segment) for segment in row["segments"])
        positions = tuple(tuple(position) for position in row["event_positions"])
        if segments != tuple(segment for segment, _ in spatial):
            raise ValueError("run_evidence_segments")
        if positions != tuple(position for _, position in spatial):
            raise ValueError("run_evidence_positions")
        codes = {
            str(control): _bits(code)
            for control, code in row["codes"].items()
        }
        expected_columns = spatial_columns(spatial, codes, str(signature))
        columns = tuple(tuple(int(bit) for bit in column) for column in row["columns"])
        if columns != expected_columns:
            raise ValueError("run_evidence_columns")
        writes = tuple(row["writes"])
        if int(row["target_writes"]) != len(writes):
            raise ValueError("run_evidence_writes")
        terminal = tuple(row["terminal"])
        if len(terminal) != 2 or not isinstance(row["progressed"], bool):
            raise ValueError("run_evidence_terminal")
        expected_progress = int(terminal[0]) > int(row["start_level"]) or str(
            terminal[1]
        ).endswith("WIN")
        if row["progressed"] is not expected_progress:
            raise ValueError("run_evidence_progress")
        if not isinstance(row["action_count"], int):
            raise ValueError("run_evidence_actions")
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error).startswith("run_evidence"):
            raise
        raise ValueError("run_evidence_malformed") from error
    if row["semantic_id"] != _semantic_id(row):
        raise ValueError("run_semantic_id")
    return row


def validate_result(result: Mapping[str, object], *, executing_head: str):
    if result.get("schema") != SCHEMA:
        raise ValueError("event_boolean_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    if result.get("model_calls") != 0 or result.get("source_inspection") is not False:
        raise ValueError("scientific_boundary")
    if result.get("action_budget_per_run") != ACTION_BUDGET:
        raise ValueError("action_budget_declaration")
    variants = tuple(result.get("variants", ()))
    verification = tuple(result.get("verification", ()))
    for row in variants + verification:
        _validate_run(row)
    runs = list(variants) + list(verification)
    if any(int(row.get("action_count", ACTION_BUDGET + 1)) > ACTION_BUDGET for row in runs):
        raise ValueError("action_budget")
    status = result.get("status")
    if status == "RESIDUAL":
        if result.get("classification") != "NON_EVIDENCE":
            raise ValueError("residual_classification")
        if not result.get("residual", {}).get("reason"):
            raise ValueError("residual_reason")
        return result
    if (
        tuple(result.get("signatures", ())) != EVENT_SIGNATURES
        or tuple(row.get("signature") for row in variants) != EVENT_SIGNATURES
        or len(variants) != len(EVENT_SIGNATURES)
    ):
        raise ValueError("boolean_family_census")
    if status == "REJECTED":
        if result.get("classification") != "WARRANTED_NEGATIVE":
            raise ValueError("negative_classification")
        if any(row.get("progressed") for row in variants):
            raise ValueError("negative_contains_progress")
        if result.get("verification") != []:
            raise ValueError("negative_verification")
        return result
    if status != "PROMOTED" or result.get("classification") != "WARRANTED_POSITIVE":
        raise ValueError("qualification_status")
    candidate = result.get("candidate", {})
    if len(verification) != 2:
        raise ValueError("replay_count")
    progressing = tuple(row for row in variants if row["progressed"])
    if len(progressing) != 1 or progressing[0]["semantic_id"] != candidate.get("semantic_id"):
        raise ValueError("promoted_census")
    _validate_run(candidate)
    identity = candidate.get("semantic_id")
    if not identity or any(row.get("semantic_id") != identity for row in verification):
        raise ValueError("replay_identity")
    if not candidate.get("progressed") or not all(row.get("progressed") for row in verification):
        raise ValueError("replay_progress")
    return result


def _source_head() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    ).strip()


def build_result(*, enter_g6=None, head: str | None = None, runner=None) -> dict[str, object]:
    runner = run_candidate if runner is None else runner
    variants = []
    base = {
        "schema": SCHEMA,
        "head": head or _source_head(),
        "route": ROUTE,
        "signatures": list(EVENT_SIGNATURES),
        "model_calls": 0,
        "source_inspection": False,
        "action_budget_per_run": ACTION_BUDGET,
        "claim_boundary": (
            "exact public tn36 G6; six legally observed singleton marker events; "
            "two-control event intervals; marker-spatial target alignment; symmetric "
            "rowwise truth signatures 000/100/101/110/111; terminal progress oracle"
        ),
    }
    def residual(reason, *, error=None, candidate=None, verification=()):
        payload = {
            **base,
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "variants": variants,
            "verification": list(verification),
            "residual": {
                "reason": reason,
                "error": error,
            },
            "target_writes": sum(int(row["target_writes"]) for row in variants)
            + sum(int(row["target_writes"]) for row in verification),
        }
        if candidate is not None:
            payload["candidate"] = candidate
        validate_result(payload, executing_head=str(payload["head"]))
        return payload

    for signature in EVENT_SIGNATURES:
        try:
            variants.append(runner(signature, enter_g6))
        except Exception as error:
            return residual(
                "candidate_run_exception",
                error=f"{type(error).__name__}:{error}",
            )
    progressed = [row for row in variants if row["progressed"]]
    if not progressed:
        result = {
            **base,
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "variants": variants,
            "verification": [],
            "target_writes": sum(int(row["target_writes"]) for row in variants),
        }
    elif len(progressed) != 1:
        return residual("ambiguous_progressing_signature")
    else:
        selected = progressed[0]
        verification = []
        for _ in range(2):
            try:
                verification.append(runner(str(selected["signature"]), enter_g6))
            except Exception as error:
                return residual(
                    "candidate_run_exception",
                    error=f"{type(error).__name__}:{error}",
                    candidate=selected,
                    verification=verification,
                )
        if any(not row["progressed"] for row in verification):
            return residual(
                "replay_no_progress",
                candidate=selected,
                verification=verification,
            )
        if any(row["semantic_id"] != selected["semantic_id"] for row in verification):
            return residual(
                "replay_identity_mismatch",
                candidate=selected,
                verification=verification,
            )
        result = {
            **base,
            "status": "PROMOTED",
            "classification": "WARRANTED_POSITIVE",
            "variants": variants,
            "candidate": selected,
            "verification": verification,
            "target_writes": int(selected["target_writes"])
            + sum(int(row["target_writes"]) for row in verification),
        }
    validate_result(result, executing_head=str(result["head"]))
    return result


def main():
    result = build_result()
    out = Path(
        os.environ.get(
            "OUTDIR",
            "evidence/arc3-public-g6-event-boolean-composition",
        )
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(f"ARC3_PUBLIC_G6_EVENT_BOOLEAN_COMPOSITION={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
