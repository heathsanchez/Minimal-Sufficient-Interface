"""Compile observed successful trajectories into guarded, reusable action macros.

Shortest paths are relative to the witnessed position graph, not universal
proofs. Replay validates every predicted position and revokes failed macros.
The full evidence is retained separately from the active executable interface.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from hashlib import sha256
import json
from world_model import MotionModel, pixels

@dataclass(frozen=True)
class Macro:
    start: tuple
    color: int
    shape: tuple
    actions: tuple
    expected: tuple
    identity: str

@dataclass
class DevelopmentalModel(MotionModel):
    macros: list = field(default_factory=list)
    macro_replays: int = 0
    macro_failures: int = 0

    def snapshot(self):
        return {**super().snapshot(), 'macro_count':len(self.macros),
                'macro_replays':self.macro_replays,'macro_failures':self.macro_failures}


def compile_macro(model, events):
    """Compile a shortest path in the witnessed graph, not the whole search.

    This is minimal only relative to the observed position graph. Contextual
    effects may invalidate the quotient; replay checks and revokes that case.
    """
    first = next((i for i,e in enumerate(events) if e is not None),None)
    if first is None or any(e is None for e in events[first:]):
        return None
    trace = events[first:]
    start = trace[0][0]
    terminal = trace[-1]
    graph = {}
    deterministic = True
    for p,a,q in trace[:-1]:
        edges = graph.setdefault(p,{})
        if a in edges and edges[a]!=q:
            deterministic=False
        edges[a]=q
    path = None
    if deterministic:
        queue=deque([(start,(),())]);seen={start}
        while queue:
            p,actions,expected=queue.popleft()
            if p==terminal[0]:
                path=(actions+(terminal[1],),expected+(None,))
                break
            for action,q in sorted(graph.get(p,{}).items()):
                if q not in seen:
                    seen.add(q)
                    queue.append((q,actions+(action,),expected+(q,)))
    if path is None:
        path=(tuple(e[1] for e in trace),tuple(e[2] for e in trace[:-1])+(None,))
    actions,expected=path
    payload = (start,model.color,model.shape,actions,expected)
    return Macro(start,model.color,model.shape,actions,expected,
                 sha256(json.dumps(payload).encode()).hexdigest())


def run_developmental_episode(env, actions, max_actions=300, model=None, retain_operators=True):
    model = model or DevelopmentalModel(tuple(actions))
    frame=env.observation_space
    if frame is None:
        frame=env.reset()
    count=0;levels=[];events=[];replay=None;replay_index=0
    while count<max_actions:
        state=getattr(frame.state,'name',str(frame.state))
        if state in ('WIN','GAME_OVER'):break
        if replay is not None:
            action=replay.actions[replay_index]
        else:
            action=model.choose() if model.position is not None else actions[count%len(actions)]
        after=env.step(action)
        if after is None:raise RuntimeError('Missing observation')
        observed=model.observe(frame,action,after)
        events.append(model.evidence[-1] if observed else None)
        advanced=int(after.levels_completed)>int(frame.levels_completed)
        count+=1
        if replay is not None:
            expected=replay.expected[replay_index]
            replay_index+=1
            if not advanced and (not observed or (expected is not None and model.position!=expected)
                                 or replay_index==len(replay.actions)):
                model.macro_failures+=1
                replay=None
        if advanced:
            levels.append(count)
            cap=compile_macro(model,events) if observed else None
            if retain_operators and cap is not None and all(c.identity!=cap.identity for c in model.macros):
                model.macros.append(cap)
            events=[];replay=None;replay_index=0
            # Preserve learned operators, not unverified level-specific edges.
            model.edges.clear();model.blocked.clear();model.visited.clear()
            if not retain_operators:
                model.vectors.clear();model.macros.clear()
            # A retained visual template may locate the actor immediately in
            # the next level. A changed shape is a new representation boundary.
            pos=model.locate(pixels(after)) if model.color is not None else None
            if pos is None:
                model.position=None;model.color=None;model.shape=()
            else:
                model.position=pos
                model.visited.add(pos)
                if retain_operators:
                    for candidate in reversed(model.macros):
                        if candidate.start==pos and candidate.color==model.color and candidate.shape==model.shape:
                            replay=candidate
                            model.macro_replays+=1
                            break
        frame=after
    return {'actions':count,'levels_completed':int(frame.levels_completed),
            'state':getattr(frame.state,'name',str(frame.state)),
            'level_actions':levels,'model_calls':0,**model.snapshot()}
