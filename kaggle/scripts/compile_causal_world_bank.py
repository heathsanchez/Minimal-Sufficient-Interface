from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    data=json.loads(a.input.read_text())
    worlds={}
    conflicts=0; observations=0
    for row in data['results']:
        game=row['game_id']; by=defaultdict(set)
        for ex in row.get('candidate_causal_examples',[]):
            observations+=1
            by[ex['role']].add(json.dumps(ex['outcome'],separators=(',',':')))
        world={}
        for role,outs in by.items():
            if len(outs)==1: world[role]=next(iter(outs))
            else: conflicts+=1
        worlds[game]=world
    out={'schema':'arc3.causal-world-bank@1','worlds':worlds,'observations':observations,
         'conflicting_game_roles':conflicts,
         'boundary':'Public-development causal worlds. Runtime public evaluation excludes the target game. A role prediction is present only when that game observed one deterministic protected outcome for the role; missing/conflicting roles remain UNKNOWN.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'worlds':len(worlds),'observations':observations,'conflicts':conflicts,
                      'roles':sum(len(v) for v in worlds.values())},sort_keys=True))
if __name__=='__main__':main()
