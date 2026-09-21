from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def state_key(event: dict[str, Any]) -> str:
    payload = {
        "board": event.get("board"),
        "level": event.get("level"),
        "score": event.get("score"),
        "state": event.get("state"),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def outcome(event: dict[str, Any]) -> str:
    if event.get("game_over"):
        return "GAME_OVER"
    if event.get("run_complete"):
        return "RUN_COMPLETE"
    if event.get("level_completed") or float(event.get("reward") or 0.0) > 0:
        return "PROGRESS"
    if not event.get("board_changed"):
        return "NO_BOARD_CHANGE"
    return "CHANGED"


def audit(events_dir: Path) -> dict[str, Any]:
    per_game: dict[str, Counter[str]] = defaultdict(Counter)
    totals: Counter[str] = Counter()
    run_rows: list[dict[str, Any]] = []

    files = sorted(events_dir.glob("*_events.jsonl"))
    for path in files:
        seen: dict[tuple[str, str], str] = {}
        last_state: str | None = None
        run: Counter[str] = Counter()
        game_id = path.name.split("_p", 1)[0]

        with path.open(encoding="utf-8") as fh:
            for raw in fh:
                if not raw.strip():
                    continue
                event = json.loads(raw)
                current_state = state_key(event)

                if event.get("type") == "action":
                    action = str(event.get("action_display") or event.get("action_name") or "").strip()
                    if action and action != "RESET" and last_state is not None:
                        result = outcome(event)
                        key = (last_state, action)
                        run["model_actions"] += 1
                        run[f"outcome_{result}"] += 1

                        if key in seen:
                            run["repeated_exact_state_action"] += 1
                            previous = seen[key]
                            if previous == result:
                                run["repeated_same_consequence"] += 1
                            if previous == "GAME_OVER":
                                run["repaid_known_terminal"] += 1
                            if previous == "NO_BOARD_CHANGE":
                                run["repaid_known_no_board_change"] += 1
                        else:
                            seen[key] = result

                last_state = current_state

        for k, v in run.items():
            totals[k] += v
            per_game[game_id][k] += v
        if run["repaid_known_terminal"] or run["repaid_known_no_board_change"]:
            run_rows.append(
                {
                    "file": path.name,
                    "game": game_id,
                    "model_actions": run["model_actions"],
                    "repeated_exact_state_action": run["repeated_exact_state_action"],
                    "repaid_known_terminal": run["repaid_known_terminal"],
                    "repaid_known_no_board_change": run["repaid_known_no_board_change"],
                }
            )

    game_rows = []
    for game, counts in per_game.items():
        game_rows.append(
            {
                "game": game,
                "model_actions": counts["model_actions"],
                "repeated_exact_state_action": counts["repeated_exact_state_action"],
                "repaid_known_terminal": counts["repaid_known_terminal"],
                "repaid_known_no_board_change": counts["repaid_known_no_board_change"],
                "terminal_repayment_rate": (
                    counts["repaid_known_terminal"] / counts["model_actions"]
                    if counts["model_actions"]
                    else 0.0
                ),
            }
        )
    game_rows.sort(
        key=lambda row: (
            -row["repaid_known_terminal"],
            -row["repaid_known_no_board_change"],
            row["game"],
        )
    )
    run_rows.sort(
        key=lambda row: (
            -row["repaid_known_terminal"],
            -row["repaid_known_no_board_change"],
            row["file"],
        )
    )

    model_actions = totals["model_actions"]
    strict_savings = totals["repaid_known_terminal"]
    advisory_savings = strict_savings + totals["repaid_known_no_board_change"]

    return {
        "source": "Tufalabs/duck-harness example-run",
        "tufa_head": "7652836056c59e044f093e3c13ed7438c814169e",
        "runs": len(files),
        "model_actions": model_actions,
        "repeated_exact_state_action": totals["repeated_exact_state_action"],
        "repeated_same_consequence": totals["repeated_same_consequence"],
        "repaid_known_terminal": strict_savings,
        "repaid_known_no_board_change": totals["repaid_known_no_board_change"],
        "strict_terminal_action_savings_fraction": (
            strict_savings / model_actions if model_actions else 0.0
        ),
        "terminal_plus_no_board_change_fraction": (
            advisory_savings / model_actions if model_actions else 0.0
        ),
        "games_with_terminal_repayments": sum(
            1 for row in game_rows if row["repaid_known_terminal"] > 0
        ),
        "games_with_no_board_change_repayments": sum(
            1 for row in game_rows if row["repaid_known_no_board_change"] > 0
        ),
        "top_games": game_rows[:25],
        "top_runs": run_rows[:50],
        "claim_boundary": {
            "strict": (
                "A DuckTape exact-state terminal guard would have refused these "
                "repeated environment actions on the recorded trajectories. "
                "Downstream counterfactual score is not inferred."
            ),
            "advisory": (
                "Repeated NO_BOARD_CHANGE events are counted separately and are "
                "not assumed safe to block because hidden state may exist."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("events_dir", type=Path)
    parser.add_argument("--out", type=Path, default=Path("duck-repayment-audit.json"))
    args = parser.parse_args()
    report = audit(args.events_dir)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("DUCK_REPAYMENT_AUDIT=PASS")


if __name__ == "__main__":
    main()
