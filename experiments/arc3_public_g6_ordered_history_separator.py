from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
import subprocess

from metalogic_arc3.protected_future import canonical_digest
from metalogic_arc3.semantic_path import _matrix, _selector_controls, _source_bits


SCHEMA = "arc3.g6-ordered-history-separator@1"
PREFIX = "RRRRUULLUU"
HISTORY_PAIRS = (("UL", "LL"), ("LU", "UU"))
SUFFIXES = ("", "U", "D", "L", "R")
ACTION_BUDGET = 13
PROTECTED_FIELDS = (
    "visible_digest",
    "changes",
    "source_bits",
    "level",
    "state",
)


def _public_field(frame, name: str):
    return frame[name] if isinstance(frame, Mapping) else getattr(frame, name)


def _normalized_matrix(value) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(row) for row in _matrix(value))


def observation_record(
    prefix_matrix: Sequence[Sequence[int]],
    frame,
    trace: Sequence[str],
) -> dict[str, object]:
    prefix = _normalized_matrix(prefix_matrix)
    visible = _normalized_matrix(frame)
    if (
        len(prefix) != len(visible)
        or not prefix
        or any(len(left) != len(right) for left, right in zip(prefix, visible))
    ):
        raise ValueError("observation_dimensions")
    changes = [
        {
            "row": row,
            "column": column,
            "before": prefix[row][column],
            "after": visible[row][column],
        }
        for row in range(len(prefix))
        for column in range(len(prefix[row]))
        if prefix[row][column] != visible[row][column]
    ]
    bits = tuple(int(bit) for bit in _source_bits(visible))
    if len(bits) != 6 or any(bit not in (0, 1) for bit in bits):
        raise ValueError("source_bit_arity")
    return {
        "visible_digest": canonical_digest(("arc.visible-matrix@1", visible)),
        "changes": changes,
        "source_bits": list(bits),
        "level": int(_public_field(frame, "levels_completed")),
        "state": str(_public_field(frame, "state")),
        "trace": [str(action) for action in trace],
    }


def _semantic_id(row: Mapping[str, object]) -> str:
    return canonical_digest(
        (
            "g6-ordered-history-trial@1",
            row["history"],
            row["endpoint"],
            row["suffix"],
            row["prefix_digest"],
            row["prefix_observation"],
            row["first_observation"],
            row["endpoint_observation"],
            row["suffix_observation"],
            row["action_count"],
            row["target_writes"],
            row["submit_clicks"],
        )
    )


def _observation_differences(
    left: Mapping[str, object],
    right: Mapping[str, object],
) -> list[str]:
    return [field for field in PROTECTED_FIELDS if left.get(field) != right.get(field)]


def compare_trials(
    left: Mapping[str, object],
    right: Mapping[str, object],
) -> dict[str, object]:
    if left.get("endpoint") != right.get("endpoint"):
        raise ValueError("comparison_endpoint")
    if left.get("suffix") != right.get("suffix"):
        raise ValueError("comparison_suffix")
    if left.get("prefix_digest") != right.get("prefix_digest"):
        raise ValueError("comparison_prefix")
    if _observation_differences(
        left["prefix_observation"], right["prefix_observation"]
    ):
        raise ValueError("comparison_prefix")
    witnesses = []
    endpoint_fields = _observation_differences(
        left["endpoint_observation"], right["endpoint_observation"]
    )
    if endpoint_fields:
        witnesses.append({"phase": "endpoint", "fields": endpoint_fields})
    suffix = str(left["suffix"])
    if suffix:
        suffix_fields = _observation_differences(
            left["suffix_observation"], right["suffix_observation"]
        )
        if suffix_fields:
            witnesses.append({"phase": "suffix", "fields": suffix_fields})
    return {
        "histories": [str(left["history"]), str(right["history"])],
        "endpoint": str(left["endpoint"]),
        "suffix": suffix,
        "separated": bool(witnesses),
        "witnesses": witnesses,
        "trial_ids": [str(left["semantic_id"]), str(right["semantic_id"])],
    }


def _validate_trial(row: Mapping[str, object]) -> None:
    required = {
        "history",
        "endpoint",
        "suffix",
        "prefix_digest",
        "prefix_observation",
        "first_observation",
        "endpoint_observation",
        "suffix_observation",
        "action_count",
        "target_writes",
        "submit_clicks",
        "semantic_id",
    }
    if not required.issubset(row):
        raise ValueError("trial_evidence")
    history = str(row["history"])
    suffix = str(row["suffix"])
    if len(history) != 2 or str(row["endpoint"]) != history[-1] or suffix not in SUFFIXES:
        raise ValueError("trial_shape")
    expected_action_count = len(PREFIX) + len(history) + len(suffix)
    if int(row["action_count"]) != expected_action_count:
        raise ValueError("trial_action_count")
    if int(row["action_count"]) > ACTION_BUDGET:
        raise ValueError("trial_action_budget")
    if int(row["target_writes"]) != 0 or int(row["submit_clicks"]) != 0:
        raise ValueError("scientific_boundary")
    expected_traces = {
        "prefix_observation": PREFIX,
        "first_observation": PREFIX + history[0],
        "endpoint_observation": PREFIX + history,
        "suffix_observation": PREFIX + history + suffix,
    }
    for key, expected_trace in expected_traces.items():
        _validate_observation(row[key], expected_trace)
    if row["prefix_observation"]["changes"] != []:
        raise ValueError("prefix_observation_changes")
    if suffix == "" and row["suffix_observation"] != row["endpoint_observation"]:
        raise ValueError("empty_suffix_observation")
    if row["semantic_id"] != _semantic_id(row):
        raise ValueError("trial_semantic_id")


def _validate_observation(observation, expected_trace: str) -> None:
    if not isinstance(observation, Mapping) or any(
        field not in observation for field in PROTECTED_FIELDS + ("trace",)
    ):
        raise ValueError("trial_observation")
    digest = observation["visible_digest"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("trial_observation")
    changes = observation["changes"]
    if not isinstance(changes, list):
        raise ValueError("trial_observation")
    coordinates = []
    for change in changes:
        if not isinstance(change, Mapping) or set(change) != {
            "row", "column", "before", "after"
        }:
            raise ValueError("trial_observation")
        values = tuple(change[field] for field in ("row", "column", "before", "after"))
        if any(not isinstance(value, int) for value in values):
            raise ValueError("trial_observation")
        if change["row"] < 0 or change["column"] < 0 or change["before"] == change["after"]:
            raise ValueError("trial_observation")
        coordinates.append((change["row"], change["column"]))
    if coordinates != sorted(set(coordinates)):
        raise ValueError("trial_observation")
    bits = observation["source_bits"]
    if (
        not isinstance(bits, list)
        or len(bits) != 6
        or any(not isinstance(bit, int) or bit not in (0, 1) for bit in bits)
    ):
        raise ValueError("trial_observation")
    if observation["level"] != 5:
        raise ValueError("trial_observation")
    state = observation["state"]
    if not isinstance(state, str) or not state.endswith("NOT_FINISHED"):
        raise ValueError("trial_observation")
    trace = observation["trace"]
    if not isinstance(trace, list) or trace != list(expected_trace):
        raise ValueError("trial_trace")


def validate_result(result: Mapping[str, object], *, executing_head: str):
    if result.get("schema") != SCHEMA:
        raise ValueError("ordered_history_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    if (
        result.get("target_writes") != 0
        or result.get("submit_clicks") != 0
        or result.get("model_calls") != 0
        or result.get("source_inspection") is not False
    ):
        raise ValueError("scientific_boundary")
    if result.get("action_budget_per_trial") != ACTION_BUDGET:
        raise ValueError("action_budget_declaration")
    trials = tuple(result.get("trials", ()))
    for row in trials:
        _validate_trial(row)
    if result.get("status") == "RESIDUAL":
        if result.get("classification") != "NON_EVIDENCE":
            raise ValueError("residual_classification")
        if not result.get("residual", {}).get("reason"):
            raise ValueError("residual_reason")
        return result
    if (
        result.get("prefix") != PREFIX
        or tuple(tuple(pair) for pair in result.get("history_pairs", ())) != HISTORY_PAIRS
        or tuple(result.get("suffixes", ())) != SUFFIXES
    ):
        raise ValueError("declared_census")
    expected = [
        (history, suffix)
        for pair in HISTORY_PAIRS
        for suffix in SUFFIXES
        for history in pair
    ]
    observed = [(str(row["history"]), str(row["suffix"])) for row in trials]
    if observed != expected:
        raise ValueError("trial_census")
    if len({str(row["prefix_digest"]) for row in trials}) != 1:
        raise ValueError("prefix_drift")
    prefix_observations = {
        canonical_digest(
            (
                "g6-protected-prefix@1",
                {field: row["prefix_observation"][field] for field in PROTECTED_FIELDS},
            )
        )
        for row in trials
    }
    if len(prefix_observations) != 1:
        raise ValueError("prefix_drift")
    expected_comparisons = [
        compare_trials(trials[index], trials[index + 1])
        for index in range(0, len(trials), 2)
    ]
    if result.get("comparisons") != expected_comparisons:
        raise ValueError("comparison_evidence")
    separated = any(row["separated"] for row in expected_comparisons)
    expected_status = "RESPONSE_SEPARATOR_ONLY" if separated else "REJECTED"
    expected_classification = (
        "RESPONSE_SEPARATOR_ONLY" if separated else "WARRANTED_NEGATIVE"
    )
    if (
        result.get("status") != expected_status
        or result.get("classification") != expected_classification
    ):
        raise ValueError("derived_classification")
    return result


def _click_public(env, coordinate):
    import arc3_public_all_blue_to_gray_g2 as ab

    return ab.click(env, coordinate)


def _source_head() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    ).strip()


def run_trial(
    history: str,
    suffix: str,
    enter_g6=None,
) -> dict[str, object]:
    allowed_histories = {history for pair in HISTORY_PAIRS for history in pair}
    if history not in allowed_histories or suffix not in SUFFIXES:
        raise ValueError("trial_program")
    if enter_g6 is None:
        from arc3_public_g6_paired_route import enter_g6 as public_enter_g6

        enter_g6 = public_enter_g6
    env, frame = enter_g6()
    if int(_public_field(frame, "levels_completed")) != 5:
        raise ValueError("g6_entry_drift")
    controls = {
        label: (y, x)
        for (x, y), label in _selector_controls(_matrix(frame))
    }
    if set(controls) != {"U", "D", "L", "R"}:
        raise ValueError("missing_control")
    trace: list[str] = []

    def click(control: str):
        nonlocal frame
        if control not in controls:
            raise ValueError(f"missing_control:{control}")
        frame = _click_public(env, controls[control])
        trace.append(control)

    for control in PREFIX:
        click(control)
    prefix_matrix = _normalized_matrix(frame)
    prefix_digest = canonical_digest(("g6-qualified-prefix@1", prefix_matrix))
    prefix_observation = observation_record(prefix_matrix, frame, trace)
    if prefix_observation["level"] != 5 or not str(prefix_observation["state"]).endswith(
        "NOT_FINISHED"
    ):
        raise ValueError("g6_prefix_state")

    click(history[0])
    first = observation_record(prefix_matrix, frame, trace)
    click(history[1])
    endpoint = observation_record(prefix_matrix, frame, trace)
    if suffix:
        click(suffix)
        suffix_observation = observation_record(prefix_matrix, frame, trace)
    else:
        suffix_observation = endpoint
    if len(trace) > ACTION_BUDGET:
        raise ValueError("trial_action_budget")
    row = {
        "history": history,
        "endpoint": history[-1],
        "suffix": suffix,
        "prefix_digest": prefix_digest,
        "prefix_observation": prefix_observation,
        "first_observation": first,
        "endpoint_observation": endpoint,
        "suffix_observation": suffix_observation,
        "action_count": len(trace),
        "target_writes": 0,
        "submit_clicks": 0,
    }
    row["semantic_id"] = _semantic_id(row)
    _validate_trial(row)
    return row


def build_result(*, enter_g6=None, head: str | None = None, runner=None):
    runner = run_trial if runner is None else runner
    trials = []
    base = {
        "schema": SCHEMA,
        "head": head or _source_head(),
        "prefix": PREFIX,
        "history_pairs": [list(pair) for pair in HISTORY_PAIRS],
        "suffixes": list(SUFFIXES),
        "action_budget_per_trial": ACTION_BUDGET,
        "target_writes": 0,
        "submit_clicks": 0,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G6; qualified common prefix RRRRUULLUU; "
            "same-endpoint histories UL/LL and LU/UU; suffix bank epsilon/U/D/L/R; "
            "public visible observation only; zero target writes and submit clicks"
        ),
    }

    def residual(reason: str, *, error: str | None = None):
        payload = {
            **base,
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "trials": trials,
            "comparisons": [],
            "residual": {"reason": reason, "error": error},
        }
        validate_result(payload, executing_head=str(payload["head"]))
        return payload

    for pair in HISTORY_PAIRS:
        for suffix in SUFFIXES:
            for history in pair:
                try:
                    row = runner(history, suffix, enter_g6)
                    _validate_trial(row)
                    trials.append(row)
                except Exception as error:
                    return residual(
                        "trial_exception",
                        error=f"{type(error).__name__}:{error}",
                    )
    if len({str(row["prefix_digest"]) for row in trials}) != 1:
        return residual("common_prefix_drift")
    prefix_observations = {
        canonical_digest(
            (
                "g6-protected-prefix@1",
                {field: row["prefix_observation"][field] for field in PROTECTED_FIELDS},
            )
        )
        for row in trials
    }
    if len(prefix_observations) != 1:
        return residual("common_prefix_drift")
    try:
        comparisons = [
            compare_trials(trials[index], trials[index + 1])
            for index in range(0, len(trials), 2)
        ]
    except Exception as error:
        return residual(
            "comparison_exception",
            error=f"{type(error).__name__}:{error}",
        )
    separated = any(row["separated"] for row in comparisons)
    result = {
        **base,
        "status": "RESPONSE_SEPARATOR_ONLY" if separated else "REJECTED",
        "classification": (
            "RESPONSE_SEPARATOR_ONLY" if separated else "WARRANTED_NEGATIVE"
        ),
        "trials": trials,
        "comparisons": comparisons,
    }
    validate_result(result, executing_head=str(result["head"]))
    return result


def main():
    result = build_result()
    out = Path(
        os.environ.get(
            "OUTDIR",
            "evidence/arc3-public-g6-ordered-history-separator",
        )
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(f"ARC3_PUBLIC_G6_ORDERED_HISTORY_SEPARATOR={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
