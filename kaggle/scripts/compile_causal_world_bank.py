from __future__ import annotations
import argparse,json,hashlib
from collections import defaultdict
from pathlib import Path

def cid(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def role_obj(s):
    try:return json.loads(s)
    except:return s

def features(role):
    r=role_obj(role)
    if not isinstance(r,list): return {}
    out={}
    out['kind']=r[0] if r else None
    if r and r[0]=='ACTION' and len(r)>1: out['action_id']=r[1]
    if r and r[0]=='CLICK' and len(r)>1:
        patch=r[1]
        flat=[tuple(x) if isinstance(x,list) else x for row in patch for x in row]
        out['patch_shape']=[len(patch),len(patch[0]) if patch else 0]
        out['boundary_count']=sum(1 for x in flat if isinstance(x,tuple) and x and x[0]=='BOUNDARY')
        cells=[x[1] for x in flat if isinstance(x,tuple) and x and x[0]=='CELL']
        out['distinct_cells']=len(set(cells))
        if patch: out['center']=patch[len(patch)//2][len(patch[0])//2]
    return out

def minimal_guard(pos_roles,neg_roles):
    pf=[features(r) for r in pos_roles]; nf=[features(r) for r in neg_roles]
    keys=sorted(set().union(*(x.keys() for x in pf+nf)))
    atoms=[]
    for k in keys:
        vals={json.dumps(x.get(k),sort_keys=True) for x in pf}
        if len(vals)==1:
            v=next(iter(vals))
            if any(json.dumps(x.get(k),sort_keys=True)!=v for x in nf):
                atoms.append((k,json.loads(v)))
    # smallest consequential representation: one witnessed separator is enough;
    # ties are preserved as alternatives rather than conjoined gratuitously.
    return [{'key':k,'value':v} for k,v in atoms]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    data=json.loads(a.input.read_text()); observations=0; transports=[]
    all_by_game={}
    for row in data['results']:
        xs=row.get('candidate_causal_examples',[]);all_by_game[row['game_id']]=xs;observations+=len(xs)
    for game,xs in all_by_game.items():
        by_epoch=defaultdict(list)
        for x in xs: by_epoch[x.get('epoch',0)].append(x)
        for epoch,seq in by_epoch.items():
            seq.sort(key=lambda x:x.get('step',0)); start=0
            for j,x in enumerate(seq):
                if x.get('after_level',0)>x.get('before_level',0):
                    seg=seq[start:j+1]; start=j+1
                    if not seg: continue
                    pos=[z['role'] for z in seg]
                    # Near misses are roles actually observed in other games
                    # without any later progress in their own recorded epoch.
                    neg=[]
                    for og,oys in all_by_game.items():
                        if og==game: continue
                        for z in oys:
                            if z.get('after_level',0)<=z.get('before_level',0): neg.append(z['role'])
                    guards=minimal_guard(pos[:max(1,min(4,len(pos)))],neg)
                    obj={'game':game,'epoch':epoch,'program_roles':pos,'progress_delta':x['after_level']-seg[0]['before_level'],
                         'cost':len(seg),'guard_alternatives':guards}
                    obj['id']=cid(obj);transports.append(obj)
                elif x.get('after_state') in ('GAME_OVER','WIN'): start=j+1
    out={'schema':'arc3.applicability-genesis-bank@1','transports':transports,'observations':observations,
         'boundary':'Guards are minimum single-feature separators derived only from positive progress prefixes versus observed cross-game near-miss roles. Alternatives are preserved. Runtime excludes target-game support; guards rank candidate transports but do not eliminate legal actions.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'observations':observations,'transports':len(transports),'guarded':sum(bool(t['guard_alternatives']) for t in transports),
                      'guard_alternatives':sum(len(t['guard_alternatives']) for t in transports)},sort_keys=True))
if __name__=='__main__':main()
