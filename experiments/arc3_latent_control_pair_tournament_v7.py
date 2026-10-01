"""V7 collision-local latent pair tournament.

V6 earned same_action_run as the only scalar that reduced the ka59-L1
prospective no-op residual. V7 freezes that coordinate and tests exactly one
additional scalar at a time. V4's changed-effect representation remains frozen.

Important: this reuses the already-observed V6 corpus/split, so a zero-error
pair is diagnostic CANDIDATE evidence only. Promotion requires a fresh
prospective trajectory/holdout gate.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path

from arc3_latent_control_tournament_v6 import traced, train


def empty_total():
    return dict(cells=0, known=0, wrong=0, folds=[])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    games = defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):
        games[p.name.split("_p", 1)[0]].append(traced(p))

    second_coordinates = (
        "prev_action",
        "prev_effect",
        "since_change",
        "since_reset",
    )
    first_total = empty_total()
    totals = {q: empty_total() for q in second_coordinates}

    for game, trs in sorted(games.items()):
        cal = [tr for i, tr in enumerate(trs) if i % 2 == 0]
        ev = [tr for i, tr in enumerate(trs) if i % 2 == 1]

        for target in sorted({r[0] for tr in trs for r in tr if r[0] > 0}):
            coarse = train(cal, target, lambda r: r[1], 4)

            noop_bad = set()
            effect_bad = set()
            for tr in cal:
                for row in tr:
                    lev, c, _, _, y, _, _ = row
                    if lev != target or c not in coarse or coarse[c] == y:
                        continue
                    if y[0] == "same" or coarse[c][0] == "same":
                        noop_bad.add(c)
                    else:
                        effect_bad.add(c)

            # Preserve V4 changed->changed behavior exactly.
            me = train(cal, target, lambda r: r[2], 5)

            # V6-earned first coordinate.
            first = train(
                cal,
                target,
                lambda r: (r[1], r[6]["same_action_run"]),
                4,
            )
            pair_maps = {
                q: train(
                    cal,
                    target,
                    lambda r, q=q: (
                        r[1],
                        r[6]["same_action_run"],
                        r[6][q],
                    ),
                    4,
                )
                for q in second_coordinates
            }

            fk = fw = fn = 0
            ck = {q: 0 for q in second_coordinates}
            cw = {q: 0 for q in second_coordinates}
            cn = {q: 0 for q in second_coordinates}

            for tr in ev:
                for row in tr:
                    lev, c, f, _, y, e, ctrl = row
                    if lev != target:
                        continue

                    fn += 1
                    for q in second_coordinates:
                        cn[q] += 1

                    if c in effect_bad:
                        first_pred = me.get(f)
                        first_actual = e
                        pair_pred = {q: first_pred for q in second_coordinates}
                        pair_actual = {q: e for q in second_coordinates}
                    elif c in noop_bad:
                        first_pred = first.get((c, ctrl["same_action_run"]))
                        first_actual = y
                        pair_pred = {
                            q: pair_maps[q].get(
                                (c, ctrl["same_action_run"], ctrl[q])
                            )
                            for q in second_coordinates
                        }
                        pair_actual = {q: y for q in second_coordinates}
                    else:
                        first_pred = coarse.get(c)
                        first_actual = y
                        pair_pred = {q: first_pred for q in second_coordinates}
                        pair_actual = {q: y for q in second_coordinates}

                    if first_pred is not None:
                        fk += 1
                        fw += first_pred != first_actual

                    for q in second_coordinates:
                        pred = pair_pred[q]
                        if pred is not None:
                            ck[q] += 1
                            cw[q] += pred != pair_actual[q]

            first_total["cells"] += fn
            first_total["known"] += fk
            first_total["wrong"] += fw
            if fn:
                first_total["folds"].append(
                    dict(
                        game=game,
                        target_level=target,
                        cells=fn,
                        known=fk,
                        wrong=fw,
                        coverage=fk / fn,
                        refined_roles=len(noop_bad),
                    )
                )

            for q in second_coordinates:
                t = totals[q]
                t["cells"] += cn[q]
                t["known"] += ck[q]
                t["wrong"] += cw[q]
                if cn[q]:
                    t["folds"].append(
                        dict(
                            game=game,
                            target_level=target,
                            cells=cn[q],
                            known=ck[q],
                            wrong=cw[q],
                            coverage=ck[q] / cn[q],
                            refined_roles=len(noop_bad),
                        )
                    )

    first_total["coverage"] = (
        first_total["known"] / first_total["cells"] if first_total["cells"] else 0
    )
    for q, t in totals.items():
        t["coverage"] = t["known"] / t["cells"] if t["cells"] else 0

    ranking = sorted(
        second_coordinates,
        key=lambda q: (totals[q]["wrong"], -totals[q]["known"], q),
    )
    best = ranking[0]

    out = dict(
        schema="msi.arc3-latent-control-pair-tournament-v7",
        first_coordinate="same_action_run",
        v6_first_baseline=first_total,
        second_candidates=totals,
        ranking=ranking,
        best_pair=["same_action_run", best],
        status=(
            "ZERO_ERROR_PAIR_CANDIDATE"
            if totals[best]["known"] and totals[best]["wrong"] == 0
            else "EXACT_RESIDUAL"
        ),
        epistemic_scope="CANDIDATE_DIAGNOSTIC_ON_ALREADY_OBSERVED_V6_SPLIT",
        promotion_requires_fresh_prospective_holdout=True,
        game_prefix=a.game_prefix,
        boundary=(
            "V4 effect branch frozen exactly. V6-earned same_action_run is fixed; "
            "one additional scalar at a time only on calibration-earned no-op "
            "collisions. No triples and no new state ontology."
        ),
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
