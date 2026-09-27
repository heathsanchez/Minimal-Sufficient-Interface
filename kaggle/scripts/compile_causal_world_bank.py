from __future__ import annotations
import argparse,json,hashlib
from collections import defaultdict
from pathlib import Path

def cid(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    data=json.loads(a.input.read_text())
    transports=[]; observations=0
    for row in data['results']:
        game=row['game_id']; xs=row.get('candidate_causal_examples',[])
        by_epoch=defaultdict(list)
        for x in xs: observations+=1; by_epoch[x.get('epoch',0)].append(x)
        for epoch,seq in by_epoch.items():
            seq.sort(key=lambda x:x.get('step',0))
            start=0
            for j,x in enumerate(seq):
                if x.get('after_level',0)>x.get('before_level',0):
                    segment=seq[start:j+1]
                    if segment:
                        program=[s['role'] for s in segment]
                        source_tests=sorted(set(s['role'] for s in segment[:max(1,min(4,len(segment)))]))
                        obj={'game':game,'epoch':epoch,'source_tests':source_tests,
                             'program_roles':program,'progress_delta':x['after_level']-segment[0]['before_level'],
                             'cost':len(segment)}
                        obj['id']=cid(obj); transports.append(obj)
                    start=j+1
                elif x.get('after_state') in ('GAME_OVER','WIN'):
                    start=j+1
    out={'schema':'arc3.certified-continuation-transport-bank@1','transports':transports,
         'observations':observations,
         'boundary':'Finite public-development witnesses only. A transport records an observed causal segment ending in protected level progress, its initial role tests, program-role lineage, support game, and observed cost. Runtime excludes target-game support. Applicability is CANDIDATE until its source tests are witnessed live; no unmatched action is eliminated.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'observations':observations,'transports':len(transports),
                      'min_cost':min((t['cost'] for t in transports),default=None),
                      'max_cost':max((t['cost'] for t in transports),default=None)},sort_keys=True))
if __name__=='__main__':main()
