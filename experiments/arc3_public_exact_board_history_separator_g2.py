from __future__ import annotations

import hashlib
import itertools
import json
import os
from collections import Counter
from pathlib import Path

from arcengine import GameAction, GameState

import arc3_public_direct_schema_g2 as ds

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-exact-board-history-separator-g2"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A = (58, 46)
B = (58, 11)
C = (58, 20)
D = (58, 22)
E = (55, 20)
REC = (2, 20)
BUNDLE = (54, 17)

# First exact direct-schema realization: three horizontal and three vertical
# toggles. Only the order is varied. If the toggles commute observationally,
# all 6! histories end at the identical visible board.
TOGGLES = [
    (33, 39), (33, 44), (33, 49),
    (36, 39), (36, 44), (36, 49),
]

PROBES = [
    ("mouse:A", "mouse", A),
    ("mouse:B", "mouse", B),
    ("mouse:C", "mouse", C),
    ("mouse:D", "mouse", D),
    ("mouse:E", "mouse", E),
    ("mouse:REC", "mouse", REC),
    ("mouse:BUNDLE", "mouse", BUNDLE),
    ("primitive:ACTION1", "primitive", "ACTION1"),
    ("primitive:ACTION2", "primitive", "ACTION2"),
    ("primitive:ACTION3", "primitive", "ACTION3"),
    ("primitive:ACTION4", "primitive", "ACTION4"),
    ("primitive:ACTION5", "primitive", "ACTION5"),
    ("primitive:ACTION7", "primitive", "ACTION7"),
]
VALID = {"PROGRESS", "GAME_OVER", "CONTINUE"}


def grid(f):
    x = f.frame
    if isinstance(x, (list, tuple)):
        x = x[-1]
    if hasattr(x, "tolist"):
        x = x.tolist()
    return [[int(v) for v in row] for row in x]


def board_hash(f):
    return hashlib.sha256(
        json.dumps(grid(f), separators=(",", ":")).encode()
    ).hexdigest()


def apply_action(e, action):
    _, kind, payload = action
    if kind == "mouse":
        return ds.click(e, tuple(payload))
    return e.step(getattr(GameAction, payload))


def replay_order(e, order):
    start, _ = ds.enter_level2(e)
    for rc in ds.SETUP:
        z = ds.click(e, rc)
        if z is None:
            raise RuntimeError("setup returned None")
    for rc in order:
        z = ds.click(e, tuple(rc))
        if z is None:
            raise RuntimeError("toggle returned None")
        if z.state == GameState.GAME_OVER or int(z.levels_completed) > 1 or z.state == GameState.WIN:
            raise RuntimeError("toggle order left the declared preterminal envelope")
    return start, e.observation_space


def protected_outcome(e, order, probe=None):
    _, f = replay_order(e, order)
    trace = []
    suffix = []
    if probe is not None:
        suffix.append(probe)
    suffix.append(("terminal:A", "mouse", A))
    for action in suffix:
        name, _, _ = action
        try:
            z = apply_action(e, action)
        except Exception as ex:
            return {
                "outcome": "INVALID",
                "error": type(ex).__name__,
                "action": name,
                "trace": trace,
            }
        if z is None:
            return {"outcome": "INVALID", "error": "NoneFrame", "action": name, "trace": trace}
        trace.append({
            "action": name,
            "level": int(z.levels_completed),
            "state": str(z.state),
        })
        if int(z.levels_completed) > 1 or z.state == GameState.WIN:
            return {"outcome": "PROGRESS", "trace": trace}
        if z.state == GameState.GAME_OVER:
            return {"outcome": "GAME_OVER", "trace": trace}
    return {"outcome": "CONTINUE", "trace": trace}


def verify_program(order, probe=None):
    rows = []
    for _ in range(2):
        e = ds.env()
        out = protected_outcome(e, order, probe)
        rows.append(out)
    return rows


def representative_orders():
    h1, h2, h3, v1, v2, v3 = TOGGLES
    raw = [
        [h1, h2, h3, v1, v2, v3],
        [v1, v2, v3, h1, h2, h3],
        [h1, v1, h2, v2, h3, v3],
        [v1, h1, v2, h2, v3, h3],
        [h3, h2, h1, v3, v2, v1],
        [v3, v2, v1, h3, h2, h1],
        [h1, v1, v2, h2, h3, v3],
        [v1, h1, h2, v2, v3, h3],
    ]
    out = []
    seen = set()
    for x in raw:
        k = tuple(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def main():
    source_net = ds.source_net()
    e = ds.env()

    # Exhaust the full order class for exact-board identity and direct terminal response.
    direct_rows = []
    board_hashes = Counter()
    outcomes = Counter()
    first_by_outcome = {}
    canonical_hash = None
    all_orders = list(itertools.permutations(TOGGLES))

    for i, order in enumerate(all_orders):
        start, f = replay_order(e, order)
        bh = board_hash(f)
        board_hashes[bh] += 1
        if canonical_hash is None:
            canonical_hash = bh
        target = ds.delta(start, ds.feat(f))
        rem = ds.residual(source_net, target)
        if rem:
            raise AssertionError(f"order {i} escaped zero-residual quotient: {rem}")

        # Same suffix A for every exact-board history.
        z = ds.click(e, A)
        if int(z.levels_completed) > 1 or z.state == GameState.WIN:
            outcome = "PROGRESS"
        elif z.state == GameState.GAME_OVER:
            outcome = "GAME_OVER"
        else:
            outcome = "CONTINUE"
        outcomes[outcome] += 1
        first_by_outcome.setdefault(outcome, {
            "order_index": i,
            "order": [list(x) for x in order],
            "board_hash": bh,
        })
        direct_rows.append((order, outcome))

    exact_board_class = len(board_hashes) == 1
    if not exact_board_class:
        raise AssertionError(f"permutations produced {len(board_hashes)} visible boards")

    # If terminal A itself splits the exact-board histories, we already have the
    # strongest one-step hidden-history separator. If it reaches progress, it is
    # also an executable G2 solution candidate.
    separator = None
    selected_program = None
    verification = []

    if "PROGRESS" in outcomes:
        witness = first_by_outcome["PROGRESS"]
        order = [tuple(x) for x in witness["order"]]
        verification = verify_program(order, None)
        if all(x["outcome"] == "PROGRESS" for x in verification):
            selected_program = [list(x) for x in ds.SETUP + order + [A]]

    if len(outcomes) > 1:
        keys = sorted(outcomes)
        left = first_by_outcome[keys[0]]
        right = first_by_outcome[keys[1]]
        lo = [tuple(x) for x in left["order"]]
        ro = [tuple(x) for x in right["order"]]
        separator = {
            "suffix": ["terminal:A"],
            "left": left,
            "right": right,
            "left_outcome": keys[0],
            "right_outcome": keys[1],
            "verification": {
                "left": verify_program(lo, None),
                "right": verify_program(ro, None),
            },
        }

    # If direct A does not split the full 720-order class, test a tiny response
    # bank on representative histories that are guaranteed to share the same
    # exact final board. This is still a history-only test, not board search.
    representative_results = []
    if separator is None and selected_program is None:
        reps = representative_orders()
        for probe in PROBES:
            rows = []
            for order in reps:
                out = protected_outcome(e, order, probe)
                rows.append({
                    "order": [list(x) for x in order],
                    "outcome": out["outcome"],
                    "trace": out["trace"],
                })
            counts = Counter(x["outcome"] for x in rows)
            representative_results.append({
                "probe": probe[0],
                "outcome_counts": dict(sorted(counts.items())),
            })
            valid_out = [x["outcome"] for x in rows]
            if set(valid_out).issubset(VALID) and len(set(valid_out)) > 1:
                li = 0
                ri = next(i for i in range(1, len(rows)) if rows[i]["outcome"] != rows[li]["outcome"])
                lo = [tuple(x) for x in rows[li]["order"]]
                ro = [tuple(x) for x in rows[ri]["order"]]
                separator = {
                    "suffix": [probe[0], "terminal:A"],
                    "left": rows[li],
                    "right": rows[ri],
                    "left_outcome": rows[li]["outcome"],
                    "right_outcome": rows[ri]["outcome"],
                    "verification": {
                        "left": verify_program(lo, probe),
                        "right": verify_program(ro, probe),
                    },
                }
                break

    if selected_program is not None:
        status = "SOLVED"
    elif separator is not None:
        status = "SEPARATOR"
    else:
        status = "NO_SEPARATOR"

    out = {
        "lineage": {
            "base_head": "e238ed3f59ad6055ce75a0b474274a29f450d7bd",
            "direct_schema_run": 35868828608,
            "direct_schema_artifact": 10754302499,
        },
        "hypothesis": (
            "if identical visible boards reached by different lawful histories have "
            "different protected future responses, snapshot state is insufficient"
        ),
        "toggle_set": [list(x) for x in TOGGLES],
        "permutations_tested": len(all_orders),
        "exact_board_hashes": dict(board_hashes),
        "exact_board_class": exact_board_class,
        "direct_terminal_outcomes": dict(sorted(outcomes.items())),
        "representative_probe_results": representative_results,
        "separator": separator,
        "selected_program": selected_program,
        "verification": verification,
        "max_level2_actions": len(ds.SETUP) + len(TOGGLES) + 2,
        "status": status,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "finite black-box hidden-history falsifier on all 6! orders of one exact "
            "zero-residual direct-schema toggle set on public tn36 G2; all histories "
            "must end at one exact board hash; terminal A is exhausted over all 720 "
            "orders and a fixed one-probe-plus-A bank is tested on eight representative "
            "orders; NO_SEPARATOR is not a proof of Markov/snapshot sufficiency"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print("ARC3_PUBLIC_EXACT_BOARD_HISTORY_SEPARATOR_G2=" + status)


if __name__ == "__main__":
    main()
