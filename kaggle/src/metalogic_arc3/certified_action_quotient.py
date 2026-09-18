from __future__ import annotations

"""Replay-certified ft09 action quotient promoted by QCKN Flash evidence.

Scope is deliberately exact-state. The ten source observation hashes were the
two training states plus eight prospective held states from run 35339917853.
Across every held state, all *present* members of each learned coordinate class
had one exact successor consequence. The only held mismatch was that coordinate
(6,31,63) from the large no-change class was absent from the later controller
catalog; no conflicting consequence was observed.

This certificate therefore authorizes replacing the observed 64-coordinate
Action6 proposal set by one representative from each of the ten consequence
classes only at the exact certified observations below. It does not generalize
by pixels, game name, dimensions, or approximate similarity.
"""

PROVENANCE = {
    "champion_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
    "action_quotient_run": 35339081620,
    "prospective_transfer_run": 35339917853,
}

CERTIFIED_STATES = frozenset({
    "0269afc0030c33d48719106407db26509b8c92e954ca8f428bd9dc897ebd27c3",
    "bf2bc8388c544a06ab412d7a08910aa56730892c5697bc191d50ae27f2c74a61",
    "eac046625b6ffab2764ab896479edb16fe7c6419c058e2de95f54a7227b6d246",
    "46ad9ddd24a1ba7c1943b5a2411f76e3bf45052c3ae3c27fd21849eb1cb7cdbc",
    "dd4d982b2376569ac66c5221d72173e0bdadd144fca27a7fd614233a8852817d",
    "d814712f642eecc00d8b82ee802f4e93a71af077f01ed6dd948f085b34936b0a",
    "14ae1d9f6038ab4f1693bfc3e80149b6de4b22c38602682fe27b1958a013aae0",
    "7a46bbf3b719ff6cf52d82603ab53fb69b77f67997e17de73d0a4d22926f5cfc",
    "fb3aaaa4710a6dd24b5c548c14b129e632a73250a6eab4ed84fa45e182236d52",
    "860f05d70ca9cd7033edfa8f1a0f9d1d71d0f8641b688c9551d7e1e9c03a0338",
})

REPRESENTATIVES = frozenset({
    (6, 6, 4),
    (6, 44, 46),
    (6, 38, 38),
    (6, 38, 46),
    (6, 38, 54),
    (6, 46, 38),
    (6, 46, 54),
    (6, 54, 38),
    (6, 54, 46),
    (6, 54, 54),
})


class CertifiedActionQuotient:
    def __init__(self) -> None:
        self.states = CERTIFIED_STATES
        self.representatives = REPRESENTATIVES

    def active(self, evidence_sha256: str) -> bool:
        return str(evidence_sha256) in self.states

    def keep(self, evidence_sha256: str, action: tuple[int, int | None, int | None]) -> bool:
        if not self.active(evidence_sha256):
            return True
        action_id, x, y = action
        if int(action_id) != 6:
            return True
        return (6, int(x), int(y)) in self.representatives

    @property
    def state_count(self) -> int:
        return len(self.states)

    @property
    def representative_count(self) -> int:
        return len(self.representatives)
