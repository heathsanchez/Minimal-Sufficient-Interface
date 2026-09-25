from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from arc3_public_g6_glyph_role_decoder import (
    ROLE_ORDER,
    _bits,
    _execute_projection,
    _read_events,
    _read_training,
    event_role_records,
)
from metalogic_arc3.protected_future import UnknownResidual, canonical_digest


INTERFACE_ID = "program.hierarchical-event-lift@1"
SCHEMA = "arc3.g6-hierarchical-program-lift@1"
G5_PROGRAM = tuple("XDDDTS")
ACTION_BUDGET = 60


def _residual(reason, evidence=()):
    return UnknownResidual(INTERFACE_ID, reason, tuple(str(item) for item in evidence))


def _extract_g5_program(training):
    try:
        levels = tuple(training.get("levels", ()))
        if [int(row.get("level", -1)) for row in levels] != [3, 4, 5]:
            return _residual("warranted_level_census")
        level = levels[-1]
        if level.get("terminal_warrant", {}).get("consequence") not in {"PROGRESS", "WIN"}:
            return _residual("missing_terminal_warrant", ("G5",))
        program = []
        for index, example in enumerate(level.get("examples", ())):
            controls = tuple(example.get("action", {}).get("controls", ()))
            if len(controls) != 1 or not isinstance(controls[0], str):
                return _residual("g5_program_census", (f"slot{index}:{controls!r}",))
            program.append({"slot": index, "control": controls[0], "output": _bits(example.get("output"))})
    except (AttributeError, TypeError, ValueError) as error:
        return _residual("g5_program_census", (str(error),))
    if tuple(row["control"] for row in program) != G5_PROGRAM:
        return _residual("g5_program_census", (repr(tuple(row["control"] for row in program)),))
    return tuple(program)


def _compile_hierarchical_columns(program, roles):
    if isinstance(program, UnknownResidual):
        return program
    roles = tuple(roles)
    if (
        tuple(row.get("role") for row in roles) != ROLE_ORDER
        or set(row.get("marker_rank") for row in roles) != set(range(6))
        or len(program) != 6
    ):
        return _residual("g6_lifecycle_census")
    aligned = [
        {"role": role["role"], "marker_rank": int(role["marker_rank"]), **instruction}
        for role, instruction in zip(roles, program)
    ]
    return tuple(row["output"] for row in sorted(aligned, key=lambda row: row["marker_rank"]))


def _unknown_candidate(residual, action_count=0):
    return {
        "status": "UNKNOWN",
        "residual": {
            "missing_interface": residual.interface_id,
            "reason": residual.reason,
            "evidence": list(residual.evidence),
        },
        "target_writes": 0,
        "submit_clicks": 0,
        "action_count": int(action_count),
    }


def run_candidate(*, training_reader=None, event_reader=None, executor=None):
    training = (training_reader or _read_training)()
    event_observation = (event_reader or _read_events)()
    observation_actions = int(event_observation.get("action_count", -1))
    if observation_actions != 12:
        return _unknown_candidate(_residual("observation_action_boundary_drift", (observation_actions,)))
    program = _extract_g5_program(training)
    if isinstance(program, UnknownResidual):
        return _unknown_candidate(program, observation_actions)
    try:
        roles = tuple(event_role_records(event_observation.get("events", ())))
    except ValueError as error:
        return _unknown_candidate(_residual("g6_lifecycle_census", (str(error),)), observation_actions)
    columns = _compile_hierarchical_columns(program, roles)
    if isinstance(columns, UnknownResidual):
        return _unknown_candidate(columns, observation_actions)
    execution = dict((executor or _execute_projection)(columns))
    execution["action_count"] = observation_actions + int(execution.get("action_count", 0))
    candidate = {
        "status": "CANDIDATE",
        "law": "G6 chronological lifecycle inherits terminal-warranted G5 program",
        "chronological_program": [row["control"] for row in program],
        "roles": list(roles),
        "spatial_program": [
            row["control"]
            for row in sorted(
                ({"control": instruction["control"], "marker_rank": role["marker_rank"]}
                 for role, instruction in zip(roles, program)),
                key=lambda row: row["marker_rank"],
            )
        ],
        "columns": [list(column) for column in columns],
        **execution,
    }
    candidate["semantic_id"] = canonical_digest((
        INTERFACE_ID, tuple(candidate["chronological_program"]),
        tuple(candidate["spatial_program"]), columns,
    ))
    return candidate


def _source_head():
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=Path(__file__).resolve().parents[1], text=True).strip()


def _identity(candidate):
    return (
        candidate.get("semantic_id"), candidate.get("terminal"), candidate.get("progressed"),
        candidate.get("target_writes"), candidate.get("submit_clicks"), candidate.get("action_count"),
    )


def _validate_candidate(candidate):
    if candidate.get("status") != "CANDIDATE" or not candidate.get("semantic_id"):
        raise ValueError("candidate_boundary")
    columns = tuple(_bits(row) for row in candidate.get("columns", ()))
    if (
        len(columns) != 6
        or not isinstance(candidate.get("progressed"), bool)
        or candidate.get("submit_clicks") != 1
        or not 0 <= int(candidate.get("target_writes", -1)) <= 36
        or not 13 <= int(candidate.get("action_count", -1)) <= ACTION_BUDGET
    ):
        raise ValueError("candidate_boundary")


def build_result(*, head=None, runner=None):
    head = head or _source_head()
    runner = runner or run_candidate
    base = {
        "schema": SCHEMA,
        "head": head,
        "model_calls": 0,
        "source_inspection": False,
        "action_budget_per_candidate": ACTION_BUDGET,
        "claim_boundary": (
            "exact public tn36; terminal-warranted G5 program XDDDTS; six legally observed "
            "G6 lifecycle roles; one hierarchical lift; two exact replays only on progress"
        ),
    }
    try:
        candidate = runner()
    except Exception as error:
        result = {**base, "status": "RESIDUAL", "classification": "NON_EVIDENCE", "candidate": None,
                  "verification": [], "target_writes": 0,
                  "residual": {"reason": "candidate_exception", "error": f"{type(error).__name__}:{error}"}}
        validate_result(result, executing_head=head)
        return result
    if candidate.get("status") == "UNKNOWN":
        result = {**base, "status": "RESIDUAL", "classification": "EXACT_RESIDUAL", "candidate": candidate,
                  "verification": [], "target_writes": 0, "residual": candidate["residual"]}
        validate_result(result, executing_head=head)
        return result
    _validate_candidate(candidate)
    if not candidate["progressed"]:
        result = {**base, "status": "REJECTED", "classification": "WARRANTED_NEGATIVE", "candidate": candidate,
                  "verification": [], "target_writes": candidate["target_writes"]}
        validate_result(result, executing_head=head)
        return result
    verification = []
    try:
        verification = [runner(), runner()]
    except Exception as error:
        result = {**base, "status": "RESIDUAL", "classification": "NON_EVIDENCE", "candidate": candidate,
                  "verification": verification, "target_writes": candidate["target_writes"],
                  "residual": {"reason": "verification_exception", "error": f"{type(error).__name__}:{error}"}}
        validate_result(result, executing_head=head)
        return result
    if any(row.get("status") != "CANDIDATE" or not row.get("progressed") or _identity(row) != _identity(candidate) for row in verification):
        result = {**base, "status": "RESIDUAL", "classification": "NON_EVIDENCE", "candidate": candidate,
                  "verification": verification, "target_writes": candidate["target_writes"],
                  "residual": {"reason": "verification_identity_drift"}}
        validate_result(result, executing_head=head)
        return result
    result = {**base, "status": "PROMOTED", "classification": "WARRANTED_POSITIVE", "candidate": candidate,
              "verification": verification, "target_writes": candidate["target_writes"]}
    validate_result(result, executing_head=head)
    return result


def validate_result(result, *, executing_head):
    if result.get("schema") != SCHEMA or result.get("head") != executing_head:
        raise ValueError("result_identity")
    if result.get("model_calls") != 0 or result.get("source_inspection") is not False or result.get("action_budget_per_candidate") != ACTION_BUDGET:
        raise ValueError("scientific_boundary")
    status = result.get("status")
    if status == "RESIDUAL":
        if result.get("classification") not in {"EXACT_RESIDUAL", "NON_EVIDENCE"} or not result.get("residual", {}).get("reason"):
            raise ValueError("residual_boundary")
        if result.get("classification") == "EXACT_RESIDUAL":
            candidate = result.get("candidate")
            if not candidate or candidate.get("status") != "UNKNOWN" or candidate.get("target_writes") != 0 or candidate.get("submit_clicks") != 0:
                raise ValueError("unknown_side_effect")
    elif status == "REJECTED":
        if result.get("classification") != "WARRANTED_NEGATIVE" or result.get("verification"):
            raise ValueError("negative_boundary")
        _validate_candidate(result["candidate"])
    elif status == "PROMOTED":
        if result.get("classification") != "WARRANTED_POSITIVE" or len(result.get("verification", ())) != 2:
            raise ValueError("positive_boundary")
        _validate_candidate(result["candidate"])
        for row in result["verification"]:
            _validate_candidate(row)
    else:
        raise ValueError("result_status")
    return result


def main():
    result = build_result()
    out = Path(os.environ.get("OUTDIR", "evidence/arc3-public-g6-hierarchical-program-lift")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"ARC3_PUBLIC_G6_HIERARCHICAL_PROGRAM_LIFT={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
