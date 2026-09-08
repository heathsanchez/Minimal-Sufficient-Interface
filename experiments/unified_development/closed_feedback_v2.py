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
        self.histories = defaultdict(set)
        self.edges = defaultdict(set)
        self.conflicts = set()
        self.options = []
        self.best = None
        self.observed_best = None

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
        self.histories[target].add(next_path)
        # Paths are witnesses, not global state-equivalence assertions.
        if target not in self.paths or len(next_path) < len(self.paths[target]):
            self.paths[target] = next_path
        if self.observed_best is None or (after['state'] == 'WIN', after['levels_completed'], -len(next_path)) > self.observed_best[0]:
            self.observed_best = ((after['state'] == 'WIN', after['levels_completed'], -len(next_path)), next_path, target)
        return row

    def install(self, entry, program, target, proof, entry_path=(), source=None, dependencies=()):
        program = tuple(program)
        entry_path = tuple(entry_path)
        if not program:
            raise ValueError('Empty operation')
        if (proof['status'] not in ('OBSERVED', 'OBSERVED_TERMINAL_PREFIX') or proof['final_sha256'] != target
                or len(proof['observations']) <= len(program)
                or digest(proof['observations'][-len(program)-1]) != entry
                or tuple(proof['executed']) != tuple(entry_path) + tuple(program)
                or tuple(proof['executed'][-len(program):]) != tuple(program)):
            raise ValueError('Unverified operation')
        if any(not isinstance(i, int) or i < 0 or i >= len(self.options) for i in dependencies):
            raise ValueError('Unknown or forward dependency')
        if source and source[0] in ('option', 'repeat'):
            if len(dependencies) != 1 or source[1] != dependencies[0]:
                raise ValueError('Dependency identity mismatch')
            predecessor = self.options[dependencies[0]]['program']
            expected_program = predecessor if source[0] == 'option' else predecessor * source[2]
            if expected_program != program or (source[0] == 'repeat' and source[2] < 2):
                raise ValueError('Source expansion mismatch')
        item = {'entry_sha256': entry, 'entry_path': tuple(entry_path),
                'program': tuple(program), 'source': source,
                'dependencies': tuple(dependencies), 'initial_sha256': proof['initial_sha256'],
                'target_sha256': target, 'proof_sha256': digest(proof['observations'])}
        if item not in self.options:
            self.options.append(item)
        return item

    def snapshot(self):
        return {'transitions': len(self.rows), 'observed_states': len(self.paths),
                'conflicts': len(self.conflicts), 'options': len(self.options), 'installed_options': self.options,
                'best_prefix': self.best[1] if self.best else (),
                'evidence_sha256': digest(self.rows),
                'observed_best_prefix': self.observed_best[1] if self.observed_best else ()}


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
                status = 'OBSERVED_TERMINAL_PREFIX' if executed else 'PREFIX_TERMINATED'; break
            frame = env.step(action)
            if frame is None:
                raise RuntimeError('Missing external observation')
            executed.append(action)
            observations.append(observe(frame))
        final = observations[-1]
        if status in ('OBSERVED', 'OBSERVED_TERMINAL_PREFIX') and expected is not None and digest(final) != expected:
            status = 'INCONCLUSIVE_PREFIX_MISMATCH'
        return {'status': status, 'initial_sha256': digest(initial),
                'final_sha256': digest(final), 'executed': tuple(executed),
                'observations': observations, 'actions': len(executed),
                'requested': tuple(path), 'truncated': len(executed) != len(tuple(path)),
                'levels_completed': final['levels_completed'], 'state': final['state']}
    finally:
        close = getattr(env, 'close', None)
        if callable(close): close()


def repetition_counts(limit):
    """A complete bounded enumeration, with doubling tried first."""
    powers = []
    n = 2
    while n <= limit:
        powers.append(n)
        n *= 2
    return tuple(powers + [n for n in range(2, limit + 1) if n not in powers])


def candidates(actions, archive, seed_programs, remaining, max_depth, feedback=True):
    """Generate programs, not claims about their effects.

    A verified option is available as an operation. Using it at another
    entry is a new experiment, not an assumed state-equivalence law.
    """
    seen = set()
    def emit(program, source, dependencies=()):
        program = tuple(program)
        if not program or len(program) > min(remaining, max_depth) or program in seen:
            return None
        seen.add(program)
        return {'program': program, 'source': source, 'dependencies': dependencies}

    if feedback:
        for i, option in enumerate(archive.options):
            program = option['program']
            item = emit(program, ('option', i), (i,))
            if item is not None:
                yield item
            for n in repetition_counts(min(remaining, max_depth) // len(program)):
                item = emit(program * n, ('repeat', i, n), (i,))
                if item is not None:
                    yield item
    for program in seed_programs:
        item = emit(program, ('seed',), ())
        if item is not None:
            yield item
    for action in actions:
        item = emit((action,), ('atom', action), ())
        if item is not None:
            yield item


def develop(factory, actions, prefix=(), checkpoint=None, budget=120,
            max_training_actions=10000, max_episodes=512, max_depth=32,
            seed_programs=(), feedback=True):
    """Close the bounded loop: execute, verify, install, change next search.

    max_depth bounds expanded candidate suffixes; budget bounds deployment.
    The constructor vocabulary is fixed: atom, verified option, repetition,
    and sequential continuation. No observed effect is promoted globally.
    """
    if not actions or min(budget, max_training_actions, max_episodes, max_depth) < 1:
        raise ValueError('Positive bounds and nonempty actions required')
    actions = tuple(dict.fromkeys(map(atom, actions)))
    prefix = tuple(map(atom, prefix))
    seeds = tuple(tuple(map(atom, p)) for p in seed_programs if p)
    archive = FeedbackArchive()
    spent = episodes = 0
    attempts = set()
    pending_proofs = []
    if len(prefix) > min(budget, max_training_actions):
        return {'status': 'DEPLOYMENT_BOUND_EXHAUSTED', 'training_actions': 0,
                'training_episodes': 0, 'development': archive.snapshot()}

    def run(path, expected=None):
        nonlocal spent, episodes
        path = tuple(path)
        if episodes >= max_episodes or spent + len(path) > max_training_actions:
            return None
        result = replay(factory, path, expected, budget)
        spent += result['actions']
        episodes += 1
        return result

    def report(status, result=None):
        out = {'status': status, 'training_actions': spent,
               'training_episodes': episodes, 'development': archive.snapshot(),
               'attempts': len(attempts), 'pending_proofs': pending_proofs}
        if result is not None:
            out['result'] = result
        return out

    first = run(prefix, checkpoint)
    if first is None:
        return report('TRAINING_BOUND_EXHAUSTED')
    initial = first['initial_sha256']
    if first['status'] != 'OBSERVED':
        return report(first['status'])
    start = first['observations'][-1]
    start_key = digest(start)
    archive.paths[start_key] = prefix
    archive.histories[start_key].add(prefix)
    archive.best = ((start['state'] == 'WIN', start['levels_completed'], -len(prefix)), prefix, start_key)
    if prefix and digest(first['observations'][0]) != start_key:
        archive.install(digest(first['observations'][0]), prefix, start_key,
                        first, (), ('retained_prefix',), ())
    # A source prefix is an actual replayed history, not a bare score.
    # Preserve its observations and primitive transitions for future evidence.
    for i, action in enumerate(prefix):
        archive.retain(prefix[:i], first['observations'][i], action, first['observations'][i+1])
    if start['state'] == 'WIN':
        return report('VERIFIED_WIN', first)
    if terminal(start):
        return report('TERMINAL_WITHOUT_WIN', first)

    queue = deque([(prefix, start_key, 0)])
    queued = {prefix}
    exhausted = False
    while queue and not exhausted:
        if spent >= max_training_actions or episodes >= max_episodes:
            break
        path, expected, depth = queue.popleft()
        queued.discard(path)
        if depth >= max_depth or len(path) >= budget:
            continue
        remaining = min(max_depth - depth, budget - len(path))
        # Recheck the actual history; the observation hash is only a checkpoint.
        if path == prefix and episodes == 1:
            current = first
        else:
            current = run(path, expected)
            if current is None:
                exhausted = True; break
        if current['initial_sha256'] != initial or current['status'] != 'OBSERVED':
            return report('INCONCLUSIVE_UNMATCHED_START_OR_PREFIX')
        before = current['observations'][-1]
        if terminal(before):
            continue
        changed = False
        for candidate in candidates(actions, archive, seeds, remaining, max_depth, feedback):
            program = candidate['program']
            key = (path, program)
            if key in attempts:
                continue
            if episodes >= max_episodes or spent + len(path) + len(program) > max_training_actions:
                exhausted = True; break
            attempts.add(key)
            trial = run(path + program)
            if trial is None:
                exhausted = True; break
            if trial['initial_sha256'] != initial or trial['status'] not in ('OBSERVED', 'OBSERVED_TERMINAL_PREFIX'):
                return report('INCONCLUSIVE_UNMATCHED_START_OR_PREFIX')
            if digest(trial['observations'][len(path)]) != expected:
                return report('INCONCLUSIVE_PREFIX_MISMATCH')
            actual = tuple(trial['executed'][len(path):])
            if not actual:
                continue
            # Record the actual executed prefix, including a terminal-clipped
            # candidate. Each history remains distinct even if pixels agree.
            for i, action in enumerate(actual):
                b = trial['observations'][len(path)+i]
                a = trial['observations'][len(path)+i+1]
                archive.retain(path+actual[:i], b, action, a)
            after = trial['observations'][-1]
            target = digest(after)
            next_path = path + actual
            if target != expected:
                proof = run(next_path, target)
                if proof is None:
                    pending_proofs.append({'path': next_path, 'target_sha256': target})
                    exhausted = True; break
                if proof['initial_sha256'] != initial or proof['status'] != 'OBSERVED':
                    return report('INCONCLUSIVE_REPLAY')
                # Install the witnessed effect, never the unexecuted tail.
                archive.install(expected, actual, target, proof, path,
                                candidate['source'], candidate['dependencies'])
                quality = (after['state'] == 'WIN', after['levels_completed'], -len(next_path))
                if quality > archive.best[0]:
                    archive.best = (quality, next_path, target)
                if after['state'] == 'WIN':
                    return report('VERIFIED_WIN', proof)
                changed = True
            if not terminal(after) and depth + len(actual) < max_depth and next_path not in queued:
                if feedback and target != expected:
                    queue.appendleft((next_path, target, depth + len(actual)))
                else:
                    queue.append((next_path, target, depth + len(actual)))
                queued.add(next_path)
            if changed and feedback:
                # The installed operation changes the very next candidate set.
                # Previously attempted pairs are not repeated.
                if path not in queued:
                    queue.appendleft((path, expected, depth))
                    queued.add(path)
                break
    return report('TRAINING_BOUND_EXHAUSTED' if exhausted or spent >= max_training_actions
                  or episodes >= max_episodes else 'NO_TERMINAL_WITHIN_BOUND')
