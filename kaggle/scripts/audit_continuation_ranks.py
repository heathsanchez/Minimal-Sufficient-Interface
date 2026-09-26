"""Independent exhaustive-policy oracle for finite observed continuation ranks.

Tests the frozen candidate's symbolic planner against all deterministic policies
in fixed small worlds; this is not a real-game score or generalization test.
"""
from __future__ import annotations
import argparse
import itertools
import json
from math import inf
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'kaggle/src'))
from metalogic_arc3.developmental_controller import ProgressMemory
from metalogic_arc3.residual_exploration import frontier_continuation
from metalogic_arc3.runtime import ActionToken,normalize_frame


def oracle(graph,start,frontier=False,first_action=None):
    best=inf
    n=3
    for policy in itertools.product((1,2),repeat=n):
        if first_action is not None and policy[start] != first_action: continue
        def visit(state,active):
            if state==3: return inf if frontier else 0
            if state==4 or state in active: return inf
            targets=graph.get((state,policy[state]),())
            if not targets: return 1 if frontier else inf
            return 1+max(visit(t,active|{state}) for t in targets)
        best=min(best,visit(start,frozenset()))
    return None if best==inf else best


def check(count=512):
    rng=random.Random(202609261101)
    observations=[normalize_frame(dict(frame=[[[i+1]]],available_actions=[1,2],
                  levels_completed=int(i==3),state='WIN' if i==3 else 'GAME_OVER' if i==4 else 'NOT_FINISHED'))
                  for i in range(5)]
    checked=0
    mismatch=[]
    for case in range(count):
        graph={}
        m=ProgressMemory(max_history=2)
        for s in range(3):
            for a in (1,2):
                targets=tuple(t for t in range(5) if rng.randrange(5)==0)
                graph[(s,a)]=targets
                for t in targets:
                    m.begin(observations[s])
                    m.observe(observations[s],ActionToken(a),observations[t])
        assert m.history_depth==0
        # This oracle qualifies the exact-state finite regression planner only.
        # Goal-relative transport has a separate oracle because it intentionally
        # acts where the absolute planner has no matching state.
        relative_programs = m.relative_programs
        m.relative_programs = []
        for s in range(3):
            for mode in (False,True):
                m.begin(observations[s])
                got=(frontier_continuation(m,observations[s],lambda _:(ActionToken(1),ActionToken(2)))
                     if mode else m.plan(observations[s]))
                actual=None if got is None else got.rank
                expected=oracle(graph,s,mode)
                checked+=1
                selected=None if got is None else oracle(graph,s,mode,got.action.action_id)
                if expected!=actual or (got is not None and selected!=actual):
                    mismatch.append(dict(case=case,start=s,frontier=mode,expected=expected,actual=actual,selected_action_rank=selected,
                        graph=[dict(source=k[0],action=k[1],targets=v) for k,v in graph.items()]))
        m.relative_programs = relative_programs
        # Canonical full-state serialization must preserve all resulting plans.
        restored=ProgressMemory.from_json(m.to_json())
        assert restored.to_json()==m.to_json()
    return dict(schema='arc3.independent-finite-policy-oracle@1',seed=202609261101,
                worlds=count,rank_comparisons=checked,all_policies_per_world=8,
                mismatches=mismatch,passed=not mismatch,
                scope='finite observed models only; neither unseen dynamics nor ARC generalization')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    result=check();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))
    if not result['passed']: raise SystemExit(1)

if __name__=='__main__': main()
