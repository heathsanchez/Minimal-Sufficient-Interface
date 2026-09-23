from __future__ import annotations
import hashlib, itertools, json, logging, os
from pathlib import Path
from arc_agi import Arcade, OperationMode
from arcengine import GameAction, GameState

GAME="tn36-ef4dde99"
ENVROOT=Path(os.environ["ENVROOT"]).resolve()
OUT=Path(os.environ.get("OUTDIR","evidence/arc3-public-hidden-mode-separator-g2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

G1=[(55,36),(14,31),(42,26),(42,36),(42,41),(45,26),(45,36),(45,41),(55,36)]
ANCHOR=[(58,46),(58,11),(58,20),(58,22),(55,20)]
REC=(2,20)
REC_STEPS=55
PRIMS=["ACTION1","ACTION2","ACTION3","ACTION4","ACTION5","ACTION7"]
MAX_DEPTH=4

def env():
    l=logging.getLogger("hidden-mode"); l.setLevel(logging.WARNING)
    a=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(ENVROOT),logger=l)
    card=a.create_scorecard(); e=a.make(GAME,scorecard_id=card)
    if e is None: raise RuntimeError("game")
    return e

def grid(frame):
    x=frame.frame
    if isinstance(x,(list,tuple)): x=x[-1]
    if hasattr(x,"tolist"): x=x.tolist()
    return [[int(v) for v in row] for row in x]

def bh(frame):
    return hashlib.sha256(json.dumps(grid(frame),separators=(",",":")).encode()).hexdigest()

def mouse(e,rc):
    r,c=rc
    return e.step(GameAction.ACTION6,data={"x":c,"y":r})

def prim(e,name):
    return e.step(getattr(GameAction,name))

def enter_boundary(e):
    f=e.reset()
    if f is None: raise RuntimeError("reset")
    if int(f.levels_completed)==0:
        for rc in G1:
            f=mouse(e,rc)
            if f is None: raise RuntimeError("g1")
    if int(e.observation_space.levels_completed)!=1:
        raise RuntimeError(f"g1 drift {e.observation_space.levels_completed}")
    for rc in ANCHOR:
        f=mouse(e,rc)
        if f is None or int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError("anchor drift")
    for i in range(REC_STEPS):
        f=mouse(e,REC)
        if f is None or int(f.levels_completed)>1 or f.state in (GameState.WIN,GameState.GAME_OVER):
            raise RuntimeError(f"rec drift {i+1}")
    return e.observation_space

def outcome(frame):
    return {
        "level":int(frame.levels_completed),
        "state":str(frame.state),
        "board_hash":bh(frame),
        "progressed":int(frame.levels_completed)>1 or frame.state==GameState.WIN,
        "game_over":frame.state==GameState.GAME_OVER,
    }

def mouse_classes(e):
    classes={}
    for r in range(64):
        for c in range(64):
            enter_boundary(e)
            f=mouse(e,(r,c))
            if f is None: continue
            o=outcome(f)
            key=json.dumps(o,sort_keys=True,separators=(",",":"))
            rec=classes.setdefault(key,{"representative":[r,c],"count":0,"outcome":o})
            rec["count"]+=1
    return list(classes.values())

def apply_history(e,seq):
    enter_boundary(e)
    start_hash=bh(e.observation_space)
    trace=[]
    for name in seq:
        f=prim(e,name)
        if f is None: return {"valid":False,"trace":trace}
        trace.append({"action":name,**outcome(f)})
        if f.state in (GameState.WIN,GameState.GAME_OVER) or int(f.levels_completed)>1:
            break
    return {
        "valid":True,
        "trace":trace,
        "board_unchanged":bh(e.observation_space)==start_hash,
        "boundary_hash":start_hash,
        "after_hash":bh(e.observation_space),
        "terminal":outcome(e.observation_space),
    }

def suffix_outcome(e,seq,rc):
    h=apply_history(e,seq)
    if not h.get("valid"): return {"history":h,"mouse":None}
    if h["terminal"]["progressed"] or h["terminal"]["game_over"]:
        return {"history":h,"mouse":h["terminal"]}
    f=mouse(e,rc)
    return {"history":h,"mouse":outcome(f)}

def verify(seq,rc):
    outs=[]
    for _ in range(2):
        e=env(); z=suffix_outcome(e,seq,rc)
        outs.append({
            "progressed":bool(z["mouse"] and z["mouse"]["progressed"]),
            "history_board_unchanged":z["history"].get("board_unchanged"),
            "mouse":z["mouse"],
        })
    return outs

def main():
    e=env()
    classes=mouse_classes(e)
    reps=[tuple(x["representative"]) for x in classes]
    baseline={}
    for rc in reps:
        z=suffix_outcome(e,(),rc)
        baseline[rc]=z["mouse"]

    tested=0
    separators=[]
    selected=None
    selected_ver=[]
    per_depth={}
    for depth in range(1,MAX_DEPTH+1):
        counts={"histories":0,"unchanged_board":0,"separators":0,"progress":0}
        for seq in itertools.product(PRIMS,repeat=depth):
            counts["histories"]+=1; tested+=1
            # First classify the history alone.
            h=apply_history(e,seq)
            if not h.get("valid"): continue
            if h.get("board_unchanged"): counts["unchanged_board"]+=1
            if h["terminal"]["progressed"]:
                counts["progress"]+=1
                selected={"seq":list(seq),"mouse":None,"kind":"primitive_progress"}
                selected_ver=verify(seq,reps[0])  # records history behavior
                break
            # Distinguishing suffix bank = one mouse representative per exact baseline outcome class.
            changed=[]
            for rc in reps:
                z=suffix_outcome(e,seq,rc)
                mo=z["mouse"]
                if mo and mo["progressed"]:
                    counts["progress"]+=1
                    selected={"seq":list(seq),"mouse":list(rc),"kind":"mouse_suffix_progress"}
                    selected_ver=verify(seq,rc)
                    break
                if mo != baseline[rc]:
                    changed.append({"mouse":list(rc),"baseline":baseline[rc],"after_history":mo})
            if selected: break
            if changed:
                counts["separators"]+=1
                rec={"seq":list(seq),"board_unchanged":h.get("board_unchanged"),"changed_suffixes":changed}
                separators.append(rec)
                # A same-visible-board separator is exactly the history-state witness we seek.
                if h.get("board_unchanged"):
                    # Expand this history over every mouse coordinate to look for protected progress.
                    for r in range(64):
                        for c in range(64):
                            z=suffix_outcome(e,seq,(r,c))
                            if z["mouse"] and z["mouse"]["progressed"]:
                                selected={"seq":list(seq),"mouse":[r,c],"kind":"expanded_separator_progress"}
                                selected_ver=verify(seq,(r,c))
                                break
                        if selected: break
            if selected: break
        per_depth[str(depth)]=counts
        if selected: break

    ok=bool(selected and selected_ver and all(x["progressed"] for x in selected_ver))
    out={
        "boundary_actions":len(ANCHOR)+REC_STEPS,
        "baseline_mouse_classes":classes,
        "baseline_class_count":len(classes),
        "primitive_alphabet":PRIMS,
        "max_depth":MAX_DEPTH,
        "histories_tested":tested,
        "per_depth":per_depth,
        "same_board_separators":[x for x in separators if x["board_unchanged"]],
        "separator_count":len(separators),
        "selected":selected,
        "verification":selected_ver,
        "status":"PROMOTED" if ok else ("HISTORY_SEPARATOR" if any(x["board_unchanged"] for x in separators) else "RESIDUAL"),
        "model_calls":0,
        "source_inspection":False,
        "claim_boundary":"exact public tn36 G2 history-state separation using primitive histories and mouse distinguishing suffixes",
    }
    (OUT/"result.json").write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
    print("ARC3_PUBLIC_HIDDEN_MODE_SEPARATOR_G2="+out["status"])

if __name__=="__main__":
    main()
