#!/usr/bin/env python3
"""Verifier-dose x meta-language causal protocol.

STATUS: protocol/harness, not a frozen scientific result.

Crucial separation: acquisition-channel outputs are computed from preregistered training
traces. Sealed semantic success is evaluated only AFTER the proposal policy has selected
candidates. Thus V0 cannot leak the held-out answer through a PASS bit.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable, Dict, List, Tuple

BUDGET=1
X=(-3,-2,-1,0,1,2,3)

@dataclass(frozen=True)
class Candidate:
    opaque_id:str
    fn:Callable[[int],int]
    cost:int
    # Acquisition verifier trace from a separate preregistered training interaction.
    # All candidates fail acquisition; payload shape may carry repair-relevant information.
    trace:Tuple[int,int,int,int]

@dataclass(frozen=True)
class Language:
    name:str
    candidates:Tuple[Candidate,...]

# Source-distinct grammars with the same semantic candidate class.  The successful held-out
# candidate has the repair-relevant nonuniform acquisition trace in both grammars, but no
# identifier or ordering correspondence is supplied to the policy.
M_A=Language('A',(
 Candidate('a7',lambda x:abs(x),1,(0,7,7,7)),
 Candidate('a2',lambda x:x+1,2,(0,9,9,9)),
 Candidate('a4',lambda x:-x,1,(0,8,8,8)),
 Candidate('a9',lambda x:x*x,3,(0,9,3,3)),
))
M_B=Language('B',(
 Candidate('zeta',lambda x:-x,1,(0,8,8,8)),
 Candidate('tau',lambda x:x*x,3,(0,9,3,3)),
 Candidate('rho',lambda x:abs(x),1,(0,7,7,7)),
 Candidate('mu',lambda x:x+1,2,(0,9,9,9)),
))
LANGUAGES=(M_A,M_B)

def target(x:int)->int:return x*x

def sealed_success(c:Candidate)->bool:
    return all(c.fn(x)==target(x) for x in X)

def V0_binary(c:Candidate): return (c.trace[0],0,0,0)
def V1_localized(c:Candidate):
    _,a,b,d=c.trace
    return (0, int(a!=b or b!=d), 0, 0)
def V2_genuine(c:Candidate): return c.trace

def scrubbed_factory(lang:Language):
    # All acquisition statuses are FAIL, so this is exactly a conditional-on-FAIL payload
    # permutation preserving the payload multiset while scrubbing candidate linkage.
    payloads=[c.trace[1:] for c in lang.candidates][::-1]
    table={c.opaque_id:(0,*p) for c,p in zip(lang.candidates,payloads)}
    return lambda c:table[c.opaque_id]

def permuted_factory(lang:Language):
    payloads=[c.trace[1:] for c in lang.candidates]
    payloads=payloads[1:]+payloads[:1]
    table={c.opaque_id:(0,*p) for c,p in zip(lang.candidates,payloads)}
    return lambda c:table[c.opaque_id]

def score(out,cost):
    # Frozen policy: prefer a nonuniform residual shape; otherwise lower declared cost.
    _,a,b,d=out
    shape=int(not (a==b==d))
    return (-shape,cost,a+b+d)

def run_cell(lang,name,ch):
    observed=[(c,ch(c)) for c in lang.candidates]
    ranked=sorted(observed,key=lambda z:(score(z[1],z[0].cost),z[0].opaque_id))
    tried=ranked[:BUDGET]
    return {'language':lang.name,'channel':name,'budget':BUDGET,
            'ranked_ids':[c.opaque_id for c,_ in ranked],
            'tried_ids':[c.opaque_id for c,_ in tried],
            'success':any(sealed_success(c) for c,_ in tried),
            'observations':[[c.opaque_id,list(o)] for c,o in observed]}

def leakage_audit(lang,channels):
    assert sum(sealed_success(c) for c in lang.candidates)==1
    assert all(c.trace[0]==0 for c in lang.candidates) # no acquisition PASS leaks answer
    assert BUDGET==1
    for name,ch in channels.items():
        outs=[ch(c) for c in lang.candidates]
        assert all(len(o)==4 for o in outs),name
        assert all(o[0]==0 for o in outs),name
    # Scrubbed arm must preserve genuine payload multiset exactly.
    g=sorted(c.trace[1:] for c in lang.candidates)
    s=sorted(channels['V3_SCRUBBED_INTERVENTION'](c)[1:] for c in lang.candidates)
    assert g==s

def main():
    rows=[]
    for lang in LANGUAGES:
        channels={'V0_BINARY':V0_binary,'V1_LOCALIZED':V1_localized,
                  'V2_GENUINE_RESIDUAL':V2_genuine,
                  'V3_SCRUBBED_INTERVENTION':scrubbed_factory(lang),
                  'V4_PERMUTED_INTERVENTION':permuted_factory(lang)}
        leakage_audit(lang,channels)
        rows += [run_cell(lang,n,ch) for n,ch in channels.items()]
    assert len(rows)==10
    # This harness is constructed to make the causal contrast decidable before freezing:
    # genuine residual must unlock the held-out repair in both grammars; binary must not.
    by={(r['language'],r['channel']):r for r in rows}
    assert all(not by[(m,'V0_BINARY')]['success'] for m in ('A','B'))
    assert all(by[(m,'V2_GENUINE_RESIDUAL')]['success'] for m in ('A','B'))
    protocol={'budget':BUDGET,'languages':['A','B'],
      'channels':['V0_BINARY','V1_LOCALIZED','V2_GENUINE_RESIDUAL','V3_SCRUBBED_INTERVENTION','V4_PERMUTED_INTERVENTION'],
      'cells':rows,
      'sealed_success_visible_to_policy':False,
      'interpretation':'Main effects: dose and meta-language. Interaction: whether dependencies are distinct. Scrubbed/permuted are do-style linkage interventions; held-out success is evaluated only after selection.',
      'status':'HARNESS_ONLY_NOT_FROZEN_RESULT'}
    encoded=json.dumps(protocol,sort_keys=True,separators=(',',':'))
    print(encoded)
    print('PROTOCOL_SHA256='+sha256(encoded.encode()).hexdigest())
    print('SEALED_SUCCESS_LEAKAGE_AUDIT=PASS')

if __name__=='__main__':main()
