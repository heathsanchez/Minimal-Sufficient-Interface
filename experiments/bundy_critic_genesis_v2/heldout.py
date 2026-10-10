"""Protected, source-independent of the V2 synthesizer. No developer access pre-freeze.
All strings denote uninterpreted unary constructors / atomic variables.
"""

def fixtures(Atom, App, Goal):
    a = Atom
    def nest(x, *fs):
        for f in reversed(fs):
            x=App(f,x)
        return x
    g=[]
    # New function labels not present in development; nested lifts and chains.
    for i,fs in enumerate([('u',),('v','w'),('z','u','v'),('p','q','r','s')]):
        src=a(f'X{i}')
        tgt=a(f'Z{i}')
        mid=a(f'Y{i}')
        g.append(Goal(f'held_context_{i}',((src,mid),(mid,tgt)),nest(src,*fs),nest(tgt,*fs)))
    # Two different chains joined through lifted contexts; requires closure interleaving.
    a0,b0,c0,d0=(a(z) for z in ('aa0','bb0','cc0','dd0'))
    g.append(Goal('held_compose_through_context',
      ((a0,b0),(nest(b0,'U'),nest(c0,'U')),(c0,d0)),nest(a0,'U'),nest(d0,'U')))
    # Mixed function-depth premise must not invent cross-head equalities.
    g.append(Goal('held_nested_mixed',
      ((nest(a0,'R'),nest(b0,'R')),(b0,c0)),
      nest(a0,'L','R'),nest(b0,'L','R')))
    # Already solvable in old grammar: do not erase or regress it.
    g.append(Goal('held_old_protected',((a0,b0),(b0,c0),(c0,d0)),a0,d0))
    # Unrelated premises may be deleted without changing proof.
    g.append(Goal('held_irrelevant',( (a0,b0), (a('kk'),a('ll'))),nest(a0,'T'),nest(b0,'T')))
    # Genuinely refutable negatives under freely interpreted functions.
    g.append(Goal('held_bad_different_heads',((a0,b0),),nest(a0,'F'),nest(b0,'G')))
    g.append(Goal('held_bad_missing_premise',((a0,b0),(a('foo'),a('bar'))),nest(a0,'F'),nest(c0,'F')))
    g.append(Goal('held_bad_noncongruent',((nest(a0,'N'),nest(b0,'M')),),nest(a0,'N'),nest(b0,'N')))
    return tuple(g)