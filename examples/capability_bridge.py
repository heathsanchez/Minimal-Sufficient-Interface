"""Minimal O1 -> finer interface -> O2 quotient-admissibility witness."""

from msi import Interface

X = (0, 1, 2)
v = {0: 0, 1: 0, 2: 1}
O1_map = {0: 0, 1: 2, 2: 0}
O2_map = {0: 0, 1: 2, 2: 0}
O1 = lambda x: O1_map[x]
O2 = lambda x: O2_map[x]

C = ("v", "v_after_O1")


def outcome(x, c):
    if c == "v":
        return v[x]
    if c == "v_after_O1":
        return v[O1(x)]
    raise KeyError(c)


I = Interface(X, C, outcome)
before = ("v",)
after = ("v", "v_after_O1")

assert I.partition(before) == ((0, 1), (2,))
assert I.partition(after) == ((0,), (1,), (2,))
assert not I.preserves_equivalence(O2, before)
assert I.preserves_equivalence(O2, after)

print("before:", I.partition(before))
print("after O1 exposes v∘O1:", I.partition(after))
print("O2 quotient-admissible before:", I.preserves_equivalence(O2, before))
print("O2 quotient-admissible after:", I.preserves_equivalence(O2, after))
print("PASS: O1 -> new protected continuation -> finer interface -> O2 admissible")
