"""Bounded, source-blind feedback development over replayable observations.

Every trial is an actual interaction. A witnessed path becomes a reusable
operation only after fresh replay. Equal observations are not assumed to be
interchangeable: conflicting outcomes retain their separate histories.
"""
from collections import deque, defaultdict
from hashlib import sha256
import json


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def atom(value):
    return tuple(value) if isinstance(value, list) else value


def observe(frame):
    if isinstance(frame, dict):
        return {k: frame[k] for k in ('frame', 'levels_completed', 'state', 'available_actions') if k in frame}
    state = getattr(frame.state, 'name', str(frame.state))
    return {'frame': [x.tolist() if hasattr(x, 'tolist') else x for x in frame.frame],
            'levels_completed': int(frame.levels_completed), 'state': state,
            'available_actions': list(getattr(frame, 'available_actions', []))}


def terminal(obs):
    return obs['state'] in ('WIN', 'GAME_OVER')


class FeedbackArchive:
    """Evidence, replayable operations, and a reversible observed-state index."""
    def __init__(self):
        self.rows = []
        self.paths = {}
        self.edges = defaultdict(set)
        self.conflicts = set()
        self.options = []
        self.best = None

    def retain(self, path, before, action, after):
        path = tuple(path)
        a = atom(action)
        source, target = digest(before), digest(after)
        key = (source, a)
        self.edges[key].add(target)
        if len(self.edges[key]) > 1:
            self.conflicts.add(key)
        row = {'path': path, 'source': source, 'action': a, 'target': target,
               'progress': after['levels_completed'] - before['levels_completed'],
               'state': after['state']}
        self.rows.append(row)
        next_path = path + (a,)
        # Paths are witnesses, not global state-equivalence assertions.
        if target not in self.paths or len(next_path) < len(self.paths[target]):
            self.paths[target] = next_path
        if self.best is None or (after['state'] == 'WIN', after['levels_completed'], -len(next_path)) > self.best[0]:
            self.best = ((after['state'] == 'WIN', after['levels_completed'], -len(next_path)), next_path, target)
        return row

    def install(self, entry, program, target, proof):
        if (proof['status'] != 'OBSERVED' or proof['final_sha256'] != target
                or len(proof['observations']) <= len(program)
                or digest(proof['observations'][-len(program)-1]) != entry):
            raise ValueError('Unverified operation')
        item = {'entry_sha256': entry, 'program': tuple(program),
                'target_sha256': target, 'proof_sha256': digest(proof['observations'])}
        if item not in self.options:
            self.options.append(item)
        return item

    def snapshot(self):
        return {'transitions': len(self.rows), 'observed_states': len(self.paths),
                'conflicts': len(self.conflicts), 'options': len(self.options), 'installed_options': self.options,
                'best_prefix': self.best[1] if self.best else (),
                'evidence_sha256': digest(self.rows)}


def replay(factory, path, expected, budget):
    """An accepted operation is checked on a fresh instance before reuse."""
    env = factory()
    frame = env.observation_space
    if frame is None:
        frame = env.reset()
    initial = observe(frame)
    executed = []
    observations = [initial]
    status = 'OBSERVED'
    try:
        for action in tuple(path):
            if len(executed) >= budget:
                status = 'BUDGET_EXHAUSTED'; break
            if terminal(observe(frame)):
                status = 'PREFIX_TERMINATED'; break
            frame = env.step(action)
            if frame is None:
                raise RuntimeError('Missing external observation')
            executed.append(action)
            observations.append(observe(frame))
        final = observations[-1]
        if status == 'OBSERVED' and expected is not None and digest(final) != expected:
            status = 'INCONCLUSIVE_PREFIX_MISMATCH'
        return {'status': status, 'initial_sha256': digest(initial),
                'final_sha256': digest(final), 'executed': tuple(executed),
                'observations': observations, 'actions': len(executed),
                'levels_completed': final['levels_completed'], 'state': final['state']}
    finally:
        close = getattr(env, 'close', None)
        if callable(close): close()


def develop(factory, actions, prefix=(), checkpoint=None, budget=120,
            max_training_actions=10000, max_episodes=512, max_depth=32,
            seed_programs=(), feedback=True):
    """Try, observe, retain, change the next search, and repeat.

    A new observation creates a replayable frontier. Known observations are
    only scheduling hints; no action or history is globally declared useless.
    The finite grammar contains primitives and repetitions of witnessed options.
    """
    if not actions or budget < 1 or max_depth < 1 or max_training_actions < 1 or max_episodes < 1:
        raise ValueError('Positive bounds and nonempty actions required')
    actions = tuple(dict.fromkeys(map(atom, actions)))
    prefix = tuple(map(atom, prefix))
    archive = FeedbackArchive()
    spent = episodes = 0
    if len(prefix) > min(budget, max_training_actions):
        return {'status': 'DEPLOYMENT_BOUND_EXHAUSTED', 'training_actions': 0, 'training_episodes': 0, 'development': archive.snapshot()}
    first = replay(factory, prefix, checkpoint, budget)
    spent += first['actions']; episodes += 1
    initial = first['initial_sha256']
    if first['status'] != 'OBSERVED':
        return {'status': first['status'], 'training_actions': spent, 'training_episodes': episodes,
                'development': archive.snapshot()}
    start = first['observations'][-1]
    if start['state'] == 'WIN':
        return {'status': 'VERIFIED_WIN', 'training_actions': spent,
                'training_episodes': episodes, 'development': archive.snapshot(), 'result': first}
    if terminal(start):
        return {'status': 'TERMINAL_WITHOUT_WIN', 'training_actions': spent,
                'training_episodes': episodes, 'development': archive.snapshot(), 'result': first}
    start_key = digest(start)
    archive.paths[start_key] = prefix
    archive.best = ((start['state'] == 'WIN', start['levels_completed'], -len(prefix)), prefix, start_key)
    queue = deque([(prefix, start_key, 0)])
    seed_programs = tuple(tuple(map(atom, p)) for p in seed_programs if p)
    action_stats = defaultdict(lambda: [0, 0, 0])
    pending = {prefix}
    observed = set()
    while queue and spent < max_training_actions and episodes < max_episodes:
        path, expected, depth = queue.popleft()
        pending.discard(path)
        if depth >= max_depth or len(path) >= budget:
            continue
        # Reuse is conditional on the exact witnessed checkpoint.
        if path == prefix and episodes == 1:
            r = first
        else:
            if spent + len(path) > max_training_actions or episodes >= max_episodes:
                break
            r = replay(factory, path, expected, budget)
            spent += r['actions']; episodes += 1
        if r['initial_sha256'] != initial or r['status'] in ('INCONCLUSIVE_PREFIX_MISMATCH', 'PREFIX_TERMINATED'):
            return {'status': 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX', 'training_actions': spent,
                    'training_episodes': episodes, 'development': archive.snapshot()}
        if r['status'] == 'BUDGET_EXHAUSTED':
            break
        before = r['observations'][-1]
        if terminal(before):
            continue
        # Consequences change the next candidate ordering. No action is deleted.
        candidates = list(actions)
        if feedback:
            candidates.sort(key=lambda a: (-action_stats[a][1], -action_stats[a][2],
                                            action_stats[a][0], actions.index(a)))
            candidates = [o['program'] for o in archive.options] + list(seed_programs) + candidates
        for candidate in dict.fromkeys(candidates):
            program = (candidate,) if candidate in actions else tuple(candidate)
            if not program or len(path)+len(program) > budget or depth+len(program) > max_depth:
                continue
            if spent+len(path)+len(program) > max_training_actions or episodes >= max_episodes:
                break
            trial = replay(factory, path+program, None, budget)
            spent += trial['actions']; episodes += 1
            if trial['initial_sha256'] != initial or trial['status'] != 'OBSERVED':
                return {'status': 'INCONCLUSIVE_UNMATCHED_START_OR_PREFIX', 'training_actions': spent,
                        'training_episodes': episodes, 'development': archive.snapshot()}
            if digest(trial['observations'][len(path)]) != expected:
                return {'status': 'INCONCLUSIVE_PREFIX_MISMATCH', 'training_actions': spent,
                        'training_episodes': episodes, 'development': archive.snapshot()}
            for i, action in enumerate(program):
                b = trial['observations'][len(path)+i]
                a = trial['observations'][len(path)+i+1]
                novel = digest(a) not in archive.paths
                row = archive.retain(path+program[:i], b, action, a)
                action_stats[action][0] += 1
                action_stats[action][1] += max(0, row['progress'])
                action_stats[action][2] += int(novel)
                next_path = path+program[:i+1]
                if row['progress'] > 0 or a['state'] == 'WIN':
                    # A witnessed result is not installed until fresh replay.
                    if spent+len(next_path) <= max_training_actions and episodes < max_episodes:
                        proof = replay(factory, next_path, digest(a), budget)
                        spent += proof['actions']; episodes += 1
                        if proof['initial_sha256'] != initial or proof['status'] != 'OBSERVED':
                            return {'status': 'INCONCLUSIVE_REPLAY', 'training_actions': spent,
                                    'training_episodes': episodes, 'development': archive.snapshot()}
                        archive.install(expected, program[:i+1], digest(a), proof)
                        if a['state'] == 'WIN':
                            return {'status': 'VERIFIED_WIN', 'training_actions': spent,
                                    'training_episodes': episodes, 'development': archive.snapshot(), 'result': proof}
                if not terminal(a) and depth+i+1 < max_depth and next_path not in pending and next_path not in observed:
                    # Only scheduling changes; equal observations are not global state laws.
                    if feedback and novel:
                        queue.appendleft((next_path, row['target'], depth+i+1))
                    else:
                        queue.append((next_path, row['target'], depth+i+1))
                    pending.add(next_path)
            observed.add(path)
    return {'status': 'TRAINING_BOUND_EXHAUSTED' if spent >= max_training_actions or episodes >= max_episodes else 'NO_TERMINAL_WITHIN_BOUND', 'training_actions': spent,
            'training_episodes': episodes, 'development': archive.snapshot()}
