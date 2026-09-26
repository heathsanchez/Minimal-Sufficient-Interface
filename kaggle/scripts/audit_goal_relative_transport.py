"""Independent oracle for prospective goal-relative transport.

This tests only the declared transport contract: a successful action program may
be proposed in a new observation before that observation has reached progress,
provided the exposed action interface binding matches. It is not ARC score
evidence and does not certify unseen dynamics.
"""
from __future__ import annotations
import argparse,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'kaggle/src'))
from metalogic_arc3.developmental_controller import ProgressMemory
from metalogic_arc3.runtime import ActionToken,normalize_frame

def obs(v,level=0,actions=(1,2,3),state='NOT_FINISHED'):
    return normalize_frame(dict(frame=[[[v,0],[0,0]]],levels_completed=level,state=state,available_actions=list(actions)))

def check(n=512):
    rng=random.Random(202609262004)
    mismatches=[];checks=0
    for case in range(n):
        prog=tuple(rng.sample((1,2,3),rng.choice((1,2,3))))
        m=ProgressMemory()
        train=[obs(10+case*10+i) for i in range(len(prog))]+[obs(19+case*10,1)]
        m.begin(train[0])
        for b,a,c in zip(train,prog,train[1:]): m.observe(b,ActionToken(a),c)
        # New pixels, same declared interface, no goal has been observed here.
        novel=obs(100000+case)
        m.begin(novel); got=m.plan(novel)
        checks+=1
        if got is None or got.action.action_id!=prog[0] or got.action.source!='crystal_relative':
            mismatches.append(dict(case=case,program=prog,actual=None if got is None else [got.action.action_id,got.action.source]))
        # Changed interface must not transport.
        changed=obs(200000+case,actions=(1,2))
        m.begin(changed); blocked=m.plan(changed);checks+=1
        if blocked is not None and blocked.action.source=='crystal_relative':
            mismatches.append(dict(case=case,reason='changed_interface_not_blocked'))
        # Empty-memory ablation must remove the proposal.
        e=ProgressMemory();e.begin(novel);checks+=1
        if e.plan(novel) is not None:
            mismatches.append(dict(case=case,reason='empty_memory_acted'))
    return dict(schema='arc3.independent-goal-relative-transport-oracle@1',worlds=n,checks=checks,
                mismatches=mismatches,passed=not mismatches,
                scope='prospective transport contract only; not unseen-dynamics or ARC generalization evidence')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    r=check();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,sort_keys=True))
    if not r['passed']:raise SystemExit(1)
if __name__=='__main__':main()
