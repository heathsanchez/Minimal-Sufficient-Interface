from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_semantic_relation_g3 as sem
import arc3_public_panel_correspondence_g3 as g3
import arc3_public_all_blue_to_gray_g2 as ab

OUT=Path(os.environ.get(
    "OUTDIR","evidence/arc3-public-compiled-state-trace-g3"
)).resolve()
OUT.mkdir(parents=True,exist_ok=True)

A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)
KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]


def snapshot_bits(f):
    rows,source,targets=sem.semantic_surface(f)
    return rows,list(source),targets


def collect_trace():
    e,trace=g3.enter_level3()
    rows,bits,targets=snapshot_bits(e.observation_space)
    states=[bits]
    events=[{"stage":"initial","bits":bits}]
    for name,rc in KNOWN:
        z=ab.click(e,rc)
        rows2,bits2,targets2=snapshot_bits(e.observation_space)
        if rows2!=rows:
            raise AssertionError("row identity changed")
        states.append(bits2)
        events.append({
            "stage":name,"rc":list(rc),"bits":bits2,
            "level":int(z.levels_completed),"state":str(z.state)
        })
        if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
            raise AssertionError("generator progressed unexpectedly")
    if len(states)!=6:
        raise AssertionError(len(states))
    return e,rows,states,events


def transform(states,mode):
    cols=[list(x) for x in states]
    if "reverse_time" in mode:
        cols=list(reversed(cols))
    # matrix rows x columns
    M=[[cols[j][i] for j in range(6)] for i in range(6)]
    if "complement" in mode:
        M=[[1-v for v in row] for row in M]
    return M


MODES=[
    "chronological",
    "reverse_time",
    "chronological_complement",
    "reverse_time_complement",
]


def write_matrix(e,M):
    rows,source,targets=sem.semantic_surface(e.observation_space)
    actions=[]
    for i in range(6):
        for j in range(6):
            cur=sem.bit(targets[i][j]["color"])
            want=M[i][j]
            if cur==want:
                continue
            rc=tuple(targets[i][j]["rc"])
            z=ab.click(e,rc)
            actions.append({
                "i":i,"j":j,"rc":list(rc),
                "before":cur,"want":want,
            })
            if int(z.levels_completed)>2 or z.state in (GameState.WIN,GameState.GAME_OVER):
                break
        if int(e.observation_space.levels_completed)>2 or e.observation_space.state in (GameState.WIN,GameState.GAME_OVER):
            break
    return actions


def run_mode(mode):
    e,rows,states,events=collect_trace()
    M=transform(states,mode)
    actions=write_matrix(e,M)

    if int(e.observation_space.levels_completed)==2 and e.observation_space.state==GameState.NOT_FINISHED:
        z=ab.click(e,A)
        submit={"level":int(z.levels_completed),"state":str(z.state)}
    else:
        submit={"level":int(e.observation_space.levels_completed),"state":str(e.observation_space.state)}

    return {
        "mode":mode,
        "rows":rows,
        "states":states,
        "events":events,
        "compiled_matrix":M,
        "write_count":len(actions),
        "progressed":int(e.observation_space.levels_completed)>2 or e.observation_space.state==GameState.WIN,
        "level":int(e.observation_space.levels_completed),
        "state":str(e.observation_space.state),
        "submit":submit,
    }


def main():
    tested=[]
    selected=None
    verification=[]

    for mode in MODES:
        row=run_mode(mode)
        tested.append(row)
        if row["progressed"]:
            vv=[run_mode(mode),run_mode(mode)]
            if all(x["progressed"] for x in vv):
                selected={
                    "mode":mode,
                    "states":row["states"],
                    "compiled_matrix":row["compiled_matrix"],
                    "write_count":row["write_count"],
                }
                verification=vv
                break

    status="PROMOTED" if selected is not None else "RESIDUAL"
    out={
        "status":status,
        "parent_transition_graph_head":"d5b9e623192f237731188467212dc2f47d7cee36",
        "parent_transition_graph_run":35930875310,
        "hypothesis":"the G3 6x6 target is the compiled consequential state trace: six row identities by six stages (initial,A,B,C,D,E), not a graph over the final state",
        "modes":MODES,
        "tested":tested,
        "selected":selected,
        "verification":verification,
        "model_calls":0,
        "source_inspection":False,
        "max_g3_actions":42,
        "claim_boundary":"exact public tn36 G3 after qualified G1+G2; source trace consists only of the observed six-row predicate at initial state and after A/B/C/D/E; target rows are shared geometric row identities; target columns are tested only as chronological or reversed stage order, with direct/complement color conventions; terminal A; any progress replayed twice",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_COMPILED_STATE_TRACE_G3="+status)


if __name__=="__main__":
    main()
