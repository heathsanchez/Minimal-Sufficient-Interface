"""Source-backed abstract clean Good-row renewal-cycle probe.

This is a local equality/Latin-injectivity discriminator, not a finite magma
model finder.  It expands the actual cells in the Good-row renewal lemma for
maximal Bad blocks of length one, inserts canonical self-fixer cells for Good
labels, closes A/B renewal cycles, and asks whether the resulting known-cell
constraints are consistent.

If a word is SAT, the local renewal+fixer vocabulary is insufficient and the
witness is the next residual.  If all words are UNSAT, the recurring conflict
is a candidate invariant, not yet a global E677 theorem.
"""
from __future__ import annotations
import json
from itertools import product
from pathlib import Path

try:
    from z3 import Int, Solver, Implies, Or, sat
except ImportError as e:
    raise SystemExit("z3-solver required") from e

MAX_CYCLE = 8


def fresh(role, i):
    return Int(f"{role}_{i}")


def solve_word(word: str):
    n=len(word)
    s=Solver()
    # Source E crossings e_i=(r_i,g_i,b_i), with r,g Good and b Bad.
    r=[fresh('r',i) for i in range(n)]
    g=[fresh('g',i) for i in range(n)]
    b=[fresh('b',i) for i in range(n)]
    z=[fresh('z',i) for i in range(n)]
    h=[fresh('h',i) for i in range(n)]
    w=[fresh('w',i) for i in range(n)]
    q=[fresh('q',i) for i in range(n)]

    good=[]; bad=[]; cells=[]
    for i in range(n):
        good += [r[i],g[i],z[i],h[i]]
        bad += [b[i]]
        # length-one maximal Bad block: r*g=b=x and r*b=z
        cells += [(r[i],g[i],b[i],f'entry[{i}]'),
                  (r[i],b[i],z[i],f'exit[{i}]')]
        # h=(r*b)*r and b*h=g.  With length one r*b=z.
        cells += [(z[i],r[i],h[i],f'hinge[{i}]'),
                  (b[i],h[i],g[i],f'entry_companion[{i}]')]
        # w=r*z; q=w*r; z*q=x=b for length one.
        cells += [(r[i],z[i],w[i],f'w[{i}]'),
                  (w[i],r[i],q[i],f'q[{i}]'),
                  (z[i],q[i],b[i],f'exit_companion[{i}]')]
        if word[i]=='A':
            good += [q[i]]
            # next E crossing is (z,q,x=b)
            j=(i+1)%n
            s.add(r[j]==z[i], g[j]==q[i], b[j]==b[i])
        else:
            # B: q bad and w good; next E crossing (w,r,q)
            bad += [q[i]]; good += [w[i]]
            j=(i+1)%n
            s.add(r[j]==w[i], g[j]==r[i], b[j]==q[i])

    # Colour separation.  We do not assert distinctness within a colour.
    for x in good:
        for y in bad:
            s.add(x != y)

    # Canonical unique fixer consequence for every known Good label:
    # Good u means u*u=u.  Column-Latin injectivity then makes this the unique
    # known row that can map input u to output u; generic injectivity below
    # enforces that whenever another known cell tries to do so.
    unique_good=[]
    for x in good:
        if str(x) not in {str(y) for y in unique_good}:
            unique_good.append(x)
            cells.append((x,x,x,f'good_self[{x}]'))

    # Bad labels are not Good: D(x)=x*x != x.  Introduce their diagonal output.
    for k,x in enumerate(bad):
        dx=fresh('D_bad',k)
        s.add(dx != x)
        cells.append((x,x,dx,f'bad_diag[{k}]'))

    # Consequences of a Latin multiplication restricted to known cells:
    # functionality, row injectivity, and column injectivity.
    for a in range(len(cells)):
        ra,ca,oa,_=cells[a]
        for bb in range(a+1,len(cells)):
            rb,cb,ob,_=cells[bb]
            s.add(Implies((ra==rb) & (ca==cb), oa==ob))
            s.add(Implies((ra==rb) & (oa==ob), ca==cb))
            s.add(Implies((ca==cb) & (oa==ob), ra==rb))

    result=s.check()
    if result==sat:
        m=s.model()
        names={}
        for role,arr in [('r',r),('g',g),('b',b),('z',z),('h',h),('w',w),('q',q)]:
            names[role]=[m.eval(v,model_completion=True).as_long() for v in arr]
        # Canonicalize arbitrary integers to equality-class IDs.
        vals=[]
        for arr in names.values(): vals.extend(arr)
        canon={v:i for i,v in enumerate(dict.fromkeys(vals))}
        witness={k:[canon[v] for v in arr] for k,arr in names.items()}
        return True,witness,len(cells)
    return False,None,len(cells)


def main():
    frontier=json.load(open('program_frontier.json'))
    assert frontier['authoritative'] is True
    assert frontier['live_residual']['type']=='REFRAME'
    results=[]; survivors=[]
    for n in range(1,MAX_CYCLE+1):
        for bits in product('AB', repeat=n):
            word=''.join(bits)
            ok,wit,ncells=solve_word(word)
            rec={'length':n,'word':word,'sat':ok,'known_cells':ncells}
            if ok:
                rec['witness']=wit
                survivors.append(rec)
            results.append(rec)
    shortest=min((x['length'] for x in survivors), default=None)
    # Keep artifact compact: all aggregate counts + shortest survivors only.
    shortest_survivors=[x for x in survivors if x['length']==shortest][:16] if shortest else []
    classification='REQUIRE_ATTACHMENT' if survivors else 'REFRAME'
    residual=(
        f"Length-one clean Good-row renewal cycles survive the local source-backed cell, colour, canonical Good-fixer, and known-cell Latin constraints; shortest length={shortest}. Join the surviving equality pattern with the Bad-row renewal or add the exact omitted global E677 constraint, rather than deepening this local vocabulary."
        if survivors else
        f"All A/B clean Good-row renewal words of lengths 1..{MAX_CYCLE} are inconsistent when every maximal Bad block has length one under the source-backed cells, colours, canonical Good fixers, and known-cell Latin constraints. Minimize the recurring contradiction and test whether it extends to arbitrary block length before promotion."
    )
    artifact={
      'probe':'good_row_clean_cycle_length1_local_latin',
      'source_commit':'5a205195a84eec54dbcb2fd766f0b2d1ded1831b',
      'source_lemma':'lemmas/e677_good_row_bad_block_renewal_and_bad_target_collision_handoff.md',
      'scope':'Good-row R_G cycles only; every maximal Bad block length exactly 1; known-cell Latin consequences only; not a full magma model and not E677 -> E255',
      'max_cycle_length':MAX_CYCLE,
      'words_tested':len(results),
      'sat_words':len(survivors),
      'unsat_words':len(results)-len(survivors),
      'shortest_sat_length':shortest,
      'shortest_survivors':shortest_survivors,
      'consumed_frontier':{
        'schema_version':frontier['schema_version'],
        'live_state_parent_sha':frontier['live_state_parent_sha'],
        'live_residual':frontier['live_residual']
      },
      'proposed_transition':{
        'classification':classification,
        'scope':'length-one Good-row clean-cycle local consistency discriminator',
        'residual':residual
      },
      'global_claimed':False
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/good_row_clean_cycle_probe.json').write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:artifact[k] for k in ['words_tested','sat_words','unsat_words','shortest_sat_length']},indent=2))
    print('CYCLE_TRANSITION='+classification)
    print('CYCLE_RESIDUAL='+residual)
    print('GOOD_ROW_CLEAN_CYCLE_LOCAL_PROBE_PASS')

if __name__=='__main__': main()
