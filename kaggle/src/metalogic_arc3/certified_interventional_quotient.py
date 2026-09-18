from __future__ import annotations

"""Exact source-scoped interventional quotient certificate.

These equivalence classes were earned by:
1. observer-only partial consequence refinement on frozen MG-ARC5;
2. active probing of every legal primitive action on surviving ls20 pairs;
3. recursive successor-pair closure to a finite replay bisimulation cone.

The certificate is intentionally narrow. It only canonicalizes exact public
observation hashes that were independently replay-verified. It does not infer
from pixels, game names, geometry, colors, objects, or approximate similarity.
It changes consequence-state identity only; .mg memory, transfer guards,
refutations and capability provenance remain raw.
"""

PROVENANCE = {
    "prior_commit": "07fe94a80edfbb295049d4140aef14ef2b47524b",
    "observer_run": 35330229606,
    "separator_run": 35330630192,
    "closure_run": 35337813971,
}

CLASSES = (
    (
        "000d17e88af90a0b78d60209177535fa2a60d3c5d293b14804a60e76be76aa01",
        "07c975565433ed56d235ececbb3dba47586f9b3c6f39b810a3b077d3bb38c57d",
    ),
    (
        "090cc48ca2cb6c721a0c6f9a0517590d2ca3e07e23b4a9e99185042ae0e1da81",
        "393685a8d92ddaf0e7d431786d71c7a35eca5fa58b40ced96c881b2719d05c0d",
    ),
    (
        "1054192bb3e05679bf8f08af54effe84ee96890cb6cf2ebc97ac510d15ed55ab",
        "4523b0d3d767aa9eefb96e41a337be2ef113494ad698f4427543cfbe6ad29c1c",
    ),
    (
        "357a07f24faf1f2dace51d8d2e7cb917e39a880e34e2a10186acc79d1a41e6fe",
        "5bd539e65dc22d2e0c65f59e980b8189665ba500a88d6869347b628b5ced34d7",
    ),
    (
        "5dda0f29b181a9cc5fcceb1f73668e188e06ea3a429f479b7c4807db098ce5e2",
        "6a50ca5fb858a45d005b9672ce9abae25d3b699192936c6c83d6f31dfd0a3617",
        "9d5efe83551026f9c20183c28e795ee23bbba5f69b7633f3e6e8fc48c23d7d26",
    ),
    (
        "8c43482f5e63d6c5697cb8b9cd17bf7d48ec3d1f7936c207bcf57648cb45225a",
        "e276f06bee69f8236641d4f95749fd6e545de45a92bda370f5c99a2bbdf95624",
    ),
)

CANONICAL = {
    member: group[0]
    for group in CLASSES
    for member in group
}


class CertifiedInterventionalQuotient:
    def __init__(self) -> None:
        self._canonical = dict(CANONICAL)

    def active(self, exact_digest: str) -> bool:
        return str(exact_digest) in self._canonical

    def context(self, exact_digest: str) -> str:
        digest = str(exact_digest)
        canonical = self._canonical.get(digest)
        return digest if canonical is None else f"iq:{canonical}"

    @property
    def class_count(self) -> int:
        return len(CLASSES)

    @property
    def member_count(self) -> int:
        return len(self._canonical)
