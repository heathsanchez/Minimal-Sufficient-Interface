"""Prospective process proof for typed residual routing.

Tests three things:
1. wording invariance: six very different attachment phrasings map identically
   because routing uses provenance fields, not lexical similarity;
2. non-attachment residual types remain exact;
3. attachment certificate is causal: adding it changes ATTACHMENT -> safe state,
   while ablating it restores the block on global promotion.
"""
from typed_residual_protocol import compile_residual

PARAPHRASES = [
    'Before using the subsystem lemma, establish that every target counterexample enters that subsystem.',
    'The implication is valid locally; certify that the live reduction satisfies its hypotheses.',
    'The result holds in the model class, but membership of the current frontier in that class remains unproved.',
    'Show that every global survivor is represented by an object obeying the lemma premises.',
    'A theorem was proved on a restricted quotient; justify transporting it back to the target problem.',
    'The local certificate is sound, but no bridge from the target state to its domain has been established.',
]

OTHER = [
    ('solver could not replay the certificate','verification','VERIFIER'),
    ('runner dependency install failed','infrastructure','INFRA'),
    ('current encoding aliases two required cases','representation','REPRESENTATION'),
    ('find an observation separating live models','observable','OBSERVABLE'),
    ('existing rules do not compose to the target','composition','COMPOSITION'),
    ('derive theorem from installed laws','derivation','DERIVATION'),
    ('search remaining witness class','search','SEARCH'),
]

def attachment(statement, cert=False):
    return compile_residual(statement=statement,stage='post-local-proof',
        local_scope='verified-subsystem',target_scope='global-target',
        verified_local_result=True,attachment_certificate=cert,
        evidence_ids=('law:local',))

if __name__=='__main__':
    rows=[]
    for text in PARAPHRASES:
        r=attachment(text,False)
        rows.append((r.kind(),r.safe_for_global_promotion()))
    assert all(k=='ATTACHMENT' and not safe for k,safe in rows), rows

    other_rows=[]
    for text,gate,expected in OTHER:
        r=compile_residual(statement=text,stage='verified-cycle',
            local_scope='global-target',target_scope='global-target',
            verified_local_result=False,failed_gate=gate)
        other_rows.append((expected,r.kind()))
    assert all(a==b for a,b in other_rows), other_rows

    # Causal intervention / ablation on the actual missing bridge.
    blocked=attachment(PARAPHRASES[0],False)
    attached=attachment(PARAPHRASES[0],True)
    reablated=attachment(PARAPHRASES[0],False)
    assert blocked.kind()=='ATTACHMENT' and not blocked.safe_for_global_promotion()
    assert attached.kind()!='ATTACHMENT' and attached.safe_for_global_promotion()
    assert reablated.kind()=='ATTACHMENT' and not reablated.safe_for_global_promotion()

    import json
    print(json.dumps({
      'paraphrase_attachment':len(rows),
      'other_types':len(other_rows),
      'attachment_intervention': {
        'before':blocked.to_dict(),'with_certificate':attached.to_dict(),
        'certificate_ablated':reablated.to_dict()},
      'process_consequence':'Residual routing is provenance-typed; free-text wording no longer determines attachment safety.'
    },indent=2,sort_keys=True))
    print('TYPED_RESIDUAL_PROCESS_TOURNAMENT_PASS')
