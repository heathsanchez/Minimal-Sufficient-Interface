"""Symbolic certificate for the saturated arbitrary-n phase theorem.

This does not enumerate saturated states. It proves the equivalence by local algebra on
one index and its color, using only:
  * row0(i)=i;
  * the A/B/C saturated row reconstruction;
  * sigma_c maps each color block to itself;
  * shifted(t,u): r_u(i) != r_t(i+u-t).

For every pair-family violation we derive one forbidden phase displacement; conversely
every forbidden displacement constructs a violation of one named pair family.
"""
from __future__ import annotations
import json
from pathlib import Path

PAIRS=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
FORBIDDEN={
    'A':{1,2,3},
    'B':{1,3,-1},
    'C':{1,2,-2,-1},
}

# A symbolic row expression at a point of known color.
# 'id' means x, 'sig' means sigma(x).
ROW_EXPR={
    'A':('id','id','sig','sig'),
    'B':('id','sig','id','sig'),
    'C':('id','sig','sig','id'),
}

# Direct forbidden-atom -> violating pair witnesses.
# same: test shifted pair at i=x.
# image: test at i=sigma(x), using block closure.
WITNESSES={
    ('A',1):((1,2),'same'),
    ('A',2):((0,2),'same'),
    ('A',3):((0,3),'same'),
    ('B',1):((0,1),'same'),
    ('B',3):((0,3),'same'),
    ('B',-1):((1,2),'image'),
    ('C',1):((0,1),'same'),
    ('C',2):((0,2),'same'),
    ('C',-2):((1,3),'image'),
    ('C',-1):((2,3),'image'),
}


def mod_eq(a,b,n):
    return (a-b)%n==0


def direct_witness_holds(color,d,pair,mode,n):
    """Check the witness algebra for generic representatives x=0, sigma(x)=d mod n.

    This is not state enumeration: the expressions contain only x and sigma(x), and
    translation invariance lets us normalize x=0.
    """
    t,u=pair; delta=u-t; x=0; sx=d%n
    if mode=='same':
        i=x
        # Evaluate r_u(x) using color of x.
        left = x if ROW_EXPR[color][u]=='id' else sx
        j=(i+delta)%n
        # The intended direct witnesses have j=sigma(x), hence same color by closure,
        # or t=0 where row0(j)=j independent of color.
        if t==0:
            right=j
        else:
            assert j==sx, (color,d,pair,mode,n,j,sx)
            right = sx if ROW_EXPR[color][t]=='id' else None
            # For these witnesses the t-row at sigma(x) is identity on the block.
            assert right is not None
        return left==right
    else:
        i=sx
        j=(i+delta)%n
        assert j==x, (color,d,pair,mode,n,j,x)
        # sigma(x) lies in same block; in image witnesses row u is identity there.
        left = sx if ROW_EXPR[color][u]=='id' else None
        assert left is not None
        # j=x; row t(x) is sigma(x) in image witnesses.
        right = sx if ROW_EXPR[color][t]=='sig' else None
        assert right is not None
        return left==right


def violation_implies_forbidden(color,t,u,case):
    """Return the displacement forced by a pair violation in a local color case.

    case says whether the left index i or shifted index j=i+delta supplies the
    non-identity sigma expression. Cases that compare two independent sigma values
    cannot occur in the saturated same-color local reduction without injectivity;
    the complete table below is obtained directly from ROW_EXPR and block closure.
    """
    delta=u-t
    # For a violation r_u(i)=r_t(j), j=i+delta.
    # If left is sigma(i), right is j (identity), d=+delta.
    # If left is i (identity), right is sigma(j), sigma(j)=i=j-delta, so d=-delta.
    if case=='left-sigma/right-id': return delta
    if case=='left-id/right-sigma': return -delta
    raise ValueError(case)


def symbolic_pair_table():
    """For each shifted pair, list exactly which color-phase atoms it can forbid.

    On a color block, a row coordinate is either identity or sigma. A pair constraint
    only creates a unary phase restriction when one side is sigma and the other is
    identity. Equal identity/identity is impossible because delta != 0; sigma/sigma
    reduces by injectivity to the same impossibility. Thus the two mixed cases are
    complete.
    """
    table={}
    for t,u in PAIRS:
        atoms=[]; delta=u-t
        for c in ('A','B','C'):
            le=ROW_EXPR[c][u]; re=ROW_EXPR[c][t]
            if le=='sig' and re=='id': atoms.append((c,delta))
            elif le=='id' and re=='sig': atoms.append((c,-delta))
        table[f'{t}{u}']=atoms
    return table


def main():
    pair_table=symbolic_pair_table()
    union={(c,d) for atoms in pair_table.values() for c,d in atoms}
    expected={(c,d) for c,ds in FORBIDDEN.items() for d in ds}
    assert union==expected, (union,expected,pair_table)

    # Independently check every constructive witness for a range of moduli where
    # signed residues may collide. This validates modular normalization only; the
    # theorem argument itself is the symbolic table above.
    witness_checks={}
    for n in range(3,33):
        ok=True
        for atom,(pair,mode) in WITNESSES.items():
            c,d=atom
            # If d=0 mod n it cannot be a derangement phase atom and is vacuous.
            if d%n==0: continue
            ok &= direct_witness_holds(c,d,pair,mode,n)
        witness_checks[str(n)]=bool(ok)
        assert ok, n

    # Verify the pair-table forbidden formula modulo n against the previously
    # exhaustive orders 3..8 when that artifact is available.
    cross_path=Path('artifacts/phase_cross_order_generalization_probe.json')
    finite_replay={}
    if cross_path.exists():
        cross=json.load(open(cross_path))
        for row in cross['orders']:
            n=row['n']
            predicted={(c,d%n) for c,ds in FORBIDDEN.items() for d in ds if d%n!=0}
            observed={tuple(x) for x in row['forbidden_atoms']}
            finite_replay[str(n)]={'predicted':sorted([list(x) for x in predicted]),'observed':sorted([list(x) for x in observed]),'match':predicted==observed}
            assert predicted==observed, (n,predicted,observed)

    out={
        'theorem':('For any cyclic order n, on a saturated partition-derangement state, all six shifted row-pair inequalities hold iff '
                   'every A-phase avoids {+1,+2,+3}, every B-phase avoids {+1,+3,-1}, and every C-phase avoids {+1,+2,-2,-1}, interpreted modulo n; zero residues are vacuous because each sigma is fixed-point-free.'),
        'assumptions':['cyclic indices mod n','saturated A/B/C row reconstruction','each sigma_c is a fixed-point-free permutation of its color block'],
        'pair_table':{k:[[c,d] for c,d in v] for k,v in pair_table.items()},
        'forbidden_union':sorted([[c,d] for c,d in expected]),
        'constructive_witnesses':{f'{c}:{d}':{'pair':list(pair),'mode':mode} for (c,d),(pair,mode) in WITNESSES.items()},
        'witness_moduli_checked':[3,32],
        'finite_replay_orders_3_to_8':finite_replay,
        'symbolic_complete':True,
        'residual':'Use the arbitrary-n phase theorem to replace all six shifted constraints on the saturated frontier by local displacement avoidance, then test whether this collapses the remaining E677 frontier enough to derive the next structural obstruction toward E255.'
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_symbolic_theorem_certificate.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'theorem':out['theorem'],'pair_table':out['pair_table'],'symbolic_complete':True,'residual':out['residual']},indent=2,sort_keys=True))
    print('PHASE_SYMBOLIC_THEOREM_CERTIFICATE_PASS')

if __name__=='__main__': main()
