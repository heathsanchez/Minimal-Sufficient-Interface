"""Attach the already-proved Bad no-fixer consequence to the one-mark FORK/G-CROSS shell.

This is a strict attachment ablation against e677_fork_gcross_ground_e677_probe.py.
The previous shell + all 121 named ground E677 instances was SAT. Before
changing representation, test the stronger existing source consequence:

    Bad(u) => no row r fixes u, i.e. r*u != u.

We can only instantiate that law on the named rows/Bad inputs of this partial
uninterpreted fragment. SAT remains only a local negative boundary; UNSAT
would show that the missing leverage was attachment rather than another mark.
"""
from __future__ import annotations

import json
from pathlib import Path
from itertools import product
from z3 import Solver, sat, unsat

from e677_fork_gcross_ground_e677_probe import C, BAD, names, mul, e677, structural_assertions


def add_named_no_fixers(s: Solver):
    # Upstream unique-fixer law: if u is Bad then no row fixes input u.
    # This partial probe instantiates it for every named row only.
    for r_name in names:
        row = C[r_name]
        for u in BAD:
            s.add(mul(row, u) != u)


def solve(*, add_e677: bool, add_no_fixers: bool):
    s=Solver()
    s.add(*structural_assertions(include_injectivity=True))
    if add_no_fixers:
        add_named_no_fixers(s)
    if add_e677:
        for a,b in product(names,names):
            s.add(e677(C[a],C[b]))
    return s.check(), s


def main():
    frontier=json.load(open('program_frontier.json'))
    assert frontier['authoritative']
    assert frontier['live_residual']['type']=='REFRAME'
    assert 'linked chain' in frontier['live_residual']['text']

    old_res,_=solve(add_e677=True,add_no_fixers=False)
    assert old_res==sat, 'must replay the previously verified single-mark SAT boundary'

    nofix_only,_=solve(add_e677=False,add_no_fixers=True)
    assert nofix_only==sat, 'no-fixer attachment must not make the structural shell inconsistent by itself'

    attached_res,_=solve(add_e677=True,add_no_fixers=True)

    if attached_res==unsat:
        classification='PROMOTE'
        residual=('Named instances of the proved Bad no-fixer law turn the previously SAT one-FORK/one-G-CROSS ground-E677 fragment UNSAT. '
                  'Minimize the required fixer inequalities and E677 instances, then derive a symbolic attachment lemma before adding a second mark.')
    else:
        classification='PARK'
        residual=('The one-FORK/one-G-CROSS fragment remains SAT even after attaching the proved no-Bad-fixer law on every named row and all named Bad inputs. '
                  'Single-mark locality is now exhausted under the current exact source consequences; proceed to the source-backed linked two-mark chain q -> H(q)=h.')

    out={
      'consumed_frontier_schema':frontier['schema_version'],
      'scope':'single FORK + one G-CROSS; named left-injectivity; 121 ground E677 instances; no-Bad-fixer instantiated on all named rows and named Bad inputs',
      'previous_single_mark_replay':str(old_res),
      'no_fixer_shell_only':str(nofix_only),
      'unique_fixer_attached_result':str(attached_res),
      'named_rows':len(names),
      'named_bad_inputs':len(BAD),
      'no_fixer_instance_count':len(names)*len(BAD),
      'ground_e677_pair_count':len(names)*len(names),
      'finite_magma_claimed':False,
      'counterexample_claimed':False,
      'global_e677_implication_claimed':False,
      'proposed_transition':{'classification':classification,'residual':residual}
    }
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_fork_gcross_unique_fixer_attachment_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    print('FORK_GCROSS_UNIQUE_FIXER_ATTACHMENT_VERIFIED')

if __name__=='__main__':
    main()
