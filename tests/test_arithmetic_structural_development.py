import itertools
import unittest


BASE = 10
DIGIT_PAIRS = tuple(itertools.product(range(BASE), repeat=2))


def prefix_value(history, side):
    return sum(pair[side] * (BASE ** i) for i, pair in enumerate(history))


def oracle_next_digit(history, pair):
    """Verifier-visible next output digit; learner is not given hidden state."""
    h = tuple(history) + (tuple(pair),)
    total = prefix_value(h, 0) + prefix_value(h, 1)
    return (total // (BASE ** (len(h) - 1))) % BASE


def oracle_terminal_output(history):
    """Verifier-visible terminal suffix after the supplied low-order digits."""
    if not history:
        return 0
    total = prefix_value(history, 0) + prefix_value(history, 1)
    return total // (BASE ** len(history))


def signature(history, contexts):
    return tuple(oracle_next_digit(history, c) for c in contexts)


def relation(histories, contexts):
    sig = {h: signature(h, contexts) for h in histories}
    return frozenset((x, y) for x in histories for y in histories if sig[x] == sig[y])


def adaptive_refine(histories, protected_contexts):
    """Start maximally coarse and add only concrete future separators."""
    retained = []
    full = relation(histories, protected_contexts)
    while True:
        current = relation(histories, retained)
        if current == full:
            return tuple(retained), current
        witness = next((x, y) for (x, y) in current if (x, y) not in full)
        x, y = witness
        sep = next(c for c in protected_contexts if oracle_next_digit(x, c) != oracle_next_digit(y, c))
        if sep not in retained:
            retained.append(sep)
        else:
            raise AssertionError("residual separator was already retained")


def histories_through(depth):
    hs = [()]
    frontier = [()]
    for _ in range(depth):
        frontier = [h + (p,) for h in frontier for p in DIGIT_PAIRS]
        hs.extend(frontier)
    return tuple(hs)


def partition(histories, contexts):
    groups = {}
    for h in histories:
        groups.setdefault(signature(h, contexts), []).append(h)
    return tuple(tuple(v) for _, v in sorted(groups.items(), key=lambda kv: kv[0]))


def learn_machine(discovery_histories, retained_contexts):
    """Synthesize quotient-state transition/output tables from verified traces only."""
    classes = partition(discovery_histories, retained_contexts)
    class_key = {signature(cls[0], retained_contexts): i for i, cls in enumerate(classes)}

    def classify(history):
        key = signature(history, retained_contexts)
        if key not in class_key:
            raise AssertionError("refined interface failed to classify a reachable history")
        return class_key[key]

    transition = {}
    output = {}
    terminal = {}

    for i, cls in enumerate(classes):
        term_values = {oracle_terminal_output(h) for h in cls}
        if len(term_values) != 1:
            raise AssertionError("terminal behaviour is not constant on learned interface class")
        terminal[i] = next(iter(term_values))

        for pair in DIGIT_PAIRS:
            observed = set()
            for h in cls:
                observed.add((oracle_next_digit(h, pair), classify(h + (pair,))))
            if len(observed) != 1:
                raise AssertionError("learned interface is not compositionally sufficient")
            out, nxt = next(iter(observed))
            output[i, pair] = out
            transition[i, pair] = nxt

    start = classify(())
    return classes, start, transition, output, terminal


def digits_lsd(n, width):
    return tuple((n // (BASE ** i)) % BASE for i in range(width))


def add_with_learned_machine(a, b, width, machine):
    classes, state, transition, output, terminal = machine
    da = digits_lsd(a, width)
    db = digits_lsd(b, width)
    out_digits = []
    for pair in zip(da, db):
        out_digits.append(output[state, pair])
        state = transition[state, pair]
    tail = terminal[state]
    value = sum(d * (BASE ** i) for i, d in enumerate(out_digits))
    value += tail * (BASE ** width)
    return value


class ArithmeticStructuralDevelopment(unittest.TestCase):
    def test_stateless_local_interface_is_falsified(self):
        # Same current input (0,0), different prior history, different verified future.
        h0 = ((0, 0),)
        h1 = ((5, 5),)
        pair = (0, 0)
        self.assertEqual(oracle_next_digit(h0, pair), 0)
        self.assertEqual(oracle_next_digit(h1, pair), 1)

    def test_residuals_discover_minimal_compositional_state_and_extrapolate(self):
        # Discovery sees only histories of length <= 2.  No hidden state variable or
        # arithmetic carry label is supplied to the learner.
        hs = histories_through(2)
        retained, recovered_relation = adaptive_refine(hs, DIGIT_PAIRS)
        classes = partition(hs, retained)

        # The verifier forces exactly two behavioural interface states from an
        # initially indiscriminate representation, using a concrete future context.
        self.assertEqual(len(classes), 2)
        self.assertEqual(recovered_relation, relation(hs, DIGIT_PAIRS))
        self.assertGreaterEqual(len(retained), 1)

        machine = learn_machine(hs, retained)
        learned_classes, _, transition, output, terminal = machine
        self.assertEqual(len(learned_classes), 2)
        self.assertEqual(len(transition), 2 * BASE * BASE)
        self.assertEqual(len(output), 2 * BASE * BASE)
        self.assertEqual(len(terminal), 2)

        # Exhaust every addition through 3 decimal digits: already beyond the
        # two-digit discovery regime.
        for a in range(1000):
            for b in range(1000):
                self.assertEqual(add_with_learned_machine(a, b, 3, machine), a + b)

        # Then test exact length extrapolation far outside discovery.  The cases
        # are deterministic and include long propagation chains and varied digits.
        long_cases = [
            (int("9" * 40), 1),
            (int("5" * 40), int("5" * 40)),
            (int("1234567890" * 4), int("9876543210" * 4)),
            (10**39 + 7, 10**39 + 8),
        ]
        seed = 1729
        mod = 10**40
        for _ in range(200):
            seed = (6364136223846793005 * seed + 1442695040888963407) % mod
            a = seed
            seed = (6364136223846793005 * seed + 1442695040888963407) % mod
            b = seed
            long_cases.append((a, b))

        for a, b in long_cases:
            self.assertEqual(add_with_learned_machine(a, b, 40, machine), a + b)

        print(
            "arithmetic structural development: "
            f"discovery_histories={len(hs)}; "
            f"protected_one_step_contexts={len(DIGIT_PAIRS)}; "
            f"retained_separator_contexts={len(retained)}; "
            f"learned_interface_states={len(classes)}; "
            f"exhaustive_3digit_pairs={1000*1000}; "
            f"long_40digit_cases={len(long_cases)}; "
            f"retained={retained}"
        )


if __name__ == "__main__":
    unittest.main()
