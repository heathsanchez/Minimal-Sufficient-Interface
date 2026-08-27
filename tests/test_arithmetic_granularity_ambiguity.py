import itertools
import unittest


def discover_chunk_machine(chunk_digits):
    chunk_base = 10 ** chunk_digits
    symbols = tuple(range(chunk_base))

    # The single protected future context (0,0) exposes whether a processed
    # chunk leaves a carry into the next chunk. No semantic carry label is used
    # by the partition itself; equality of next verified output is enough.
    histories = tuple(itertools.product(symbols, repeat=2))
    sig = {h: (sum(h) // chunk_base) for h in histories}
    groups = {}
    for h in histories:
        groups.setdefault(sig[h], []).append(h)
    classes = tuple(tuple(v) for _, v in sorted(groups.items()))
    assert len(classes) == 2

    # Synthesize the two-state quotient dynamics from verified chunk arithmetic.
    output = {}
    transition = {}
    for state in range(2):
        for a in symbols:
            for b in symbols:
                total = a + b + state
                output[state, a, b] = total % chunk_base
                transition[state, a, b] = total // chunk_base
    return chunk_base, output, transition


def chunks_lsd(n, chunk_base, count):
    return tuple((n // (chunk_base ** i)) % chunk_base for i in range(count))


def run_chunk_machine(a, b, decimal_width, chunk_digits, machine):
    chunk_base, output, transition = machine
    assert decimal_width % chunk_digits == 0
    count = decimal_width // chunk_digits
    aa = chunks_lsd(a, chunk_base, count)
    bb = chunks_lsd(b, chunk_base, count)
    state = 0
    out = []
    for x, y in zip(aa, bb):
        out.append(output[state, x, y])
        state = transition[state, x, y]
    value = sum(d * (chunk_base ** i) for i, d in enumerate(out))
    return value + state * (chunk_base ** count)


class ArithmeticGranularityAmbiguity(unittest.TestCase):
    def test_multiple_chunk_granularities_are_equally_compositional(self):
        machines = {k: discover_chunk_machine(k) for k in (1, 2)}
        self.assertEqual(machines[1][0], 10)
        self.assertEqual(machines[2][0], 100)

        # Both decompositions have the same two-state minimal hidden interface.
        # Exactness therefore cannot by itself choose digit chunks over 2-digit
        # chunks; representation granularity needs an additional cost/resource
        # criterion above verifier correctness.
        cases = [
            (int("9" * 40), 1),
            (int("5" * 40), int("5" * 40)),
            (int("1234567890" * 4), int("9876543210" * 4)),
            (10**39 + 123456, 10**39 + 654321),
        ]
        seed = 271828
        mod = 10**40
        for _ in range(128):
            seed = (6364136223846793005 * seed + 1442695040888963407) % mod
            a = seed
            seed = (6364136223846793005 * seed + 1442695040888963407) % mod
            b = seed
            cases.append((a, b))

        for k, machine in machines.items():
            for a, b in cases:
                self.assertEqual(run_chunk_machine(a, b, 40, k, machine), a + b)

        print(
            "arithmetic granularity ambiguity: "
            f"chunk_digits=(1,2); learned_states=(2,2); exact_40digit_cases_each={len(cases)}"
        )


if __name__ == "__main__":
    unittest.main()
