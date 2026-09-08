"""Observation-only, bounded motion-model discovery and graph exploration.

No game-specific colours, directions, object labels, source code, or goals are
supplied. A rigid moving component is inferred from public frame differences.
Nonzero action effects become provisional operators. Failed predictions are
retained as local counterexamples, not promoted to universal impossibilities.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from hashlib import sha256
import json
import numpy as np


def pixels(frame):
    layers = frame.frame
    if not layers:
        raise ValueError('No visual observation')
    return np.asarray(layers[0], dtype=np.int16)


def components(a, color):
    mask = a == color
    seen = np.zeros(mask.shape, dtype=bool)
    out = []
    for y, x in np.argwhere(mask):
        if seen[y, x]:
            continue
        seen[y, x] = True
        todo = [(int(y), int(x))]
        pts = []
        while todo:
            cy, cx = todo.pop()
            pts.append((cy, cx))
            for ny, nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx] = True
                    todo.append((ny,nx))
        top = min(p[0] for p in pts); left = min(p[1] for p in pts)
        shape = tuple(sorted((y-top,x-left) for y,x in pts))
        out.append(((top,left),shape))
    return out


def moving_components(before, after, max_area=128, max_motion=16):
    """Find translated same-colour shapes; discard components that stayed put."""
    if before.shape != after.shape:
        return []
    found = []
    for color in sorted(set(np.unique(before)) | set(np.unique(after))):
        old = components(before,color)
        new = components(after,color)
        oldset = set(old); newset = set(new)
        for p,shape in old:
            if (p,shape) in newset or not 4 <= len(shape) <= max_area:
                continue
            for q,other in new:
                if shape != other or (q,other) in oldset:
                    continue
                delta = (q[0]-p[0],q[1]-p[1])
                if 0 < max(map(abs,delta)) <= max_motion:
                    found.append((len(shape),int(color),shape,p,q,delta))
    return sorted(found,key=lambda c:(-c[0],c[1],c[3],c[4]))


@dataclass
class MotionModel:
    actions: tuple
    color: int | None = None
    shape: tuple = ()
    position: tuple | None = None
    vectors: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    blocked: set = field(default_factory=set)
    visited: set = field(default_factory=set)
    evidence: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    revisions: int = 0
    dimensions: tuple = (64,64)

    def locate(self, a, preferred=None):
        if self.color is None:
            return None
        matches = [p for p,s in components(a,self.color) if s == self.shape]
        if not matches:
            return None
        if preferred is None:
            return min(matches)
        return min(matches,key=lambda p:(abs(p[0]-preferred[0])+abs(p[1]-preferred[1]),p))

    def observe(self, before, action, after):
        a,b = pixels(before),pixels(after)
        self.dimensions = a.shape
        if self.color is None:
            found = moving_components(a,b)
            if not found:
                return False
            _,self.color,self.shape,p,q,delta = found[0]
        else:
            p = self.locate(a,self.position)
            q = self.locate(b,p)
            if p is None or q is None:
                self.conflicts.append(('lost_tracker',action))
                return False
            delta = (q[0]-p[0],q[1]-p[1])
        self.position = q
        self.visited.update((p,q))
        key = (p,action)
        old = self.edges.get(key)
        if old is not None and old != q:
            self.conflicts.append(('transition',key,old,q))
            self.revisions += 1
        self.edges[key] = q
        if p == q:
            self.blocked.add(key)
        else:
            self.blocked.discard(key)
            known = self.vectors.setdefault(action,set())
            known.add(delta)
            if len(known) > 1:
                self.conflicts.append(('nonuniform_effect',action,tuple(sorted(known))))
        self.evidence.append((p,action,q))
        return True

    def vector(self, action):
        vals = self.vectors.get(action,set())
        return next(iter(vals)) if len(vals)==1 else None

    def predict(self, pos, action):
        key = (pos,action)
        if key in self.edges:
            return self.edges[key]
        v = self.vector(action)
        if v is None:
            return None
        p = (pos[0]+v[0],pos[1]+v[1])
        if not (0 <= p[0] < self.dimensions[0] and 0 <= p[1] < self.dimensions[1]):
            return None
        return p

    def choose(self):
        if self.position is None:
            return self.actions[0]
        # Search learned transitions and one-step predictions for a new position.
        # Every proposed edge remains provisional until tested in the environment.
        start = self.position
        queue = deque([(start,())]); seen={start}
        while queue:
            pos,path = queue.popleft()
            for action in self.actions:
                if (pos,action) in self.blocked:
                    continue
                nxt = self.predict(pos,action)
                if nxt is None:
                    if pos == start:
                        return action
                    continue
                if nxt == pos:
                    continue
                candidate = path+(action,)
                if nxt not in self.visited:
                    return candidate[0]
                if nxt not in seen and len(candidate)<64:
                    seen.add(nxt);queue.append((nxt,candidate))
        # Finite exhaustion is not a universal impossibility theorem.
        for action in self.actions:
            if (start,action) not in self.edges:
                return action
        return self.actions[0]

    def snapshot(self):
        return {'tracked_color':self.color,'tracked_area':len(self.shape),
                'position':self.position,'vectors':{str(k):sorted(v) for k,v in self.vectors.items()},
                'observed_edges':len(self.edges),'visited_positions':len(self.visited),
                'conflicts':self.conflicts,'revisions':self.revisions,
                'evidence_sha256':sha256(json.dumps(self.evidence).encode()).hexdigest()}


def run_model_episode(env, actions, max_actions=300, model=None):
    model = model or MotionModel(tuple(actions))
    frame=env.observation_space
    if frame is None:
        frame=env.reset()
    count=0;levels=[]
    while count<max_actions:
        state=getattr(frame.state,'name',str(frame.state))
        if state=='WIN':break
        if state=='GAME_OVER':break
        action=model.choose() if model.position is not None else actions[count%len(actions)]
        after=env.step(action)
        if after is None:raise RuntimeError('Missing observation')
        model.observe(frame,action,after)
        if int(after.levels_completed)>int(frame.levels_completed):
            levels.append(count+1)
            model.position=None
            model.color=None
            model.shape=()
            model.edges.clear();model.blocked.clear();model.visited.clear()
        frame=after;count+=1
    return {'actions':count,'levels_completed':int(frame.levels_completed),
            'state':getattr(frame.state,'name',str(frame.state)),
            'level_actions':levels,'model_calls':0,**model.snapshot()}
