"""Matched process tournament for the ATTACHMENT distinction.

The original controller is the frozen baseline. The candidate must preserve all
existing routing cases and improve on attachment-specific held-out cases.
"""
from developmental_operating_system import DevelopmentalOperatingSystem
from developmental_operating_system_v2 import AttachmentAwareDevelopmentalOS

BASE_CASES = [
    ('Need a quotient representation that preserves the decision.', 'REPRESENTATION'),
    ('Find an observable probe separating the remaining hypotheses.', 'OBSERVABLE'),
    ('The proof certificate verifier cannot replay this claim.', 'VERIFIER'),
    ('Prove the claimed theorem symbolically from the retained laws.', 'DERIVATION'),
    ('The GitHub runner timed out while installing a dependency.', 'INFRA'),
    ('Search the remaining candidate space for a witness.', 'SEARCH'),
    ('Current finite scope is insufficient; test whether the law generalizes to the infinite domain.', 'SCOPE'),
    ('The available rewrite operator cannot express the required transformation.', 'OPERATOR'),
    ('Pairwise rules work but their composition/closure leaves the target unreachable.', 'COMPOSITION'),
]
ATTACH_DEV = [
    ('The phase theorem is verified locally; prove that its assumptions map into the current frontier before using it globally.', 'ATTACHMENT'),
    ('Attach this verified block law to the live frontier or certify non-attachment.', 'ATTACHMENT'),
    ('Lift the local theorem to the global counterexample reduction before promotion.', 'ATTACHMENT'),
    ('Show that this representation layer actually occurs in the live frontier.', 'ATTACHMENT'),
]
ATTACH_HELDOUT = [
    ('The lemma is true on the saturated subsystem, but does it apply to the live frontier?', 'ATTACHMENT'),
    ('Connect this theorem to the current global residual before changing search.', 'ATTACHMENT'),
    ('The assumptions of the local result have not yet been shown to hold in the target reduction.', 'ATTACHMENT'),
    ('Do not promote this discovery until attachment to the global problem is proved.', 'ATTACHMENT'),
]

def score(os, cases):
    rows=[]; ok=0
    for residual, expected in cases:
        got,_=os.classify_residual(residual)
        hit=got==expected
        ok += int(hit)
        rows.append({'residual':residual,'expected':expected,'got':got,'ok':hit})
    return ok, rows


def main():
    baseline=DevelopmentalOperatingSystem()
    candidate=AttachmentAwareDevelopmentalOS()
    b_base,_=score(baseline,BASE_CASES)
    c_base,cbase_rows=score(candidate,BASE_CASES)
    b_dev,bdev_rows=score(baseline,ATTACH_DEV)
    c_dev,cdev_rows=score(candidate,ATTACH_DEV)
    b_hold,bhold_rows=score(baseline,ATTACH_HELDOUT)
    c_hold,chold_rows=score(candidate,ATTACH_HELDOUT)

    # Non-regression on the old routing task is mandatory.
    assert c_base == b_base == len(BASE_CASES), cbase_rows
    # Candidate must strictly improve on both new dev and held-out attachment cases.
    assert c_dev > b_dev and c_dev == len(ATTACH_DEV), (bdev_rows,cdev_rows)
    assert c_hold > b_hold and c_hold == len(ATTACH_HELDOUT), (bhold_rows,chold_rows)

    import json
    out={
        'base_nonregression': {'baseline':b_base,'candidate':c_base,'n':len(BASE_CASES)},
        'attachment_dev': {'baseline':b_dev,'candidate':c_dev,'n':len(ATTACH_DEV)},
        'attachment_heldout': {'baseline':b_hold,'candidate':c_hold,'n':len(ATTACH_HELDOUT)},
        'heldout_rows': chold_rows,
        'promotion': 'ATTACHMENT distinction earned',
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    print('ATTACHMENT_PROCESS_TOURNAMENT_PASS')

if __name__=='__main__':
    main()
