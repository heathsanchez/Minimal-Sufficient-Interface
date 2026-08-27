import itertools
import unittest


BASE = 10
DIGITS = tuple(range(BASE))
PAIR_ALPHABET = tuple(itertools.product(DIGITS, repeat=2))


def digits(n, width):
    return tuple((n // (BASE ** i)) % BASE for i in range(width))


def stream(a, b, width, direction):
    da = digits(a, width)
    db = digits(b, width)
    if direction == "lsd":
        idx = range(width)
    elif direction == "msd":
        idx = range(width - 1, -1, -1)
    else:
        raise ValueError(direction)
    return tuple((da[i], db[i]) for i in idx)


def target_digit_stream(a, b, width, direction):
    s = a + b
    ds = digits(s % (BASE ** width), width)
    if direction == "lsd":
        return ds
    if direction == "msd":
        return tuple(reversed(ds))
    raise ValueError(direction)


def first_causal_conflict(width, direction):
    """Find same observed prefix/current symbol with different required next output."""
    seen = {}
    limit = BASE ** width
    for a in range(limit):
        for b in range(limit):
            xs = stream(a, b, width, direction)
            ys = target_digit_stream(a, b, width, direction)
            prefix = ()
            for x, y in zip(xs, ys):
                key = (prefix, x)
                old = seen.get(key)
                if old is not None and old[0] != y:
                    return {
                        "prefix": prefix,
                        "symbol": x,
                        "output_a": old[0],
                        "example_a": old[1],
                        "output_b": y,
                        "example_b": (a, b),
                    }
                seen[key] = (y, (a, b))
                prefix = prefix + (x,)
    return None


def prefix_value(history, side):
    return sum(pair[side] * (BASE ** i) for i, pair in enumerate(history))


def oracle_next_digit_lsd(history, pair):
    h = tuple(history) + (tuple(pair),)
    total = prefix_value(h, 0) + prefix_value(h, 1)
    return (total // (BASE ** (len(h) - 1))) % BASE


def oracle_terminal_lsd(history):
    if not history:
        return 0
    total = prefix_value(history, 0) + prefix_value(history, 1)
    return total // (BASE ** len(history))


def signature(history, contexts):
    return tuple(oracle_next_digit_lsd(history, c) for c in contexts)


def histories_through(depth):
    hs = [()]
    frontier = [()]
    for _ in range(depth):
        frontier = [h + (p,) for h in frontier for p in PAIR_ALPHABET]
        hs.extend(frontier)
    return tuple(hs)


def adaptive_refine(histories):
    retained = []
    full = {h: signature(h, PAIR_ALPHABET) for h in histories}
    while True:
        current = {h: signature(h, retained) for h in histories}
        bucket = {}
        witness = None
        for h in histories:
            k = current[h]
            if k in bucket and full[bucket[k]] != full[h]:
                witness = (bucket[k], h)
                break
            bucket.setdefault(k, h)
        if witness is None:
            return tuple(retained)
        x, y = witness
        sep = next(c for c in PAIR_ALPHABET if oracle_next_digit_lsd(x, c) != oracle_next_digit_lsd(y, c))
        retained.append(sep)


def partition(histories, contexts):
    groups = {}
    for h in histories:
        groups.setdefault(signature(h, contexts), []).append(h)
    return tuple(tuple(v) for _, v in sorted(groups.items(), key=lambda kv: kv[0]))


def learn_lsd_machine(histories, contexts):
    classes = partition(histories, contexts)
    class_key = {signature(cls[0], contexts): i for i, cls in enumerate(classes)}

    def classify(h):
        return class_key[signature(h, contexts)]

    transition = {}
    output = {}
    terminal = {}
    for i, cls in enumerate(classes):
        terms = {oracle_terminal_lsd(h) for h in cls}
        if len(terms) != 1:
            raise AssertionError("terminal output is not class-invariant")
        terminal[i] = next(iter(terms))
        for pair in PAIR_ALPHABET:
            obs = {(oracle_next_digit_lsd(h, pair), classify(h + (pair,))) for h in cls}
            if len(obs) != 1:
                raise AssertionError("quotient is not compositionally sufficient")
            output[i, pair], transition[i, pair] = next(iter(obs))
    return classify(()), transition, output, terminal, len(classes)


def run_machine(a, b, width, machine):
    state, transition, output, terminal, _ = machine
    da = digits(a, width)
    db = digits(b, width)
    out = []
    for pair in zip(da, db):
        out.append(output[state, pair])
        state = transition[state, pair]
    return sum(d * (BASE ** i) for i, d in enumerate(out)) + terminal[state] * (BASE ** width)


class ArithmeticRepresentationSelection(unittest.TestCase):
    def test_verifier_rejects_msd_first_causal_decomposition(self):
        # Width two already contains a decisive counterexample: the same visible
        # prefix/current digit pair can require different current output digits,
        # depending on an unseen lower-order suffix.
        conflict = first_causal_conflict(2, "msd")
        self.assertIsNotNone(conflict)
        self.assertNotEqual(conflict["output_a"], conflict["output_b"])

        # The low-to-high traversal has no such causal conflict at the same width.
        self.assertIsNone(first_causal_conflict(2, "lsd"))
        print(f"arithmetic direction falsifier: msd_conflict={conflict}")

    def test_structural_selector_recovers_lsd_then_latent_state(self):
        # The selector is not told which traversal is arithmetically natural. It
        # keeps only candidate decompositions for which verified local output is
        # causally well-defined.
        candidates = ("msd", "lsd")
        viable = tuple(d for d in candidates if first_causal_conflict(2, d) is None)
        self.assertEqual(viable, ("lsd",))

        # Only after selecting the viable decomposition do residuals refine the
        # history interface. No carry bit/state label is supplied.
        hs = histories_through(2)
        retained = adaptive_refine(hs)
        classes = partition(hs, retained)
        self.assertEqual(len(classes), 2)
        self.assertEqual(len(retained), 1)

        machine = learn_lsd_machine(hs, retained)
        self.assertEqual(machine[-1], 2)

        # Freeze both representation choice and learned quotient dynamics, then
        # extrapolate far outside the two-position discovery regime.
        cases = [
            (int("9" * 60), 1),
            (int("5" * 60), int("5" * 60)),
            (int("1234567890" * 6), int("9876543210" * 6)),
            (10**59 + 12345, 10**59 + 98765),
        ]
        seed = 314159
        mod = 10**60
        for _ in range(256):
            seed = (2862933555777941757 * seed + 3037000493) % mod
            a = seed
            seed = (2862933555777941757 * seed + 3037000493) % mod
            b = seed
            cases.append((a, b))

        for a, b in cases:
            self.assertEqual(run_machine(a, b, 60, machine), a + b)

        print(
            "arithmetic representation selection: "
            f"candidates={candidates}; viable={viable}; "
            f"discovery_histories={len(hs)}; retained={retained}; "
            f"learned_states={len(classes)}; extrapolated_60digit_cases={len(cases)}"
        )


if __name__ == "__main__":
    unittest.main()
