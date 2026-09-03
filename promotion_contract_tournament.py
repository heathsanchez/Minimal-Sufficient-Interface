"""Matched qualification for the earned promotion contract."""
from verified_promotion_contract import PromotionEvidence,promotable

def ev(**kw):
    base=dict(verifier_id='V',executed=True,passed=True,
              verified_scope=frozenset({'SHORT'}),promoted_scope=frozenset({'SHORT'}))
    base.update(kw); return PromotionEvidence(**base)

def main():
    cases=[
      ('same-scope',ev(),True),
      ('unexecuted',ev(executed=False),False),
      ('failed',ev(passed=False),False),
      ('silent-scope-widen',ev(promoted_scope=frozenset({'SHORT','LONG'})),False),
      ('certified-scope-widen',ev(promoted_scope=frozenset({'SHORT','LONG'}),widening_certificate='scope-ablation',widening_certificate_passed=True),True),
      ('need-equality-completion',ev(equality_completion_required=True,equality_completion_passed=False),False),
      ('completed-equality',ev(equality_completion_required=True,equality_completion_passed=True),True),
      ('syntactic-inequality',ev(inequalities=(('h','w','different names'),)),False),
      ('source-backed-inequality',ev(inequalities=(('b0','x','LONG block definition'),)),True),
    ]
    rows=[]
    for name,e,expected in cases:
        got,reason=promotable(e); rows.append((name,got,reason)); assert got==expected,(name,got,reason)
    # Ablation: the old naive promoter accepts every passed candidate and therefore
    # wrongly promotes all three failure-derived negative controls below.
    naive_false_promotions=0
    for name,e,expected in cases:
        naive=e.passed
        if naive and not expected: naive_false_promotions+=1
    assert naive_false_promotions>=3
    print({'cases':rows,'candidate_correct':len(cases),'naive_false_promotions':naive_false_promotions})
    print('PROMOTION_CONTRACT_TOURNAMENT_PASS')
if __name__=='__main__':main()