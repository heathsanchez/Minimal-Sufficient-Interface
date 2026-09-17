"""Intervention-gated finite configuration proposals over repeated visual cells.

This is a hypothesis generator, not a supplied game solver or a certified state
quotient. It infers editable cohorts from actual pixel changes. Reference copies,
Boolean combinations, then Gray-code configurations are proposed; only external
level progress verifies a solution. Timers and hidden state are NOT assumed away.
"""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import replace
import hashlib,json
from .consequence_controller import ConsequenceController, visual_components, settled_grid
from .memory_graph import _freeze
from .runtime import ActionToken, OnlineController, normalize_frame


def repeated_cohort(grid, controls):
    if not grid or not controls:return None
    points,attrs=visual_components(grid)
    shapes={attrs[p] for p in points if attrs[p][0]>=4 and attrs[p][0]==attrs[p][1]*attrs[p][2]}
    for shape in sorted(shapes,key=lambda s: -s[0]*sum(attrs[p]==s for p in points)):
        ps=[p for p in points if attrs[p]==shape]
        if len(ps)<4:continue
        gaps=[abs(a[0]-b[0])+abs(a[1]-b[1]) for i,a in enumerate(ps) for b in ps[i+1:]
              if a[0]==b[0] or a[1]==b[1]]
        if not gaps:continue
        step=min(gaps);unseen=set(ps);groups=[]
        while unseen:
            root=min(unseen);unseen.remove(root);stack=[root];group=[]
            while stack:
                p=stack.pop();group.append(p)
                for q in ((p[0]-step,p[1]),(p[0]+step,p[1]),(p[0],p[1]-step),(p[0],p[1]+step)):
                    if q in unseen:unseen.remove(q);stack.append(q)
            if 2<=len(group)<=10:groups.append(tuple(sorted(group,key=lambda p:(p[1],p[0]))))
        if not groups:continue
        def supported(group):
            return sum(any(abs(x-px)<=shape[1]/2 and abs(y-py)<=shape[2]/2
                           for px,py in group) for x,y in controls)
        active=max(groups,key=supported)
        if not supported(active):continue
        def layout(group):
            x=min(p[0] for p in group);y=min(p[1] for p in group)
            return tuple((px-x,py-y) for px,py in group)
        layout_key=layout(active)
        refs=[g for g in groups if g!=active and layout(g)==layout_key]
        values=tuple(grid[y][x] for x,y in active)
        references=[tuple(grid[y][x] for x,y in g) for g in sorted(refs,key=repr)]
        colours=tuple(sorted({v for r in references+[values] for v in r}))
        if len(colours)!=2:continue
        return active,values,references,colours
    return None


class PatternController(ConsequenceController):
    """Keep the old core; prefer current visual constraints over raw macro replay."""

    def __init__(self,*args,pattern_search=True,**kwargs):
        self.pattern_search=bool(pattern_search)
        self._coverage=OrderedDict()
        self._controls=OrderedDict()
        self._pattern_sessions=OrderedDict()
        self._last_pattern_attempt=None
        self._pattern_stalls=0
        super().__init__(*args,**kwargs)

    def reset_episode(self):
        super().reset_episode()
        self._last_pattern_attempt=None
        self._pattern_stalls=0

    @staticmethod
    def _settled_context(obs,grid):
        data=(obs.levels_completed,obs.state,obs.available_actions,grid)
        return hashlib.sha256(repr(data).encode()).hexdigest()

    def _record_effect(self,frame,obs):
        grid=settled_grid(frame)
        if self._pending_effect is not None:
            _,action,before,_,_=self._pending_effect
            aid,x,y=action
            if (aid==6 and before and grid and x is not None and y is not None
                and 0<=y<min(len(before),len(grid)) and 0<=x<min(len(before[y]),len(grid[y]))
                and before[y][x]!=grid[y][x] and self._previous is not None
                and self._previous.levels_completed==obs.levels_completed
                and obs.state=='NOT_FINISHED'):
                self._controls[(obs.levels_completed,x,y)]=True
                if len(self._controls)>2048:self._controls.popitem(last=False)
        settled=replace(obs,evidence_sha256=self._settled_context(obs,grid))
        super()._record_effect(frame,settled)

    def _select_probe(self,obs,catalog):
        settled=replace(obs,evidence_sha256=self._settled_context(obs,self._grid))
        if self.consequence_enabled and self.visual_grounding:
            available={self._action_key(a) for a in catalog}
            # Sampling a new location outranks inherited no-op appearance priors.
            for a in self._primary:
                k=self._action_key(a)
                if a.action_id==6 and k in available and not self._coverage.get((obs.levels_completed,k),0):
                    return self._token(k,'consequence_new_location')
        return super()._select_probe(settled,catalog)

    def _pattern_probe(self,obs):
        if not (self.pattern_search and self.consequence_enabled and self.visual_grounding and 6 in self._legal_ids(obs)):
            return None
        controls=[(x,y) for (level,x,y) in self._controls if level==obs.levels_completed]
        found=repeated_cohort(self._grid,controls)
        if found is None:return None
        points,values,refs,colours=found
        key=repr((obs.levels_completed,points,refs,colours))
        session=self._pattern_sessions.setdefault(key,dict(target=None,seen=[],gray=0,origin=list(values)))
        self._pattern_sessions.move_to_end(key)
        if len(self._pattern_sessions)>64:self._pattern_sessions.popitem(last=False)
        # This means "observed without immediate level progress", NOT refuted
        # for all histories, phases or delayed effects.
        if list(values) not in session['seen']:session['seen'].append(list(values))
        target=session['target']
        if target is None or tuple(target)==values:
            proposals=list(refs)
            bits=[[int(v==colours[1]) for v in row] for row in refs]
            if bits:
                proposals += [tuple(colours[sum(row[i] for row in bits)%2] for i in range(len(points))),
                              tuple(colours[int(all(row[i] for row in bits))] for i in range(len(points))),
                              tuple(colours[int(any(row[i] for row in bits))] for i in range(len(points)))]
            target=next((list(p) for p in proposals if list(p) not in session['seen']),None)
            while target is None and session['gray'] < (1<<len(points)):
                i=session['gray'];session['gray']+=1;g=i^(i>>1)
                proposal=[colours[int(v==colours[1])^((g>>j)&1)] for j,v in enumerate(session['origin'])]
                if proposal not in session['seen']:target=proposal
            session['target']=target
        if target is None:return None
        if self._last_pattern_attempt is not None:
            last_key,last_values=self._last_pattern_attempt
            self._pattern_stalls=self._pattern_stalls+1 if last_key==key and last_values==values else 0
        if self._pattern_stalls>=2:
            self._pattern_stalls=0;self._last_pattern_attempt=None
            return None
        for i,(x,y) in enumerate(points):
            if values[i]!=target[i]:
                action=(6,x,y)
                if action in self.memory.forbidden_next(self._episode_context,tuple(self._episode_program)):
                    return None
                self._last_pattern_attempt=(key,values)
                return ActionToken(6,x,y,'visual_configuration_hypothesis')
        return None

    def _next_retained(self,obs):
        exact=OnlineController._next_retained(self,obs)
        if exact is not None:return exact
        proposed=self._pattern_probe(obs)
        if proposed is not None:
            self._clear_transfer()
            return proposed
        return self._next_transfer(obs)

    def observe_and_choose(self,frame):
        obs=normalize_frame(frame)
        token=super().observe_and_choose(frame)
        if token is not None:
            k=self._action_key(token);key=(obs.levels_completed,k)
            self._coverage[key]=self._coverage.get(key,0)+1
            if len(self._coverage)>2048:self._coverage.popitem(last=False)
            if token.source=='visual_configuration_hypothesis':
                self.memory.note_attempt(self._memory_context(obs),k)
            old=self._pending_effect
            # Preserve raw animation/history provenance while using a defeasible
            # settled-image search key. Conflicting successors remain separate.
            history=hashlib.sha256((old[4]+obs.evidence_sha256).encode()).hexdigest()
            self._pending_effect=(self._settled_context(obs,self._grid),old[1],old[2],old[3],history)
        return token

    def snapshot_memory(self):
        return json.dumps(dict(version='MG-ARC-PATTERN1',base=super().snapshot_memory(),
            pattern_search=self.pattern_search,coverage=list(self._coverage.items()),
            controls=list(self._controls.items()),sessions=list(self._pattern_sessions.items())),sort_keys=True,separators=(',',':'))

    def restore_memory(self,text):
        data=json.loads(text)
        if data['version']!='MG-ARC-PATTERN1' or data['pattern_search']!=self.pattern_search:
            raise ValueError('incompatible pattern snapshot')
        if len(data['coverage'])>2048 or len(data['controls'])>2048 or len(data['sessions'])>64:
            raise ValueError('pattern memory exceeds bound')
        super().restore_memory(data['base'])
        self._coverage=OrderedDict((_freeze(k),int(v)) for k,v in data['coverage'])
        self._controls=OrderedDict((_freeze(k),bool(v)) for k,v in data['controls'])
        self._pattern_sessions=OrderedDict(data['sessions'])
