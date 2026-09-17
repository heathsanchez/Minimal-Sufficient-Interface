"""Bounded, defeasible learning from public nonterminal visual consequences.

No game IDs, source inspection, winning colours, direction semantics or supplied
solutions. Effect statistics guide probes; they NEVER certify a no-op, a goal,
a behavioural quotient, or impossibility. Observed routes are replanned after
every live observation. A conflicting successor disqualifies a route edge.
"""
from __future__ import annotations
from collections import OrderedDict, deque
import hashlib
import json
from typing import Any
from .memory_graph import ArcMemoryGraph, ActionKey, _freeze
from .memory_controller import MemoryGraphController
from .runtime import ActionToken, normalize_frame, _field, _plain


class EffectMemory:
    """Finite observational evidence, not universal transition laws."""

    def __init__(self, limit: int = 2048):
        if limit < 1:
            raise ValueError('positive effect-memory bound required')
        self.limit = int(limit)
        self.edges: OrderedDict[tuple[str, ActionKey], dict] = OrderedDict()
        self.descriptors: OrderedDict[str, list[int]] = OrderedDict()
        self.catalogs: OrderedDict[str, tuple[ActionKey, ...]] = OrderedDict()
        self.total_observations = 0

    def record(self, context, action, outcome, descriptor, changed, history, terminal):
        key = (str(context), tuple(action))
        row = self.edges.setdefault(key, dict(n=0, changed=0, outcomes={}, histories=[],
                                               terminal=False, ambiguous=False))
        row['n'] += 1
        row['changed'] += int(changed > 0)
        if outcome not in row['outcomes'] and row['outcomes']:
            row['ambiguous'] = True
        # Retain bounded witnesses and a sticky conflict marker if saturated.
        if outcome in row['outcomes'] or len(row['outcomes']) < 8:
            row['outcomes'][str(outcome)] = row['outcomes'].get(str(outcome), 0) + 1
        witness = [str(history), str(outcome), int(changed)]
        if witness not in row['histories']:
            row['histories'] = (row['histories'] + [witness])[-8:]
        row['terminal'] = row['terminal'] or bool(terminal)
        self.edges.move_to_end(key)
        if len(self.edges) > self.limit:
            self.edges.popitem(last=False)
        stats = self.descriptors.setdefault(str(descriptor), [0, 0])
        stats[0] += 1; stats[1] += int(changed > 0)
        self.descriptors.move_to_end(str(descriptor))
        if len(self.descriptors) > self.limit:
            self.descriptors.popitem(last=False)
        self.total_observations += 1

    def attempts(self, context, action):
        return self.edges.get((context, tuple(action)), {}).get('n', 0)

    def ambiguous(self, context, action):
        return self.edges.get((context, tuple(action)), {}).get('ambiguous', False)

    def rate(self, descriptor):
        n, changed = self.descriptors.get(str(descriptor), (0, 0))
        # A smoothed ranking heuristic, NOT a calibrated causal probability.
        return (changed + 1) / (n + 2)

    def descriptor_attempts(self, descriptor):
        return self.descriptors.get(str(descriptor), (0, 0))[0]

    def note_catalog(self, context, actions):
        self.catalogs[str(context)] = tuple(tuple(a) for a in actions)
        self.catalogs.move_to_end(str(context))
        if len(self.catalogs) > min(self.limit, 512):
            self.catalogs.popitem(last=False)

    def successors(self, context):
        out = []
        for (source, action), row in self.edges.items():
            if source != context or row['terminal'] or row['ambiguous']:
                continue
            if len(row['outcomes']) == 1:
                target = next(iter(row['outcomes']))
                if target != source:
                    out.append((action, target))
        return sorted(out, key=repr)

    def frontier_action(self, context):
        """First step of a short observed route; recompute on the next frame."""
        queue = deque([(context, None)])
        seen = {context}
        while queue and len(seen) <= 128:
            state, first = queue.popleft()
            catalog = self.catalogs.get(state, ())
            if first is not None and any(self.attempts(state, a) == 0 for a in catalog):
                return first
            for action, target in self.successors(state):
                if target not in seen:
                    seen.add(target)
                    queue.append((target, action if first is None else first))
        return None

    def payload(self):
        return dict(limit=self.limit, total_observations=self.total_observations,
                    edges=[[s, list(a), row] for (s, a), row in self.edges.items()],
                    descriptors=list(self.descriptors.items()),
                    catalogs=[[s, [list(a) for a in actions]] for s, actions in self.catalogs.items()])

    @classmethod
    def from_payload(cls, data):
        out = cls(int(data['limit']))
        if len(data['edges']) > out.limit or len(data['descriptors']) > out.limit:
            raise ValueError('effect snapshot exceeds its bound')
        if len(data['catalogs']) > min(out.limit, 512):
            raise ValueError('context snapshot exceeds its bound')
        out.edges = OrderedDict(((str(s), tuple(a)), row) for s, a, row in data['edges'])
        out.descriptors = OrderedDict((str(d), list(v)) for d, v in data['descriptors'])
        out.catalogs = OrderedDict((str(s), tuple(tuple(a) for a in actions)) for s, actions in data['catalogs'])
        out.total_observations = int(data['total_observations'])
        return out


def settled_grid(frame):
    frames = _plain(_field(frame, 'frame', []))
    grid = frames[-1] if frames else []
    if not grid:
        return ()
    width = len(grid[0])
    if not width or len(grid) > 128 or width > 128 or any(len(row) != width for row in grid):
        raise ValueError('unsupported public raster dimensions')
    return tuple(tuple(int(x) for x in row) for row in grid)


def visual_components(grid):
    """Mechanical same-value regions. Representatives are actual member pixels."""
    if not grid:
        return [], {}
    height, width = len(grid), len(grid[0])
    visited = set(); regions = []; attributes = {}
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            value = grid[y][x]; stack = [(x, y)]; visited.add((x, y)); cells = []
            while stack:
                px, py = stack.pop(); cells.append((px, py))
                for nx, ny in ((px-1,py),(px+1,py),(px,py-1),(px,py+1)):
                    if 0 <= nx < width and 0 <= ny < height and (nx,ny) not in visited and grid[ny][nx] == value:
                        visited.add((nx,ny)); stack.append((nx,ny))
            n=len(cells); sx=sum(p[0] for p in cells); sy=sum(p[1] for p in cells)
            representative=min(cells,key=lambda p: ((p[0]*n-sx)**2+(p[1]*n-sy)**2,p[1],p[0]))
            bw=max(p[0] for p in cells)-min(p[0] for p in cells)+1
            bh=max(p[1] for p in cells)-min(p[1] for p in cells)+1
            shape=(n,bw,bh)
            for p in cells: attributes[p]=shape
            regions.append((n,representative))
    # Deprioritising the largest region is a proposal bias, not a no-op rule.
    largest=max(n for n,_ in regions)
    regions.sort(key=lambda r: (r[0]==largest, r[1][1], r[1][0]))
    return [point for _,point in regions], attributes


class ConsequenceController(MemoryGraphController):
    """Same retention/refutation core with a reward-independent probe selector."""

    def __init__(self, *args, consequence_enabled=True, visual_grounding=True,
                 effect_limit=2048, **kwargs):
        self.consequence_enabled = bool(consequence_enabled)
        self.visual_grounding = bool(visual_grounding)
        self.effects = EffectMemory(effect_limit)
        self._decision_tick = 0
        self._probe_serial = 0
        super().__init__(*args, **kwargs)

    def reset_episode(self):
        super().reset_episode()
        self._pending_effect = None
        self._grid = ()
        self._shape_attributes = {}
        self._primary = ()
        self._repeat = None
        self._repeat_left = 0
        self._raster_cache = None

    def _descriptor(self, action):
        if action.action_id != 6 or not self._grid:
            return 'primitive:' + str(action.action_id)
        x,y=action.x,action.y; h,w=len(self._grid),len(self._grid[0])
        values={}; pattern=[]
        for ny in range(y-1,y+2):
            for nx in range(x-1,x+2):
                if not (0 <= nx < w and 0 <= ny < h):
                    pattern.append(-1)
                else:
                    value=self._grid[ny][nx]
                    if value not in values: values[value]=len(values)
                    pattern.append(values[value])
        shape=self._shape_attributes.get((x,y),())
        return repr((6,shape,tuple(pattern)))

    def _catalog(self, obs):
        base=super()._action_catalog(obs)
        if not self.visual_grounding or 6 not in self._legal_ids(obs) or not self._grid:
            self._primary=base
            self._shape_attributes={}
            return base
        if self._raster_cache is None or self._raster_cache[0] != self._grid:
            points, attributes=visual_components(self._grid)
            self._raster_cache=(self._grid,points,attributes)
        _,points,self._shape_attributes=self._raster_cache
        primary=[a for a in base if a.action_id != 6]
        primary += [ActionToken(6,x,y,'consequence') for x,y in points[:64]]
        seen=set(); catalog=[]
        for a in primary+list(base):
            key=self._action_key(a)
            if key not in seen:
                seen.add(key);catalog.append(a)
            if len(catalog) >= self.max_grounded_actions:break
        self._primary=tuple(a for a in catalog[:len(primary)])
        return tuple(catalog)

    def _record_effect(self, frame, obs):
        grid=settled_grid(frame)
        if self._pending_effect is not None:
            context, action, before, descriptor, history = self._pending_effect
            if len(before)==len(grid) and (not grid or len(before[0])==len(grid[0])):
                changed=sum(a!=b for ra,rb in zip(before,grid) for a,b in zip(ra,rb))
            else:
                changed=max(sum(map(len,before)),sum(map(len,grid)))
            self.effects.record(context,action,obs.evidence_sha256,descriptor,changed,history,
                                obs.state in ('WIN','GAME_OVER'))
            self._pending_effect=None
        self._grid=grid

    def observe_terminal(self, frame):
        """Consume the final consequence even when no next action is requested."""
        obs=normalize_frame(frame)
        self._record_effect(frame,obs)
        self._process_previous_outcome(obs)
        self._previous=obs;self._last_action=None

    def _select_probe(self, obs, catalog):
        context=obs.evidence_sha256
        allowed_keys={self._action_key(a) for a in catalog}
        primary=tuple(a for a in self._primary if self._action_key(a) in allowed_keys) or catalog
        self.effects.note_catalog(context,[self._action_key(a) for a in primary])
        if not self.consequence_enabled:
            guard=self._exploration_guard(obs)
            return min(catalog,key=lambda a:self._visits.get((guard,self._action_key(a)),0))
        if self._repeat is not None and self._repeat_left and self._repeat in allowed_keys:
            self._repeat_left-=1
            return self._token(self._repeat,'consequence_delayed_probe')
        self._repeat=None;self._repeat_left=0
        # Sparse duration experiments retain the possibility of hidden/delayed
        # effects. They are proposals, never evidence that preceding no-ops fail.
        if self._decision_tick % 16 == 8:
            index=self._probe_serial
            token=primary[index % len(primary)]
            length=2 ** (1 + (index // len(primary)) % 3)
            self._probe_serial+=1
            self._repeat=self._action_key(token);self._repeat_left=length-1
            return self._token(self._repeat,'consequence_delayed_probe')
        # Fair probes stop a visually changing distraction monopolising actions.
        if self._decision_tick % 8 == 0:
            token=min(catalog,key=lambda a:(
                self.effects.descriptor_attempts(self._descriptor(a)),
                self.effects.attempts(context,self._action_key(a))))
            return self._token(self._action_key(token),'consequence_fair_probe')
        if all(self.effects.attempts(context,self._action_key(a)) for a in primary):
            first=self.effects.frontier_action(context)
            if first in allowed_keys:
                return self._token(first,'consequence_frontier')
        # Context-specific observations dominate transferred appearance priors.
        # A negative outcome score lowers rank; it does not remove an action.
        token=max(primary,key=lambda a:(
            self.effects.rate(self._descriptor(a)) /
                (1+self.effects.attempts(context,self._action_key(a))),
            -self.effects.descriptor_attempts(self._descriptor(a))))
        return self._token(self._action_key(token),'consequence')

    def observe_and_choose(self, frame):
        obs=normalize_frame(frame)
        self._record_effect(frame,obs)
        previous_level=self._previous.levels_completed if self._previous is not None else None
        self._process_previous_outcome(obs)
        if previous_level is not None and obs.levels_completed > previous_level:
            self._repeat=None;self._repeat_left=0
        if self._episode_context is None:self._episode_context=self._memory_context(obs)
        if self._level_start_guard is None:self._level_start_guard=self._retention_guard(obs)
        if obs.state=='WIN':
            self._previous=obs;self._last_action=None
            return None
        token=self._next_archive(obs)
        if token is None:token=self._next_continuation(obs)
        if token is None:token=self._next_retained(obs)
        self._decision_tick+=1
        if token is None or token.source=='transfer':
            catalog=self._catalog(obs)
            prefix=tuple(self._episode_program)
            self.memory.note_legal(self._episode_context,prefix,[self._action_key(a) for a in catalog])
            forbidden=self.memory.forbidden_next(self._episode_context,prefix)
            allowed=tuple(a for a in catalog if self._action_key(a) not in forbidden)
            # Existing trie closes only this bounded action catalog; never emit
            # a claim of whole-game impossibility when its options are exhausted.
            candidates=allowed or catalog
            if token is None or self._action_key(token) in forbidden:
                self._clear_transfer()
                token=self._select_probe(obs,candidates)
            key=self._action_key(token)
            guard=self._exploration_guard(obs)
            self._visits[(guard,key)]=self._visits.get((guard,key),0)+1
            self.memory.note_attempt(self._memory_context(obs),key)
        key=self._action_key(token)
        history=hashlib.sha256(repr(tuple(self._episode_program[-8:])).encode()).hexdigest()
        self._pending_effect=(obs.evidence_sha256,key,self._grid,self._descriptor(token),history)
        self._episode_program.append(key)
        self._previous=obs;self._last_action=token
        return token

    def snapshot_memory(self):
        """Persistent present only. Restore starts a fresh episode, not a world clone."""
        data=dict(version='MG-ARC-CONSEQUENCES1', memory=self.memory.text(),
                  effects=self.effects.payload(), tick=self._decision_tick, probe=self._probe_serial,
                  settings=[list(self.action_ids),self.consequence_enabled,self.visual_grounding],
                  retained=[[k,[[list(self._action_key(a)) for a in p] for p in programs]]
                            for k,programs in sorted(self._retained.items(),key=repr)],
                  visits=[[k,v] for k,v in sorted(self._visits.items(),key=repr)])
        return json.dumps(data,sort_keys=True,separators=(',',':'))

    def restore_memory(self,text):
        data=json.loads(text)
        if data['version']!='MG-ARC-CONSEQUENCES1' or data['settings'] != [list(self.action_ids),self.consequence_enabled,self.visual_grounding]:
            raise ValueError('incompatible consequence snapshot')
        self.memory=ArcMemoryGraph.parse(data['memory'])
        self.effects=EffectMemory.from_payload(data['effects'])
        self._decision_tick=int(data['tick']);self._probe_serial=int(data['probe'])
        self._retained={_freeze(k):[tuple(self._token(tuple(a),'retained') for a in p) for p in programs]
                        for k,programs in data['retained']}
        self._visits={_freeze(k):int(v) for k,v in data['visits']}
        self.reset_episode()
