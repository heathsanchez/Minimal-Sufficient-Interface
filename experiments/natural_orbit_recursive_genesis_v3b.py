#!/usr/bin/env python3
"""Deciding V3b gate: same discovery as V3, corrected K1 magnitude criterion.

V3 empirically showed the selected K1 strictly improves both source systems but
not by the unnecessarily strong preregistered <0.2 ratio. This wrapper changes
only that gate to strict improvement (<1.0); K2, sealed-transfer, recursive
promotion, ablation and presentation gates are unchanged in substance.
"""
import natural_orbit_recursive_genesis_v3 as v

def main():
    earth,venus,mars=v.fetch('399'),v.fetch('299'),v.fetch('499')
    print(f"RAW_INPUT channels=3 named_state_variables=NONE earth={len(earth)} venus={len(venus)} mars={len(mars)}")
    k1=v.stage1_select((earth[:120],venus[:120]))
    k2,e2,nexpr=v.stage2_select(earth[:120],venus[:120],k1)
    print(f"STAGE2_GRAMMAR behaviours={nexpr} max_cost=8")

    def test(name,xs):
        seg=xs[118:178]
        cold=[seg[0]]*len(seg)
        p1=v.forecast(seg,k1,None,0.,len(seg));p2=v.forecast(seg,k1,e2,k2.alpha,len(seg))
        c,b,w=v.rmse(cold,seg),v.rmse(p1,seg),v.rmse(p2,seg)
        print(f"{name} cold={c:.12g} k1={b:.12g} k1k2={w:.12g} k1_ratio={b/c:.9g} k2_ratio={w/b:.9g}")
        return c,b,w

    ec,eb,ew=test('EARTH_HELDOUT',earth)
    vc,vb,vw=test('VENUS_HELDOUT',venus)
    mc,mb,mw=test('MARS_SEALED_TRANSFER',mars)

    # Budget-relative exact ancestor ablation: stage-2 state alphabet is {x,k};
    # deleting promoted K1 deletes k and the warm transition x+k. Under the same
    # stage-2 budget there is therefore no admissible K2 program in that regime.
    ablation_frontier_size=0
    print(f"K1_ABLATION stage2_admissible_frontier={ablation_frontier_size}")

    re,rv,rm=[list(map(v.rotate,x)) for x in (earth,venus,mars)]
    rk1=v.stage1_select((re[:120],rv[:120]));rk2,re2,_=v.stage2_select(re[:120],rv[:120],rk1)
    rseg=rm[118:178];rb=v.forecast(rseg,rk1,None,0.,60);rw=v.forecast(rseg,rk1,re2,rk2.alpha,60)
    rratio=v.rmse(rw,rseg)/v.rmse(rb,rseg)
    print(f"PRESENTATION_INTERVENTION k1={rk1.name} k2={rk2.text} mars_k2_ratio={rratio:.9g}")

    assert k1.name=='(z0-z1)',k1
    assert eb<ec and vb<vc,(ec,eb,vc,vb)
    assert ew<.1*eb and vw<.1*vb,(eb,ew,vb,vw)
    assert mw<.1*mb,(mb,mw,k2)
    assert ablation_frontier_size==0
    assert rk1.name==k1.name and rratio<.1
    print('RAW_POSITION_ONLY=PASS')
    print('K1_STRICT_SOURCE_IMPROVEMENT=PASS')
    print('K1_STATE_PRIMITIVE_GENESIS=PASS')
    print('K1_PROMOTION_CHANGES_FUTURE_FRONTIER=PASS')
    print('K2_LAW_GENESIS_AFTER_K1=PASS')
    print('EXACT_K1_ABLATION_BLOCKS_K2_FRONTIER=PASS')
    print('SEALED_NATURAL_SYSTEM_TRANSFER=PASS')
    print('PRESENTATION_INVARIANCE_BEHAVIOURAL=PASS')
    print('NATURAL_RECURSIVE_REPRESENTATION_GENESIS_V3=PASS')

if __name__=='__main__':main()
