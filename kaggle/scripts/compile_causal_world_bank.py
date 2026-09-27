from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    data=json.loads(a.input.read_text())
    supports=defaultdict(lambda:defaultdict(list)); observations=0
    for row in data['results']:
        game=row['game_id']
        xs=row.get('candidate_causal_examples',[])
        by_epoch=defaultdict(list)
        for x in xs:
            observations+=1; by_epoch[x.get('epoch',0)].append(x)
        for epoch,seq in by_epoch.items():
            seq.sort(key=lambda x:x.get('step',0))
            for i,x in enumerate(seq):
                depth=None
                for j in range(i,len(seq)):
                    y=seq[j]
                    if y.get('after_level',0)>x.get('before_level',0):
                        depth=j-i+1; break
                    if y.get('after_state') in ('GAME_OVER','WIN'):
                        break
                supports[x['role']][game].append(depth)
    laws={}
    for role,games in supports.items():
        rg={}
        for game,depths in games.items():
            positives=[d for d in depths if d is not None]
            rg[game]={'min_observed_positive_depth':min(positives) if positives else None,
                      'positive_occurrences':len(positives),'occurrences':len(depths)}
        laws[role]=rg
    out={'schema':'arc3.progress-future-quotient-bank@1','roles':laws,'observations':observations,
         'boundary':'Observed finite lineage only. Depth is distance along the recorded episode to the next positive level-progress event before terminal/reset. It is evidence of reachable progress, not a proof of minimum environmental distance. Runtime excludes target-game support and uses depth only as a prospective-cost ordering; no legal action is eliminated.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    pos=sum(1 for games in laws.values() for v in games.values() if v['min_observed_positive_depth'] is not None)
    print(json.dumps({'roles':len(laws),'observations':observations,'positive_role_game_supports':pos},sort_keys=True))
if __name__=='__main__':main()
