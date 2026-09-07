"""Fresh post-repair holdout for ATTACHMENT routing.

These cases were not present in the dev/heldout set that caused the previous
repair.  This file is added without modifying the candidate classifier first.
Its purpose is to distinguish genuine attachment concept capture from phrase
memorization.
"""
from developmental_operating_system import DevelopmentalOperatingSystem
from developmental_operating_system_v2 import AttachmentAwareDevelopmentalOS

CASES = [
    ('Before using the subsystem lemma, establish that every target counterexample enters that subsystem.', 'ATTACHMENT'),
    ('The implication is valid locally; certify that the live reduction satisfies its hypotheses.', 'ATTACHMENT'),
    ('The result holds in the model class, but membership of the current frontier in that class remains unproved.', 'ATTACHMENT'),
    ('Show that every global survivor is represented by an object obeying the lemma premises.', 'ATTACHMENT'),
    ('A theorem was proved on a restricted quotient; justify transporting it back to the target problem.', 'ATTACHMENT'),
    ('The local certificate is sound, but no bridge from the target state to its domain has been established.', 'ATTACHMENT'),
]

def score(os):
    rows=[]; n=0
    for residual,expected in CASES:
        got,_=os.classify_residual(residual)
        ok=got==expected; n+=int(ok)
        rows.append({'residual':residual,'expected':expected,'got':got,'ok':ok})
    return n,rows

if __name__=='__main__':
    b,br=score(DevelopmentalOperatingSystem())
    c,cr=score(AttachmentAwareDevelopmentalOS())
    import json
    print(json.dumps({'baseline':b,'candidate':c,'n':len(CASES),'candidate_rows':cr},indent=2,sort_keys=True))
    # No soft pass: either the distinction generalizes or this becomes the next process residual.
    assert c==len(CASES), cr
    assert c>b, (b,c)
    print('ATTACHMENT_FRESH_HOLDOUT_PASS')
