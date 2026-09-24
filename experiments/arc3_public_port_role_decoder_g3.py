from __future__ import annotations

import itertools
import json
import os
from pathlib import Path

OUT = Path(
    os.environ.get("OUTDIR", "evidence/arc3-public-port-role-decoder-g3")
).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A = (58, 46)
B = (58, 11)
C = (58, 20)
D = (58, 22)
E = (55, 20)
G2_GEN = [("A", A), ("B", B), ("C", C)]
G3_KNOWN = [("A", A), ("B", B), ("C", C), ("D", D), ("E", E)]

GameState = None
ab = None
g3 = None
glyphs = None
sem = None


def require_runtime():
    global GameState, ab, g3, glyphs, sem
    if ab is not None:
        return
    from arcengine import GameState as game_state
    import arc3_public_all_blue_to_gray_g2 as ab_module
    import arc3_public_panel_correspondence_g3 as g3_module
    import arc3_public_selector_glyph_decoder as glyphs_module
    import arc3_public_semantic_relation_g3 as sem_module

    GameState = game_state
    ab = ab_module
    g3 = g3_module
    glyphs = glyphs_module
    sem = sem_module


def truth(mask: int, before: int, after: int) -> int:
    return (mask >> ((before << 1) | after)) & 1


def distance_to_color(point, patch, color):
    cells = [
        (r, c)
        for r, row in enumerate(patch)
        for c, value in enumerate(row)
        if int(value) == color
    ]
    if not cells:
        raise AssertionError(f"color {color} absent from glyph")
    r, c = point
    return min(abs(r - rr) + abs(c - cc) for rr, cc in cells)


def classify_port_roles(patch, holes_local):
    holes = [tuple(x) for x in holes_local]
    if len(holes) != 2:
        raise AssertionError(f"expected two ports, got {holes}")
    ranked = sorted((distance_to_color(p, patch, 11), p) for p in holes)
    if ranked[0][0] == ranked[1][0]:
        raise AssertionError(f"color-11 distance does not separate ports: {ranked}")
    return {ranked[0][1]: "near", ranked[1][1]: "far"}


def decode_column(masks_by_role, role, before, after):
    mask = masks_by_role[role]
    return [truth(mask, b, a) for b, a in zip(before, after)]


def fit_role_masks(interventions, winner):
    survivors = []
    for near_mask, far_mask in itertools.product(range(16), repeat=2):
        masks = {"near": near_mask, "far": far_mask}
        if all(
            decode_column(masks, rec["role"], rec["before"], rec["after"])
            == winner
            for rec in interventions
        ):
            survivors.append((near_mask, far_mask))
    return survivors


def novel_mixed_pairs(survivors):
    return [pair for pair in survivors if pair[0] != pair[1]]


def protected(frame):
    if int(frame.levels_completed) > 2 or frame.state == GameState.WIN:
        return "PROGRESS"
    if frame.state == GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"


def enter_g2_generated():
    env = ab.env()
    ab.enter2(env)
    for _, rc in G2_GEN:
        ab.click(env, rc)
    return env


def enter_g3(prefix):
    env, _ = g3.enter_level3()
    for _, rc in prefix:
        ab.click(env, rc)
    return env


def source_bits(frame):
    return glyphs.source_bits(frame)[1]


def labeled_boxes(frame):
    boxes = glyphs.selector_boxes(frame)
    for box in boxes:
        role_by_local = classify_port_roles(box["patch"], box["holes_local"])
        box["port_roles"] = [
            role_by_local[tuple(local)] for local in box["holes_local"]
        ]
        box["port_distances"] = [
            distance_to_color(tuple(local), box["patch"], 11)
            for local in box["holes_local"]
        ]
    return boxes


def g2_supervision():
    base = enter_g2_generated()
    winner = source_bits(base.observation_space)
    boxes = labeled_boxes(base.observation_space)
    if len(boxes) != 2:
        raise AssertionError(f"expected two G2 selector glyphs, got {len(boxes)}")
    records = []
    for box in boxes:
        for hole, role in zip(box["holes"], box["port_roles"]):
            env = enter_g2_generated()
            before = source_bits(env.observation_space)
            ab.click(env, tuple(hole))
            after = source_bits(env.observation_space)
            records.append(
                {
                    "hole": hole,
                    "role": role,
                    "before": before,
                    "after": after,
                }
            )
    survivors = fit_role_masks(records, winner)
    return winner, boxes, records, survivors


def g3_records(prefix):
    base = enter_g3(prefix)
    boxes = labeled_boxes(base.observation_space)
    if len(boxes) != 3:
        raise AssertionError(f"expected three G3 selector glyphs, got {len(boxes)}")
    before = source_bits(base.observation_space)
    out = []
    for macro_index, box in enumerate(boxes):
        for hole, local, role, distance in zip(
            box["holes"],
            box["holes_local"],
            box["port_roles"],
            box["port_distances"],
        ):
            env = enter_g3(prefix)
            ab.click(env, tuple(hole))
            out.append(
                {
                    "macro_index": macro_index,
                    "hole": hole,
                    "hole_local": local,
                    "role": role,
                    "distance": distance,
                    "before": before,
                    "after": source_bits(env.observation_space),
                }
            )
    return boxes, out


def ordered_records(records, order_name):
    by_macro = {}
    for rec in records:
        by_macro.setdefault(rec["macro_index"], []).append(rec)
    ordered = []
    for macro_index in sorted(by_macro):
        group = by_macro[macro_index]
        if order_name == "screen":
            group = sorted(group, key=lambda x: tuple(x["hole"]))
        elif order_name == "screen-reverse":
            group = sorted(group, key=lambda x: tuple(x["hole"]), reverse=True)
        elif order_name == "near-far":
            group = sorted(group, key=lambda x: x["distance"])
        elif order_name == "far-near":
            group = sorted(group, key=lambda x: x["distance"], reverse=True)
        else:
            raise ValueError(order_name)
        ordered.extend(group)
    return ordered


def write_matrix(env, columns):
    matrix = [[columns[j][i] for j in range(6)] for i in range(6)]
    _, _, targets = sem.semantic_surface(env.observation_space)
    actions = []
    for i in range(6):
        for j in range(6):
            want = matrix[i][j]
            current = sem.bit(targets[i][j]["color"])
            if current == want:
                continue
            rc = tuple(targets[i][j]["rc"])
            ab.click(env, rc)
            actions.append({"i": i, "j": j, "rc": list(rc), "want": want})
            if protected(env.observation_space) != "CONTINUE":
                return matrix, actions
    return matrix, actions


def run_variant(prefix, pair, order_name, records):
    masks = {"near": pair[0], "far": pair[1]}
    ordered = ordered_records(records, order_name)
    columns = [
        decode_column(masks, rec["role"], rec["before"], rec["after"])
        for rec in ordered
    ]
    env = enter_g3(prefix)
    matrix, actions = write_matrix(env, columns)
    if protected(env.observation_space) == "CONTINUE":
        ab.click(env, A)
    return {
        "masks_near_far": list(pair),
        "order": order_name,
        "port_order": [
            {
                "macro_index": rec["macro_index"],
                "hole": rec["hole"],
                "role": rec["role"],
                "distance": rec["distance"],
            }
            for rec in ordered
        ],
        "columns": columns,
        "matrix": matrix,
        "write_count": len(actions),
        "outcome": protected(env.observation_space),
        "progressed": protected(env.observation_space) == "PROGRESS",
        "level": int(env.observation_space.levels_completed),
        "state": str(env.observation_space.state),
    }


def main():
    require_runtime()
    winner, g2_boxes, g2_records, survivors = g2_supervision()
    mixed = novel_mixed_pairs(survivors)
    if mixed != [(12, 14), (14, 12)]:
        raise AssertionError(f"unexpected mixed G2 survivors: {mixed}")

    tested = []
    selected = None
    verification = []
    diagnostics = []
    orders = ["screen", "screen-reverse", "near-far", "far-near"]

    for prefix_len in range(6):
        prefix = G3_KNOWN[:prefix_len]
        boxes, records = g3_records(prefix)
        diagnostics.append(
            {
                "prefix_len": prefix_len,
                "prefix": [name for name, _ in prefix],
                "boxes": boxes,
                "records": records,
            }
        )
        for pair in mixed:
            for order_name in orders:
                row = run_variant(prefix, pair, order_name, records)
                tested.append(
                    {
                        "prefix_len": prefix_len,
                        "prefix": [name for name, _ in prefix],
                        **row,
                    }
                )
                if row["progressed"]:
                    trials = [
                        run_variant(prefix, pair, order_name, records),
                        run_variant(prefix, pair, order_name, records),
                    ]
                    if all(trial["progressed"] for trial in trials):
                        selected = {
                            "prefix_len": prefix_len,
                            "prefix": [name for name, _ in prefix],
                            **row,
                        }
                        verification = trials
                        break
            if selected:
                break
        if selected:
            break

    status = "PROMOTED" if selected else "RESIDUAL"
    result = {
        "status": status,
        "hypothesis": (
            "the two holes in every transported selector glyph have an observed "
            "binary role given by distance to the color-11 block (NEAR/FAR); G2 "
            "supervision permits role-specific BEFORE or BEFORE-OR-AFTER decoders, "
            "and only the two mixed assignments are scientifically new"
        ),
        "g2": {
            "winner": winner,
            "boxes": g2_boxes,
            "interventions": g2_records,
            "surviving_mask_pairs_near_far": [list(x) for x in survivors],
            "new_mixed_pairs_near_far": [list(x) for x in mixed],
        },
        "g3_diagnostics": diagnostics,
        "orders": orders,
        "tested_variants": len(tested),
        "tested": tested,
        "selected": selected,
        "verification": verification,
        "model_calls": 0,
        "source_inspection": False,
        "max_g3_actions": 42,
        "claim_boundary": (
            "exact public tn36; role is the strict Manhattan-distance order from "
            "each observed singleton hole to the color-11 cells inside its containing "
            "size-41 selector glyph; G2 training uses the qualified A/B/C state and "
            "exact winning target; uniform (12,12) and (14,14) decoders are excluded "
            "because run 35960356431 already rejected them; transfer tests only the "
            "two newly G2-consistent mixed role decoders across prefixes 0..5 and "
            "four earned within-macro orders; terminal A; any progress replayed twice"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"ARC3_PUBLIC_PORT_ROLE_DECODER_G3={status}")


if __name__ == "__main__":
    main()
