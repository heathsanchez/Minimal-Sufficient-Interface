from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'kaggle/src'))
from metalogic_arc3.developmental_controller import ProgressMemory
from metalogic_arc3.runtime import ActionToken,normalize_frame

def obs(v,level=0,actions=(1,2,3),state='NOT_FINISHED'):
    return normalize_frame(dict(frame=[[[v,0],[0,0]]],levels_completed=level,state=state,available_actions=list(actions)))

def run():
    # Context A: the guarded procedure is absent initially. Executing evidence
    # acquires it only after protected progress is actually witnessed.
    m=ProgressMemory()
    a0,a1,agoal=obs(10),obs(11),obs(12,1)
    m.begin(a0)
    assert m.plan(a0) is None
    m.observe(a0,ActionToken(2,source='evidence'),a1)
    m.observe(a1,ActionToken(3,source='evidence'),agoal)
    assert m.relative_programs
    learned=m.relative_programs[-1]

    # Context B: genuinely new observations, same earned applicability binding.
    b0,b1,bgoal=obs(100),obs(101),obs(102,1)
    m.begin(b0)
    p=m.plan(b0); assert p and p.action.action_id==2 and p.action.source=='crystal_relative'
    m.observe(b0,p.action,b1)
    q=m.plan(b1); assert q and q.action.action_id==3 and q.action.source=='crystal_relative'
    m.observe(b1,q.action,bgoal)

    # Ablation: remove learned capability; prospective gain must disappear.
    ab=ProgressMemory();ab.begin(b0)
    assert ab.plan(b0) is None

    # Near miss: changed declared action interface must refuse transfer.
    near=obs(200,actions=(1,2))
    m.begin(near)
    assert m.plan(near) is None

    # Revocation: invalidating any support used by the compiled capability
    # invalidates prospective reuse.
    support=learned['support'][0]
    m.revoked[support]='composition-gate-revocation'
    m._invalidate()
    c0=obs(300);m.begin(c0)
    assert m.plan(c0) is None

    return {'schema':'arc3.developmental-composition-gate@1','passed':True,
      'acquired_actions':list(learned['actions']),
      'prospective_reuse':True,'ablation_removed_gain':True,
      'near_miss_refused':True,'revocation_invalidated_reuse':True,
      'boundary':'Finite declared interface fixture. Establishes composition of acquisition, verified progress, compilation, prospective reuse, ablation, refusal, and revocation; not ARC cross-mechanic generalization.'}

def main():
    out=run();p=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
