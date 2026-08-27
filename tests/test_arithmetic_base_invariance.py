import itertools
import unittest


def prefix_value(history, side, base):
    return sum(pair[side] * (base ** i) for i, pair in enumerate(history))


def oracle_next_digit(history, pair, base):
    h = tuple(history) + (tuple(pair),)
    total = prefix_value(h, 0, base) + prefix_value(h, 1, base)
    return (total // (base ** (len(h) - 1))) % base


def signature(history, contexts, base):
    return tuple(oracle_next_digit(history, c, base) for c in contexts)


def adaptive_partition(base):
    pairs = tuple(itertools.product(range(base), repeat=2))
    # Empty history plus every possible one-position history is enough to expose
    # both latent future-behaviour classes for two-addend positional addition.
    histories = ((),) + tuple((p,) for p in pairs)
    retained = []
    full = {h: signature(h, pairs, base) for h in histories}

    while True:
        current = {h: signature(h, retained, base) for h in histories}
        buckets = {}
        witness = None
        for h in histories:
            key = current[h]
            if key in buckets and full[buckets[key]] != full[h]:
                witness = (buckets[key], h)
                break
            buckets.setdefault(key, h)
        if witness is None:
            break
        x, y = witness
        sep = next(c for c in pairs if oracle_next_digit(x, c, base) != oracle_next_digit(y, c, base))
        retained.append(sep)

    groups = {}
    for h in histories:
        groups.setdefault(signature(h, retained, base), []).append(h)
    return pairs, histories, tuple(retained), tuple(tuple(v) for v in groups.values())


class ArithmeticBaseInvariance(unittest.TestCase):
    def test_two_state_interface_reappears_across_positional_bases(self):
        census = {}
        for base in range(2, 17):
            pairs, histories, retained, classes = adaptive_partition(base)
            self.assertEqual(len(classes), 2)
            self.assertGreaterEqual(len(retained), 1)

            # The external judge may inspect the known arithmetic meaning only to
            # verify the learned partition. The learner itself used future-output
            # equality only. Every discovered class has one constant carry-out.
            class_carries = []
            for cls in classes:
                carries = set()
                for h in cls:
                    if not h:
                        carries.add(0)
                    else:
                        a, b = h[-1]
                        carries.add((a + b) // base)
                self.assertEqual(len(carries), 1)
                class_carries.append(next(iter(carries)))
            self.assertEqual(sorted(class_carries), [0, 1])

            census[base] = {
                "alphabet": len(pairs),
                "histories": len(histories),
                "retained": retained,
                "states": len(classes),
            }

        print(f"arithmetic base-invariance census: {census}")


if __name__ == "__main__":
    unittest.main()
