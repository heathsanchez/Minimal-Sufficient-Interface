"""Generic public action grounding. No game source or semantic labels.

The finite coordinate lattice is a bounded experiment grammar, not a claim
that every valid or useful action has been enumerated. Action 6 uses the
public SDK's x/y payload. Other non-simple actions remain unsupported.
"""
from agent import observation


def action_catalog(space, frame, stride=8, max_actions=256):
    if stride < 1 or max_actions < 1:
        raise ValueError('positive grounding bounds required')
    obs = observation(frame)
    layers = obs['frame']
    if not layers or not layers[0] or not layers[0][0]:
        raise ValueError('No public image dimensions')
    height, width = len(layers[0]), len(layers[0][0])
    if any(len(row) != width for row in layers[0]):
        raise ValueError('Nonrectangular public image')
    ids = sorted({int(a.value) for a in space})
    actions = [a for a in ids if a != 6]
    unsupported = [a for a in ids if a != 6 and not next(x for x in space if int(x.value)==a).is_simple()]
    actions = [a for a in actions if a not in unsupported]
    if 6 in ids:
        # Coarse-to-fine sampling: every coordinate is derived from public
        # image dimensions. No color, object, goal, or game-specific location.
        seen = set()
        for step in (stride, max(1, stride // 2), 1):
            for y in range(step // 2, height, step):
                for x in range(step // 2, width, step):
                    a = (6, x, y)
                    if a not in seen:
                        seen.add(a)
                        actions.append(a)
                        if len(actions) >= max_actions:
                            return tuple(actions), tuple(unsupported)
    return tuple(actions), tuple(unsupported)


def decode(action):
    from arcengine import GameAction
    if isinstance(action, int):
        return GameAction.from_id(action), None
    if isinstance(action, tuple) and len(action) == 3 and action[0] == 6:
        return GameAction.from_id(6), {'x': int(action[1]), 'y': int(action[2])}
    raise ValueError('Unsupported action token')
