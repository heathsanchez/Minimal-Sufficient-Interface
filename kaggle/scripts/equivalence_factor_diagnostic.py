"""Describe only the visual/component distinctions licensed as irrelevant by
closed ls20 interventional equivalence certificates.

The certificates come first. Geometry is used only after exact replay closure
has established bounded behavioral equivalence under every primitive action.
This diagnostic asks what structural variable differs inside those certified
classes, so candidate factor genesis is consequence-driven rather than guessed.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "equivalence-factor-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import interventional_separator_probe as sep
import interventional_closure_probe as closure

sep.OUT = OUT
sep.AGENT = AGENT
closure.OUT = OUT
closure.AGENT = AGENT

CLASSES = (
    (
        "000d17e88af90a0b78d60209177535fa2a60d3c5d293b14804a60e76be76aa01",
        "07c975565433ed56d235ececbb3dba47586f9b3c6f39b810a3b077d3bb38c57d",
    ),
    (
        "090cc48ca2cb6c721a0c6f9a0517590d2ca3e07e23b4a9e99185042ae0e1da81",
        "393685a8d92ddaf0e7d431786d71c7a35eca5fa58b40ced96c881b2719d05c0d",
    ),
    (
        "1054192bb3e05679bf8f08af54effe84ee96890cb6cf2ebc97ac510d15ed55ab",
        "4523b0d3d767aa9eefb96e41a337be2ef113494ad698f4427543cfbe6ad29c1c",
    ),
    (
        "357a07f24faf1f2dace51d8d2e7cb917e39a880e34e2a10186acc79d1a41e6fe",
        "5bd539e65dc22d2e0c65f59e980b8189665ba500a88d6869347b628b5ced34d7",
    ),
    (
        "5dda0f29b181a9cc5fcceb1f73668e188e06ea3a429f479b7c4807db098ce5e2",
        "6a50ca5fb858a45d005b9672ce9abae25d3b699192936c6c83d6f31dfd0a3617",
        "9d5efe83551026f9c20183c28e795ee23bbba5f69b7633f3e6e8fc48c23d7d26",
    ),
    (
        "8c43482f5e63d6c5697cb8b9cd17bf7d48ec3d1f7936c207bcf57648cb45225a",
        "e276f06bee69f8236641d4f95749fd6e545de45a92bda370f5c99a2bbdf95624",
    ),
)


def replay_frame(module, game_id, envdir, prefix, expected_digest):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ls20 unavailable")
    adapter = module.MyAgent(
        card_id="equivalence-factor-replay",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    latest = adapter._convert_raw_frame_data(env.observation_space)
    for action_id, x, y in prefix:
        action, data = sep.make_action(action_id, x, y)
        raw = env.step(action, data=data, reasoning={"source": "exact_replay"})
        latest = adapter._convert_raw_frame_data(raw)
    digest = module.normalize_frame(latest).evidence_sha256
    if digest != expected_digest:
        arc.close_scorecard()
        raise AssertionError("exact replay failed for certified class member")
    grid = module.settled_grid(latest)
    arc.close_scorecard()
    return grid


def shape_digest(shape):
    return hashlib.sha256(repr(shape).encode()).hexdigest()[:16]


def components(grid):
    if not grid:
        return []
    h, w = len(grid), len(grid[0])
    seen = set()
    rows = []
    for y in range(h):
        for x in range(w):
            if (x, y) in seen:
                continue
            value = int(grid[y][x])
            stack = [(x, y)]
            seen.add((x, y))
            cells = []
            while stack:
                px, py = stack.pop()
                cells.append((px, py))
                for nx, ny in (
                    (px - 1, py), (px + 1, py),
                    (px, py - 1), (px, py + 1),
                ):
                    if (
                        0 <= nx < w and 0 <= ny < h
                        and (nx, ny) not in seen
                        and int(grid[ny][nx]) == value
                    ):
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            ox = min(px for px, _ in cells)
            oy = min(py for _, py in cells)
            shape = tuple(sorted((px - ox, py - oy) for px, py in cells))
            bw = max(px for px, _ in cells) - ox + 1
            bh = max(py for _, py in cells) - oy + 1
            rows.append({
                "color": value,
                "area": len(cells),
                "bbox": [bw, bh],
                "shape": shape_digest(shape),
                "origin": [ox, oy],
            })
    return rows


def component_map(grid):
    out = defaultdict(list)
    for row in components(grid):
        key = (
            int(row["color"]),
            int(row["area"]),
            tuple(row["bbox"]),
            row["shape"],
        )
        out[key].append(tuple(row["origin"]))
    return {
        key: tuple(sorted(origins))
        for key, origins in out.items()
    }


def color_counts(grid):
    return Counter(int(v) for row in grid for v in row)


def diff_stats(left, right):
    points = []
    pairs = Counter()
    for y, (lrow, rrow) in enumerate(zip(left, right)):
        for x, (a, b) in enumerate(zip(lrow, rrow)):
            if int(a) != int(b):
                points.append((x, y))
                pairs[(int(a), int(b))] += 1
    if points:
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        bbox = [min(xs), min(ys), max(xs), max(ys)]
    else:
        bbox = None
    return {
        "changed_pixels": len(points),
        "bbox": bbox,
        "color_pairs": [
            {"from": a, "to": b, "count": count}
            for (a, b), count in pairs.most_common(12)
        ],
    }


def reproduce_certificate_context(module, q, prefixes, game_id, envdir, candidates):
    candidate_nodes = sorted({node for pair in candidates for node in pair})
    for node in candidate_nodes:
        for action in q.nodes[node].legal_actions:
            row = sep.replay_and_probe(
                module, game_id, envdir, prefixes[node], node, action
            )
            q.observe_node(
                row["target"],
                protected=tuple(row["target_protected"]),
                legal_actions=tuple(row["target_legal_actions"]),
            )
            q.observe_transition(
                row["source"], row["action"], row["target"],
                outcome=tuple(row["outcome"]),
            )
            candidate_prefix = tuple(prefixes[node]) + ((int(action), None, None),)
            old = prefixes.get(row["target"])
            if old is None or len(candidate_prefix) < len(old):
                prefixes[row["target"]] = candidate_prefix

    classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    survivors = [
        pair for pair in candidates
        if classes[pair[0]] == classes[pair[1]]
    ]
    assert len(survivors) == 4
    closer = closure.ClosureProbe(module, q, prefixes, game_id, envdir)
    results = [closer.close_root(pair) for pair in survivors]
    assert all(
        row["status"] == "CLOSED_BOUNDED_REPLAY_BISIMULATION"
        for row in results
    )
    return results


def main():
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ls20-")
    )
    game_id = game["game_id"]

    module, q, prefixes, source_meta = sep.build_frozen_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    original_nodes = set(q.nodes)
    classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    candidates = sep.merged_pairs(classes, original_nodes)
    assert len(candidates) == 15
    reproduce_certificate_context(
        module, q, prefixes, game_id, manifest["environments_dir"], candidates
    )

    class_reports = []
    changed_key_sets = []
    for class_id, group in enumerate(CLASSES):
        grids = []
        maps = []
        counts = []
        for digest in group:
            if digest not in prefixes:
                raise AssertionError("certificate member lacks exact replay prefix")
            grid = replay_frame(
                module, game_id, manifest["environments_dir"],
                prefixes[digest], digest,
            )
            grids.append(grid)
            maps.append(component_map(grid))
            counts.append(color_counts(grid))

        base_map = maps[0]
        all_keys = set().union(*(set(m) for m in maps))
        changed_components = []
        changed_signatures = set()
        for key in sorted(all_keys, key=repr):
            origins = [m.get(key, ()) for m in maps]
            if len(set(origins)) > 1:
                color, area, bbox, shape = key
                signature = (color, area, bbox, shape)
                changed_signatures.add(repr(signature))
                changed_components.append({
                    "color": color,
                    "area": area,
                    "bbox": list(bbox),
                    "shape": shape,
                    "origins": [
                        [list(origin) for origin in member_origins]
                        for member_origins in origins
                    ],
                })

        base_counts = counts[0]
        color_deltas = []
        colors = sorted(set().union(*(set(c) for c in counts)))
        for color in colors:
            values = [int(c.get(color, 0)) for c in counts]
            if len(set(values)) > 1:
                color_deltas.append({
                    "color": color,
                    "counts": values,
                    "range": max(values) - min(values),
                })

        pairwise = []
        for i in range(1, len(grids)):
            pairwise.append({
                "left": group[0],
                "right": group[i],
                **diff_stats(grids[0], grids[i]),
            })

        report = {
            "class_id": class_id,
            "members": list(group),
            "member_count": len(group),
            "pairwise_pixel_differences": pairwise,
            "changed_component_count": len(changed_components),
            "changed_components": changed_components[:24],
            "changed_color_counts": color_deltas,
        }
        class_reports.append(report)
        changed_key_sets.append(changed_signatures)
        print(
            "EQUIVALENCE_FACTOR_CLASS="
            + json.dumps(report, sort_keys=True),
            flush=True,
        )

    shared_changed_components = sorted(
        set.intersection(*changed_key_sets)
        if changed_key_sets else set()
    )
    union_changed_components = sorted(
        set.union(*changed_key_sets)
        if changed_key_sets else set()
    )

    report = {
        "interpretation": (
            "post-certificate structural description of distinctions inside "
            "closed ls20 interventional equivalence classes; consequence "
            "evidence licenses the classes before any visual factor proposal"
        ),
        "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
        "game_id": game_id,
        "source_trace": source_meta,
        "class_count": len(CLASSES),
        "classes": class_reports,
        "shared_changed_component_signatures": shared_changed_components,
        "union_changed_component_signature_count": len(union_changed_components),
    }
    audit.write_json(OUT / "equivalence-factor.json", report)
    print(
        "EQUIVALENCE_FACTOR_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_EQUIVALENCE_FACTOR_DIAGNOSTIC=PASS", flush=True)


if __name__ == "__main__":
    main()
