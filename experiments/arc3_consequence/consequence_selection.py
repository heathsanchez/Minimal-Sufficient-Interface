"""Bounded, source-blind consequence discovery around the existing MSI kernel.

A candidate is an observable statistic, not a semantic game rule. It is
promoted only by held-out prediction of action-conditioned consequences.
The protected progress/terminal outcome remains authoritative. No source or
hidden game state is inspected. Failure to qualify is an explicit result.
"""
from __future__ import annotations
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'convergence'))
from finite_consequence import Candidate, freeze, digest, synthesize, conflict_count, replay
from agent import Development, Transition, observation, consequence, terminal


def pixels(o):
    return tuple(freeze(layer) for layer in o.get('frame', ()))


def flat(o):
    return tuple(v for layer in o.get('frame', ()) for row in layer for v in row)


def signatures():
    """Frozen generic observations; no palette meanings or object labels."""
    return (
        Candidate('changed', 1, lambda r: pixels(r.source) != pixels(r.target)),
        Candidate('changed_cells', 2, lambda r: sum(a != b for a,b in zip(flat(r.source),flat(r.target))) if len(flat(r.source)) == len(flat(r.target)) else None),
        Candidate('value_count_delta', 3, lambda r: tuple(sorted((v, Counter(flat(r.target))[v]-Counter(flat(r.source))[v]) for v in set(flat(r.source)) | set(flat(r.target)) if Counter(flat(r.target))[v] != Counter(flat(r.source))[v]))),
        Candidate('observation_delta', 100, lambda r: (pixels(r.source),pixels(r.target))),
    )


def prediction_score(rows, candidate, base=lambda r: r.action):
    """Temporal held-out exact prediction; no future rows used to fit modes."""
    split = max(1, len(rows)*2//3)
    train, test = rows[:split], rows[split:]
    if not test: return None
    tables = defaultdict(Counter)
    global_counts = Counter()
    for r in train:
        value = freeze(candidate.evaluate(r))
        tables[freeze(base(r))][value] += 1
        global_counts[value] += 1
    if len(global_counts) < 2: return None
    default = global_counts.most_common(1)[0][0]
    covered = [r for r in test if freeze(base(r)) in tables]
    if len(covered) < 4: return None
    correct = sum(tables[freeze(base(r))].most_common(1)[0][0] == freeze(candidate.evaluate(r)) for r in covered)
    baseline = sum(default == freeze(candidate.evaluate(r)) for r in covered)
    return {'accuracy':correct/len(covered),'baseline':baseline/len(covered),'coverage':len(covered),'test_rows':len(test)}


@dataclass(frozen=True)
class ConsequenceSelection:
    status: str
    candidate: object = None
    evidence: object = None


def select_consequence(rows, candidates=None, minimum_accuracy=.8):
    candidates = signatures() if candidates is None else candidates
    eligible=[]
    for c in candidates:
        score=prediction_score(rows,c)
        if score is not None and score['accuracy'] >= minimum_accuracy and score['accuracy'] > score['baseline']:
            eligible.append((-score['accuracy'],c.rank,c.name,c,score))
    if not eligible:
        return ConsequenceSelection('NO_QUALIFIED_CONSEQUENCE',None,{'rows':len(rows)})
    _,_,_,c,score=min(eligible,key=lambda x:x[:3])
    return ConsequenceSelection('HELDOUT_PREDICTIVE',c,dict(score,rows=len(rows),evidence_sha256=digest([(r.action,c.evaluate(r)) for r in rows])))


class ConsequenceController(Development):
    """The existing developmental kernel, with a qualified intermediate target.

    The selector and the representation repair are separate. A predictive
    statistic is never treated as proof of a goal, causal mechanism or transfer.
    """
    def __init__(self, actions, enabled=True, **kw):
        super().__init__(tuple(actions), **kw)
        self.enabled=enabled
        self.intermediate=None
        self.selection_log=[]
        self.intermediate_features=()
        self.intermediate_repairs=[]
        self.dense_visits=defaultdict(int)
        self.intermediate_interval=16

    def begin_episode(self):
        super().begin_episode()
        self.dense_visits.clear()

    def refresh_intermediate(self):
        if not self.enabled:return None
        rows=self.records[-self.evidence_limit:]
        if len(rows)<12:return None
        selection=select_consequence(rows)
        if selection.status!='HELDOUT_PREDICTIVE':
            return selection
        if self.intermediate is None or self.intermediate.name!=selection.candidate.name:
            self.intermediate=selection.candidate
            self.intermediate_features=()
            self.selection_log.append({'status':selection.status,'candidate':self.intermediate.name,'evidence':selection.evidence})
        target=lambda r:freeze(self.intermediate.evaluate(r))
        q=lambda r:(r.action,)+tuple(freeze(c.evaluate(r)) for c in self.intermediate_features)
        before=conflict_count(rows,q,target)
        if not before:return selection
        existing={c.name for c in self.intermediate_features}
        pool=tuple(c for c in self.grammar.candidates(rows,q,target) if c.name not in existing)
        repair=synthesize(rows,q,target,pool,max_features=2,max_combinations=5000)
        self.intermediate_repairs.append({'status':repair.status,'before':before,'after':repair.after,'features':[c.name for c in repair.features]})
        if repair.status=='FINITE_ADEQUATE':
            self.intermediate_features+=repair.features
            assert replay(rows,lambda r:r.action,target,type('R',(),{'features':self.intermediate_features})())==0
        return selection

    def observe(self,before,action,after):
        r=super().observe(before,action,after)
        if self.enabled and len(self.records)%self.intermediate_interval==0:
            self.refresh_intermediate()
        return r

    def dense_state(self,obs,history):
        r=Transition(obs,history,-1,obs,(0,obs['state']))
        return tuple(freeze(c.evaluate(r)) for c in self.intermediate_features)

    def choose(self,frame):
        if not self.enabled or self.intermediate is None:
            return super().choose(frame)
        obs=observation(frame)
        # Externally verified progress remains the first priority.
        if self.active_script or (not self.history and self._script_candidates(obs)):
            return super().choose(frame)
        key=self.dense_state(obs,self.history)
        target=lambda r:freeze(self.intermediate.evaluate(r))
        graph=defaultdict(lambda:defaultdict(set))
        for r in self.records:
            src=self.dense_state(r.source,r.history)
            dst=self.dense_state(r.target,r.history+(r.action,))
            graph[src][r.action].add((dst,freeze(r.outcome),target(r)))
        queue=deque([(key,())]);seen={key}
        while queue:
            node,path=queue.popleft()
            for action,successors in sorted(graph.get(node,{}).items()):
                if len(successors)!=1:continue
                nxt,out,_=next(iter(successors));candidate=path+(action,)
                if out[0]>0 or out[1]=='WIN':return candidate[0]
                if nxt not in seen and len(candidate)<16:
                    seen.add(nxt);queue.append((nxt,candidate))
        # Prefer an untested action in the refined state. Only observed
        # no-change effects receive a penalty; no goal semantics are assumed.
        def cost(a):
            successors=graph.get(key,{}).get(a,set())
            unchanged=bool(successors) and all(effect is False or effect == 0 or effect == () for _,_,effect in successors)
            return (self.dense_visits[key,a],int(unchanged),self.actions.index(a))
        return min(self.actions,key=cost)

    def act(self,env,frame):
        key=self.dense_state(observation(frame),self.history)
        action=self.choose(frame)
        self.dense_visits[key,action]+=1
        self.visits[self.state(observation(frame),self.history),action]=self.visits.get((self.state(observation(frame),self.history),action),0)+1
        after=env.step(action)
        if after is None:raise RuntimeError('Missing external observation')
        self.observe(frame,action,after)
        return after

    def snapshot(self):
        return dict(super().snapshot(),consequence_selection=self.selection_log,
                    intermediate_features=[c.name for c in self.intermediate_features],
                    intermediate_repairs=self.intermediate_repairs,
                    selected_consequence=self.intermediate.name if self.intermediate else None)
