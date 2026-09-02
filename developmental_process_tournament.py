"""Matched A/B process tournament for next-action selection.

This is a constructed controller qualification, not evidence that E677 is solved.
The task/verifier/cases are fixed; only the process policy changes.
"""
from __future__ import annotations
from developmental_operating_system import DevelopmentalOperatingSystem, DevelopmentalOSState, LockState

CASES = [
    ('Need a quotient representation that preserves the decision.', 'REFRAME'),
    ('Find an observable probe separating the remaining hypotheses.', 'PROBE'),
    ('The proof certificate verifier cannot replay this claim.', 'VERIFY'),
    ('The GitHub runner timed out while installing a dependency.', 'INFRA'),
    ('Search the remaining candidate space for a witness.', 'PUSH'),
    ('Current finite scope is insufficient; test whether the law generalizes to the infinite domain.', 'SCOPE'),
    ('The available rewrite operator cannot express the required transformation.', 'OPERATOR'),
    ('Pairwise rules work but their composition/closure leaves the target unreachable.', 'COMPOSITION'),
]
HELDOUT = [
    ('Compress the surviving states by the smallest decision-preserving encoding.', 'REFRAME'),
    ('What measurement would distinguish these two survivors?', 'PROBE'),
    ('Replay fails under the independent judge despite a claimed proof.', 'VERIFY'),
    ('Package installation fails on the CI runner.', 'INFRA'),
    ('Enumerate candidates until a counterexample or witness appears.', 'PUSH'),
    ('The bounded domain may be the issue; enlarge the scope.', 'SCOPE'),
    ('No licensed operation can produce the missing move.', 'OPERATOR'),
    ('Binary attachments succeed individually but not when chained.', 'COMPOSITION'),
]

EXPECTED_FROM_TYPE = {
    'REPRESENTATION':'REFRAME','OBSERVABLE':'PROBE','VERIFIER':'VERIFY','INFRA':'INFRA',
    'SEARCH':'PUSH','SCOPE':'SCOPE','OPERATOR':'OPERATOR','COMPOSITION':'COMPOSITION','UNKNOWN':'PROBE'
}


def baseline_policy(_: str) -> str:
    # Frozen pre-routing default: push strongest current route first.
    return 'PUSH'


def routed_policy(os: DevelopmentalOperatingSystem, residual: str) -> str:
    typ,_=os.classify_residual(residual)
    return EXPECTED_FROM_TYPE[typ]


def score(policy, cases):
    rows=[]; correct=0
    for residual,expected in cases:
        got=policy(residual)
        ok=got==expected; correct+=ok
        rows.append({'residual':residual,'expected':expected,'got':got,'ok':ok})
    return correct, rows


def main():
    os=DevelopmentalOperatingSystem()
    b_dev,brows=score(baseline_policy,CASES)
    r_dev,rrows=score(lambda x:routed_policy(os,x),CASES)
    b_hold,bhrows=score(baseline_policy,HELDOUT)
    r_hold,rhrows=score(lambda x:routed_policy(os,x),HELDOUT)
    assert r_dev > b_dev, (b_dev,r_dev,rrows)
    assert r_hold > b_hold, (b_hold,r_hold,rhrows)
    assert r_hold >= 6, rhrows
    import json
    out={'dev':{'baseline':b_dev,'routed':r_dev,'n':len(CASES)},'heldout':{'baseline':b_hold,'routed':r_hold,'n':len(HELDOUT)},'heldout_rows':rhrows}
    print(json.dumps(out,indent=2,sort_keys=True))
    print('DEVELOPMENTAL_PROCESS_TOURNAMENT_PASS')

if __name__=='__main__': main()
