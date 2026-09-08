"""Evidence-driven recovery of earlier ARC3 progress.

Historical witnesses are proposals, not installed capabilities. The existing
continuation replays and Lean-checks them before retention. The remaining
search uses the frozen ranked controller and retains the complete alphabet.
No game-specific rule or winning sequence is encoded here.
"""
import argparse
import hashlib
import json
from pathlib import Path

import arc3_shared_continuation as C
import arc3_shared_transfer as T

SOURCE_SHA256 = 'bf8a69009a641fe20d02ee495a2a7ddef76ee1fc88ab42e766ccfe9e333bea99'
SOURCE_RUN = 34192005884
SOURCE_ARTIFACT = 10042541326
SOURCE_COMMIT = 'c65201683d0eccd8a03e07abb9ba35409419cf14'


def load_witnesses(path, game, initial_sha, actions):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Historical evidence bytes do not match the pinned artifact')
    r = json.loads(raw)
    d = r['policies']['ranked-factor-v1']['development']
    if (r['status'] != 'COMPARABLE' or r['game'] != game
            or r['initial_sha256'] != initial_sha
            or d['initial_sha256'] != initial_sha
            or r['selected_policy'] != 'ranked-factor-v1'
            or r['model_calls'] != 0 or r['competition_submission']):
        raise ValueError('Historical evidence provenance mismatch')
    permitted = set(actions)
    previous = ()
    levels = 0
    witnesses = []
    for stage in d['stages']:
        prefix = C.atoms(stage['prefix'])
        suffix = C.atoms(stage['suffix'])
        if (not suffix or prefix != previous+suffix
                or stage['level'] <= levels or stage['actions'] != len(prefix)
                or any(a not in permitted for a in suffix)):
            raise ValueError('Historical witness is malformed or outside the action grammar')
        witnesses.append(prefix)
        previous, levels = prefix, stage['level']
    if previous != C.atoms(d['prefix']) or levels != d['levels_witnessed']:
        raise ValueError('Historical development does not match its witnesses')
    return tuple(witnesses)


def make_search_class(witnesses, ranked_class, factor_fn):
    """Prioritize replay candidates from the current entry, then rank fairly."""
    class EvidenceSearch(ranked_class):
        def __init__(self, actions, options=(), max_depth=32):
            options = tuple(C.atoms(o) for o in options)
            entry = tuple(a for o in options for a in o)
            extra = tuple(f for o in options for f in factor_fn(o, max_depth))
            expanded = tuple(dict.fromkeys(options+extra))
            super().__init__(actions, expanded, max_depth=max_depth)
            self.recovery_candidates = []
            for witness in witnesses:
                if witness[:len(entry)] == entry:
                    suffix = witness[len(entry):]
                    if 0 < len(suffix) <= max_depth and all(a in self.rank for a in suffix):
                        self.recovery_candidates.append(suffix)
                        self._add(suffix, -1)
    return EvidenceSearch


def run(factory, actions, source, game, identity, historical_path, output,
        ranked_class, factor_fn, execute_stage, max_training_actions=3000,
        max_episodes=512, max_depth=32, max_levels=5, gate=T.run_lean_gate):
    witnesses = load_witnesses(historical_path, game, source['initial_sha256'], actions)
    search = make_search_class(witnesses, ranked_class, factor_fn)
    r = C.continue_run(factory, actions, source, game, identity, output,
                       max_training_actions=max_training_actions,
                       max_episodes=max_episodes, max_depth=max_depth,
                       max_levels=max_levels, search_class=search,
                       execute_stage=execute_stage, gate=gate)
    r['search_policy'] = 'archived-witnesses-then-ranked-v1'
    r['historical_evidence'] = {'run_id':SOURCE_RUN,'artifact_id':SOURCE_ARTIFACT,
        'source_commit':SOURCE_COMMIT,'sha256':SOURCE_SHA256,
        'candidate_prefix_lengths':[len(w) for w in witnesses]}
    return r


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--frozen-dir',required=True)
    p.add_argument('--environments-dir',required=True)
    p.add_argument('--game',required=True)
    p.add_argument('--source',required=True)
    p.add_argument('--source-identity',required=True)
    p.add_argument('--historical-evidence',required=True)
    p.add_argument('--output',default='arc3-shared-recovery.json')
    p.add_argument('--max-training-actions',type=int,default=3000)
    p.add_argument('--max-episodes',type=int,default=512)
    p.add_argument('--max-depth',type=int,default=32)
    p.add_argument('--max-levels',type=int,default=5)
    a=p.parse_args()
    _,_,grounding,_,multilevel=T.load_frozen(a.frozen_dir)
    from consequence_search import RankedSearch, factors
    from arc_agi import Arcade,OperationMode
    import logging
    logger=logging.getLogger('arc3-shared-recovery')
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    def factory():
        arcade=Arcade(operation_mode=OperationMode.OFFLINE,
                      environments_dir=a.environments_dir,logger=logger)
        env=arcade.make(a.game)
        if env is None:raise RuntimeError('Environment unavailable')
        class Adapter:
            @property
            def observation_space(self):return env.observation_space
            @property
            def action_space(self):return env.action_space
            def reset(self):return env.reset()
            def step(self,action):
                kind,data=grounding.decode(action)
                return env.step(kind,data=data)
            def close(self):return arcade.close_scorecard()
        return Adapter()
    first=factory()
    actions,unsupported=grounding.action_catalog(first.action_space,first.observation_space,8,256)
    first.close()
    source=json.loads(Path(a.source).read_text())
    r=run(factory,actions,source,a.game,a.source_identity,a.historical_evidence,
          Path(a.output).parent/'shared-recovery-gate',RankedSearch,factors,
          multilevel.execute_stage,max_training_actions=a.max_training_actions,
          max_episodes=a.max_episodes,max_depth=a.max_depth,max_levels=a.max_levels)
    r.update(mode='offline',unsupported_action_ids=unsupported)
    Path(a.output).write_text(json.dumps(r,indent=2,sort_keys=True,default=str)+'\n')
    print('ARC3_SHARED_RECOVERY='+json.dumps({k:r.get(k) for k in
          ('status','training_actions','training_episodes','grounded_actions','terminal_win')},sort_keys=True))
    print('CERTIFIED_STAGES='+str(len(r['stages'])))

if __name__=='__main__':main()
