"""ARC observation adapter for the existing finite consequential-refinement kernel.

No player, movement, goal, timer, or game-specific action semantics are supplied.
The only protected objective is the public progress/terminal consequence. The
source grammar is a bounded, generic grammar over public arrays and histories.
The controller is an experimental baseline, not an ARC-3 competition solver.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict, deque
from itertools import combinations
from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'convergence'))
from finite_consequence import Candidate, freeze, digest, synthesize, replay, conflict_count


def observation(frame):
    if isinstance(frame, dict):
        return {k: frame[k] for k in ('frame','levels_completed','state','available_actions') if k in frame}
    state = getattr(frame.state, 'name', str(frame.state))
    return {'frame': [x.tolist() if hasattr(x,'tolist') else x for x in frame.frame],
            'levels_completed': int(frame.levels_completed), 'state': state,
            'available_actions': list(getattr(frame,'available_actions',[]))}


def terminal(obs):
    return obs['state'] in ('WIN','GAME_OVER')


def consequence(before, after):
    return (after['levels_completed'] - before['levels_completed'], after['state'])


@dataclass(frozen=True)
class Transition:
    source: dict
    history: tuple
    action: object
    target: dict
    outcome: tuple


def cell(source, layer, y, x):
    try: return source['frame'][layer][y][x]
    except (KeyError, IndexError, TypeError): return None


def count_value(source, layer, value):
    try: return sum(x == value for line in source['frame'][layer] for x in line)
    except (KeyError, IndexError, TypeError): return None

class SensorGrammar:
    """A frozen, target-neutral feature grammar; no semantic object labels."""
    def __init__(self, history_bound=4, feature_bound=64):
        self.history_bound = history_bound
        self.feature_bound = feature_bound

    def candidates(self, rows, q=None, f=None):
        if not rows: return ()
        out = []
        def add(name, rank, fn): out.append(Candidate(name,rank,fn))
        for key in ('levels_completed','state','available_actions'):
            if key in rows[0].source:
                add('field:'+key,1,lambda r,k=key: r.source.get(k))
        for k in range(1,self.history_bound+1):
            add('history:'+str(k),k+1,lambda r,k=k: r.history[-k:])
        arrays = rows[0].source.get('frame',[])
        # Generic count / coordinate constructors; palette values are observed,
        # not supplied as names for game entities.
        for layer, a in enumerate(arrays):
            values = sorted({int(v) for r in rows for image in r.source.get('frame',[])[layer:layer+1]
                             for line in image for v in line})
            for value in values:
                add(f'count:{layer}:{value}',2,lambda r,l=layer,v=value:count_value(r.source,l,v))
            for y,line in enumerate(a):
                for x,_ in enumerate(line):
                    add(f'cell:{layer}:{y}:{x}',3,lambda r,l=layer,y=y,x=x:cell(r.source,l,y,x))
        add('full_observation',100,lambda r: r.source)
        # Rank all generated primitives by their actual ability to separate
        # the protected residual, not by a manually chosen game object.
        if q is None:q=lambda r:(r.action,)
        if f is None:f=lambda r:r.outcome
        before=conflict_count(rows,q,f)
        useful=[]
        for c in out:
            after=conflict_count(rows,lambda r,c=c:(q(r),freeze(c.evaluate(r))),f)
            if after<before:
                useful.append((after,c.rank,c.name,c))
        useful.sort(key=lambda x:x[:3])
        # Keep a bounded candidate version space, including coarse primitives.
        # Full observation is a last-resort realization, never proof of transfer.
        chosen=[x[3] for x in useful[:self.feature_bound]]
        full=next((x[3] for x in useful if x[2]=='full_observation'),None)
        if full is not None and full not in chosen:chosen.append(full)
        return tuple(chosen)


@dataclass
class Development:
    actions: tuple
    grammar: SensorGrammar = field(default_factory=SensorGrammar)
    records: list = field(default_factory=list)
    evidence_archive: list = field(default_factory=list)
    features: tuple = ()
    repair_log: list = field(default_factory=list)
    version: int = 0
    evidence_limit: int = 512
    repair_interval: int = 16
    history: tuple = ()
    global_history: tuple = ()
    policy_history: tuple = ()
    policy_records: list = field(default_factory=list)
    policy_features: tuple = ()
    policy_repairs: list = field(default_factory=list)
    visits: dict = field(default_factory=dict)
    active_script: tuple = ()
    scripts: list = field(default_factory=list)
    approved_scripts: dict = field(default_factory=dict)
    qualification_log: list = field(default_factory=list)
    allow_provisional: bool = False
    script_trials: set = field(default_factory=set)
    active_trial: tuple | None = None
    trial_source: object = None
    trial_history: tuple = ()
    level_start: object = None
    retain_scripts: bool = True
    max_script_length: int = 128
    script_attempts: int = 0
    script_successes: int = 0
    last_progress: int = 0
    since_progress: tuple = ()
    model_calls: int = 0

    def begin_episode(self):
        """Retain acquired capabilities, separate the new task's live evidence."""
        if self.records:
            self.evidence_archive.extend(self.records)
        self.records=[];self.history=();self.global_history=();self.policy_history=()
        self.visits.clear();self.active_script=();self.active_trial=None
        self.trial_source=None;self.trial_history=();self.level_start=None
        self.since_progress=();self.script_trials.clear()

    def base(self,r):
        return (r.action,)

    def state(self,obs,history):
        r=Transition(obs,history,-1,obs,(0,obs['state']))
        return tuple(freeze(c.evaluate(r)) for c in self.features)

    def _key(self,r):
        return (self.base(r),)+tuple(freeze(c.evaluate(r)) for c in self.features)

    def refresh(self):
        rows=self.records[-self.evidence_limit:]
        if not rows:return None
        q=self.base;f=lambda r:r.outcome
        before=conflict_count(rows,self._key,f)
        if not before:return None
        # The obligation is fixed by the verifier; the feature is not.
        existing={c.name for c in self.features}
        candidates=tuple(c for c in self.grammar.candidates(rows,self._key,f) if c.name not in existing)
        old=self.features
        repair=synthesize(rows,self._key,f,candidates,max_features=2,max_combinations=5000)
        if repair.status=='FINITE_ADEQUATE':
            self.features=old+repair.features
            self.version+=1
            assert replay(rows,self.base,f, type('R',(),{'features':self.features})())==0
        self.repair_log.append({'before':before,'after':repair.after,'status':repair.status,
            'features':[c.name for c in repair.features],'witness':repair.witness,
            'evidence_sha256':repair.evidence_sha256,'candidate_count':repair.candidate_count,
            'evaluated_combinations':repair.evaluated_combinations,'version':self.version})
        return repair

    def observe(self,before,action,after):
        b=observation(before);a=observation(after)
        r=Transition(b,self.history,action,a,consequence(b,a))
        self.records.append(r)
        self.history+=(action,)
        self.global_history+=(action,)
        self.since_progress+=(action,)
        if self.active_trial is not None:
            self.active_trial=(self.active_trial[0],self.active_trial[1]+1)
        if len(self.records)%self.repair_interval==0:self.refresh()
        trial_finished=self.active_trial is not None and (a['levels_completed']>b['levels_completed'] or not self.active_script)
        if trial_finished:
            script=self.active_trial[0]
            self.policy_records.append(Transition(self.trial_source,self.trial_history,('program',script),a,
                                                  consequence(self.trial_source,a)+(self.active_trial[1],)))
            self.refresh_policy()
            self.trial_source=None
        if a['levels_completed']>b['levels_completed']:
            # A successful action program is a candidate capability. It is
            # tested on a later episode before being called transferable.
            script=self.since_progress
            if self.retain_scripts and script and len(script)<=self.max_script_length:
                if not any(s['actions']==script and freeze(s['source'])==freeze(self.level_start) for s in self.scripts):
                    self.scripts.append({'actions':script,'source':self.level_start,
                                         'history':self.policy_history,'evidence':digest(script)})
            if self.active_trial is not None:
                self.script_successes+=1
            self.active_trial=None;self.active_script=()
            self.since_progress=()
            self.refresh()
            self.visits.clear()
            self.history=()
            self.global_history+=(('progress',a['levels_completed']-b['levels_completed']),)
            self.level_start=a
            self.policy_history=self.global_history
        if self.active_trial is not None and not self.active_script:
            self.active_trial=None
        return r

    def policy_state(self,obs,history):
        r=Transition(obs,history,('program',),obs,(0,obs['state']))
        return tuple(freeze(c.evaluate(r)) for c in self.policy_features)

    def refresh_policy(self):
        rows=self.policy_records[-self.evidence_limit:]
        if not rows:return None
        q=lambda r:(r.action,)+tuple(freeze(c.evaluate(r)) for c in self.policy_features)
        f=lambda r:r.outcome
        if not conflict_count(rows,q,f):return None
        existing={c.name for c in self.policy_features}
        candidates=tuple(c for c in self.grammar.candidates(rows,q,f) if c.name not in existing)
        repair=synthesize(rows,q,f,candidates,max_features=2,max_combinations=5000)
        if repair.status=='FINITE_ADEQUATE':
            self.policy_features+=repair.features
        self.policy_repairs.append({'status':repair.status,'before':repair.before,'after':repair.after,
             'features':[c.name for c in repair.features],'witness':repair.witness,
             'evidence_sha256':repair.evidence_sha256})
        return repair

    def _script_candidates(self, obs):
        if not self.retain_scripts:return ()
        guard=self.policy_state(obs,self.global_history)
        choices=set()
        for entry in self.scripts:
            if not self.allow_provisional and entry['actions'] not in self.approved_scripts:continue
            if self.policy_state(entry['source'],entry['history'])!=guard:continue
            script=entry['actions']
            if len(script)>self.max_script_length:continue
            choices.add(script)
            if not self.allow_provisional:continue
            # Generic one-deletion closure. Every shorter candidate requires
            # external replay; deletion is not a proof of semantic equivalence.
            for i in range(len(script)):
                if len(script)>1:choices.add(script[:i]+script[i+1:])
        return tuple(sorted(choices,key=lambda s:(len(s),s)))

    def _graph(self):
        graph=defaultdict(lambda:defaultdict(set))
        for r in self.records:
            src=self.state(r.source,r.history)
            next_history=() if r.outcome[0]>0 else r.history+(r.action,)
            dst=self.state(r.target,next_history)
            graph[src][r.action].add((dst,r.outcome))
        return graph

    def choose(self,frame):
        obs=observation(frame)
        if self.active_script:
            a=self.active_script[0];self.active_script=self.active_script[1:]
            return a
        # The candidate is a program generated from an observed success, not
        # a built-in game rule. A fresh level is a provisional replay trial.
        if not self.history and self.retain_scripts:
            guard=self.policy_state(obs,self.global_history)
            for script in self._script_candidates(obs):
                key=(guard,script)
                if key not in self.script_trials:
                    self.script_trials.add(key);self.script_attempts+=1
                    self.active_trial=(script,0);self.active_script=script[1:]
                    self.trial_source=obs;self.trial_history=self.global_history
                    return script[0]
        key=self.state(obs,self.history)
        graph=self._graph()
        # Search only witnessed deterministic edges for a protected success.
        queue=deque([(key,())]);seen={key}
        while queue:
            node,path=queue.popleft()
            for action,successors in sorted(graph.get(node,{}).items()):
                if len(successors)!=1:continue
                nxt,out=next(iter(successors))
                candidate=path+(action,)
                if out[0]>0 or out[1]=='WIN':return candidate[0]
                if nxt not in seen and len(candidate)<16:
                    seen.add(nxt);queue.append((nxt,candidate))
        # A bounded, model-free experiment selector. It does not assume motion.
        return min(self.actions,key=lambda a:(self.visits.get((key,a),0),self.actions.index(a)))

    def act(self,env,frame):
        a=self.choose(frame)
        key=self.state(observation(frame),self.history)
        self.visits[key,a]=self.visits.get((key,a),0)+1
        after=env.step(a)
        if after is None:raise RuntimeError('Missing external observation')
        self.observe(frame,a,after)
        return after

    def snapshot(self):
        return {'records':len(self.records),'archived_records':len(self.evidence_archive),'features':[c.name for c in self.features],
                'version':self.version,'repairs':self.repair_log,'scripts':len(self.scripts),
                'script_attempts':self.script_attempts,'script_successes':self.script_successes,
                'evidence_sha256':digest([(r.action,r.outcome) for r in self.records]),
                'model_calls':self.model_calls,'policy_features':[c.name for c in self.policy_features],
                'policy_repairs':self.policy_repairs,'policy_records':len(self.policy_records),
                'approved_scripts':len(self.approved_scripts),'qualification_log':self.qualification_log}


def run_episode(env,actions,max_actions=300,development=None):
    d=development if development is not None else Development(tuple(actions))
    d.begin_episode()
    frame=env.observation_space
    if frame is None:frame=env.reset()
    if d.level_start is None:d.level_start=observation(frame)
    if not d.policy_history:d.policy_history=d.global_history
    levels=[];count=0
    while count<max_actions and not terminal(observation(frame)):
        before=observation(frame)
        frame=d.act(env,frame);count+=1
        if observation(frame)['levels_completed']>before['levels_completed']:
            levels.append(count)
    return {'actions':count,'levels_completed':observation(frame)['levels_completed'],
            'state':observation(frame)['state'],'level_actions':levels,**d.snapshot()}
