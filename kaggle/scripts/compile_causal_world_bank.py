from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    data=json.loads(a.input.read_text())
    role_game=defaultdict(lambda:defaultdict(Counter)); observations=0
    for row in data['results']:
        game=row['game_id']
        for ex in row.get('candidate_causal_examples',[]):
            observations+=1
            role_game[ex['role']][game][json.dumps(ex['outcome'],separators=(',',':'))]+=1
    laws={}; conflicts=0
    for role,games in role_game.items():
        # Each source game contributes at most one vote for an outcome and only
        # if its own evidence is deterministic. Conflicting source-game roles
        # remain UNKNOWN rather than majority-voting their internal traces.
        outcomes=defaultdict(list)
        for game,c in games.items():
            if len(c)!=1:
                conflicts+=1; continue
            outcome=next(iter(c))
            outcomes[outcome].append(game)
        if outcomes:
            laws[role]={out:sorted(gs) for out,gs in sorted(outcomes.items())}
    out={'schema':'arc3.causal-law-product-bank@1','laws':laws,'observations':observations,
         'conflicting_source_game_roles':conflicts,
         'boundary':'Independent role→consequence fragments. Runtime removes target-game support from each consequence; a consequence remains admissible only with at least one other-game support. No historical game identity is a world and no conflicting within-game role is majority-voted.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'roles':len(laws),'outcome_fragments':sum(len(x) for x in laws.values()),
                      'observations':observations,'conflicts':conflicts},sort_keys=True))
if __name__=='__main__':main()
