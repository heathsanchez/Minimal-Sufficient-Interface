"""Source-blind continuation from the three-stage verified archive.

Archived observations propose coordinates, never solutions. Frozen execution,
fresh replay, the shared Lean gate, and cumulative accounting remain in force.
"""
import argparse
import hashlib
import json
import logging
from collections import deque
from pathlib import Path

import numpy as np
import arc3_archive_transfer as A
import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F

TRANSFER_RUN = 34272649151
TRANSFER_SHA256 = "0eba01df78865553b1be566d1544e77ef2d6a5006cb1b312d7c04e8c6c0eff51"


def verified_entry(source, report, transfer, evidence, actions):
    stages = A.select_archive(report, source, actions)
    prefix = tuple(map(F.atom, stages[-1]["prefix"]))
    if (transfer.get("status") != "ALL_LEVELS_WITNESSED"
            or transfer.get("source_run") != M.SOURCE_RUN
            or transfer.get("archive_run") != A.ARCHIVE_RUN
            or transfer.get("source_commit") != T.FROZEN
            or transfer.get("initial_sha256") != source["initial_sha256"]
            or transfer.get("checkpoint_sha256") != stages[-1]["checkpoint_sha256"]
            or tuple(map(F.atom, transfer.get("prefix", ()))) != prefix
            or transfer.get("levels_witnessed") != len(stages)
            or len(transfer.get("accepted", ())) != len(stages)
            or transfer["warm"]["state"] != "NOT_FINISHED"
            or transfer["warm"]["levels_completed"] != len(stages)
            or transfer["warm"]["final_sha256"] != stages[-1]["checkpoint_sha256"]):
        raise ValueError("Unqualified archive transfer")
    proof, replay = evidence["proof"], evidence["replay"]
    if (evidence.get("source_commit") != T.FROZEN
            or evidence.get("initial_sha256") != source["initial_sha256"]
            or tuple(map(F.atom, evidence.get("program", ()))) != prefix
            or proof["status"] != "OBSERVED" or replay["status"] != "OBSERVED"
            or tuple(map(F.atom, proof["executed"])) != prefix
            or proof["observations"] != replay["observations"]
            or proof["initial_sha256"] != source["initial_sha256"]
            or proof["final_sha256"] != stages[-1]["checkpoint_sha256"]
            or proof["levels_completed"] != len(stages)
            or proof["state"] != "NOT_FINISHED"
            or len(proof["observations"]) != len(prefix) + 1
            or F.digest(proof["observations"][0]) != source["initial_sha256"]
            or F.digest(proof["observations"][-1]) != proof["final_sha256"]):
        raise ValueError("Archived replay mismatch")
    identity = T.digest({"kind":"arc3_witnessed_policy",
        "evidence_sha256":T.digest(evidence), "program":prefix,
        "source_commit":T.FROZEN})
    accepted = transfer["accepted"][-1]
    if (accepted["promotion"] != identity
            or accepted["checkpoint_sha256"] != proof["final_sha256"]
            or tuple(map(F.atom, accepted["prefix"])) != prefix
            or not accepted.get("gate_source_sha256")):
        raise ValueError("Archived promotion mismatch")
    return proof["observations"][-1]


def component_actions(observation, available, limit=48):
    """Generic public-pixel coordinate grammar, with the old grammar retained."""
    if 6 not in available:
        return ()
    frames = observation.get("frame", ())
    if not frames:
        return ()
    image = np.asarray(frames[0])
    if image.ndim != 2 or not image.size:
        return ()
    h, w = image.shape
    values, counts = np.unique(image, return_counts=True)
    background = values[int(np.argmax(counts))]
    candidates = []
    def add(x, y):
        x, y = int(x), int(y)
        if 0 <= x < w and 0 <= y < h:
            candidates.append((6, x, y))
    components = []
    for value in values:
        if value == background:
            continue
        mask = image == value
        seen = np.zeros(mask.shape, dtype=bool)
        for y in range(h):
            for x in range(w):
                if not mask[y,x] or seen[y,x]:
                    continue
                stack, pixels = [(y,x)], []
                seen[y,x] = True
                while stack:
                    cy,cx = stack.pop()
                    pixels.append((cy,cx))
                    for ny,nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny,nx] and not seen[ny,nx]:
                            seen[ny,nx] = True
                            stack.append((ny,nx))
                components.append(pixels)
    components.sort(key=lambda p:(-len(p),min(p)))
    for pixels in components:
        ys, xs = [p[0] for p in pixels], [p[1] for p in pixels]
        cy,cx = (min(ys)+max(ys))/2, (min(xs)+max(xs))/2
        representative = min(pixels,key=lambda p:((p[0]-cy)**2+(p[1]-cx)**2,p))
        add(representative[1],representative[0])
        add(round(cx),round(cy))
        for p in (min(pixels),max(pixels),min(pixels,key=lambda p:p[1]),
                  max(pixels,key=lambda p:p[1])):
            add(p[1],p[0])
    for y in range(4,h,8):
        for x in range(4,w,8):
            add(x,y)
    return tuple(dict.fromkeys(candidates))[:limit]


def observed_stage(execute_stage):
    """Record the public trace without changing the frozen executor."""
    def execute(env, prefix, suffix, target, budget, checkpoint=None, stop_at_progress=True):
        frames = []
        class Recorder:
            def __getattr__(self,name): return getattr(env,name)
            @property
            def observation_space(self):
                frame = env.observation_space
                if frame is not None and not frames: frames.append(F.observe(frame))
                return frame
            def reset(self):
                frame = env.reset()
                if not frames: frames.append(F.observe(frame))
                return frame
            def step(self,action):
                frame = env.step(action)
                if frame is not None: frames.append(F.observe(frame))
                return frame
        result = execute_stage(Recorder(),prefix,suffix,target,budget,checkpoint,
                               stop_at_progress=stop_at_progress)
        if len(frames) != result["actions"]+1:
            raise ValueError("Observation/action count mismatch")
        result["suffix_observations"] = frames[len(prefix):]
        return result
    return execute


def continuation_search(stages, proposed, all_actions, diagnostics=None):
    """Replay archived stages, then adapt repetition from observed consequences."""
    if diagnostics is None: diagnostics = []
    class Search:
        def __init__(self, actions, options=(), max_depth=32):
            self.max_depth = max_depth
            prefix = tuple(a for option in options for a in option)
            self.frontier = deque()
            self.seen = set()
            for stage in stages:
                full = tuple(map(F.atom,stage["prefix"]))
                suffix = tuple(map(F.atom,stage["suffix"]))
                if full[:len(prefix)] == prefix and len(full)>len(prefix):
                    if full == prefix+suffix: self.frontier.append(suffix)
                    return
            if prefix != tuple(map(F.atom,stages[-1]["prefix"])): return
            self.frontier = deque((a,) for a in dict.fromkeys(proposed+all_actions))
        def propose(self):
            while self.frontier:
                p = self.frontier.popleft()
                if p not in self.seen:
                    self.seen.add(p)
                    return p
            return None
        def retain(self,program,result):
            if result.get("progress",0)>0: return "PROGRESS_WITNESSED"
            if result.get("terminal"): return "TERMINAL_PREFIX"
            actual = tuple(result["executed"])
            observations = result.get("suffix_observations",())
            if not actual or len(observations)!=len(actual)+1: return "INCONCLUSIVE"
            hashes = tuple(map(F.digest,observations))
            changed = len(set(hashes))>1
            row = {"program":actual,"changed":changed,
                   "observed_hashes":hashes,"observations":observations}
            diagnostics.append(row)
            counts = (2,4,8,16) if changed else (2,4)
            additions = [actual*n for n in counts if len(actual)*n<=self.max_depth]
            self.frontier.extendleft(reversed([p for p in additions if p not in self.seen]))
            return "NONTERMINAL_PREFIX"
    return Search


def run(factory, actions, source, report, transfer, evidence, execute_stage, output,
        max_training_actions=1200, max_episodes=64, gate=T.run_lean_gate):
    stages = A.select_archive(report,source,actions)
    entry = verified_entry(source,report,transfer,evidence,actions)
    proposed = component_actions(entry,entry["available_actions"])
    diagnostics = []
    search = continuation_search(stages,proposed,tuple(actions),diagnostics)
    result = M.continue_verified(factory,actions,source,search,observed_stage(execute_stage),output,
        max_training_actions=max_training_actions,max_episodes=max_episodes,
        max_depth=32,budget=120,max_levels=4,gate=gate)
    result.update(diagnostic_rows=diagnostics,archive_run=A.ARCHIVE_RUN,
        transfer_run=TRANSFER_RUN,transfer_kind="verified_archive_then_new_probe",
        proposed_actions=proposed,archived_levels=len(stages),
        new_discoveries=max(0,len(result.get("accepted",()))-len(stages)))
    warm = result.get("warm",{})
    result["improved_over_archive"] = bool(
        warm.get("initial_sha256")==source["initial_sha256"]
        and T.quality(warm)>T.quality(transfer["warm"]))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-evidence",required=True)
    p.add_argument("--archive-evidence",required=True)
    p.add_argument("--transfer-evidence",required=True)
    p.add_argument("--stage-evidence",required=True)
    p.add_argument("--frozen-dir",required=True)
    p.add_argument("--environments-dir",required=True)
    p.add_argument("--game",default="bt33-a7c3f9d18b4e")
    p.add_argument("--output",default="arc3-stage4-probe.json")
    a=p.parse_args()
    _,_,grounding,_,multilevel=T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade,OperationMode
    logger=logging.getLogger("arc3-stage4-probe")
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    def factory():
        arcade=Arcade(operation_mode=OperationMode.OFFLINE,
                      environments_dir=a.environments_dir,logger=logger)
        env=arcade.make(a.game)
        if env is None: raise RuntimeError("Environment unavailable")
        class Adapter:
            @property
            def observation_space(self): return env.observation_space
            @property
            def action_space(self): return env.action_space
            def reset(self): return env.reset()
            def step(self,action):
                kind,data=grounding.decode(action)
                return env.step(kind,data=data)
            def close(self): return arcade.close_scorecard()
        return Adapter()
    first=factory()
    actions,unsupported=grounding.action_catalog(first.action_space,first.observation_space,8,256)
    first.close()
    def read(path): return json.loads(Path(path).read_text())
    transfer_path=Path(a.transfer_evidence)
    if hashlib.sha256(transfer_path.read_bytes()).hexdigest()!=TRANSFER_SHA256:
        raise ValueError("Archive-transfer evidence SHA256 mismatch")
    result=run(factory,actions,read(a.source_evidence),read(a.archive_evidence),
               read(a.transfer_evidence),read(a.stage_evidence),multilevel.execute_stage,
               Path(a.output).parent/"stage4-gate")
    result.update(game=a.game,mode="offline",unsupported_action_ids=unsupported,
                  upstream_commit=T.UPSTREAM,source_blobs=T.SOURCE_BLOBS)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+"\n")
    print("ARC3_STAGE4="+json.dumps({k:result.get(k) for k in
          ("status","training_actions","training_episodes","levels_witnessed",
           "installed_options","new_discoveries","terminal_win")},sort_keys=True))

if __name__=="__main__": main()
