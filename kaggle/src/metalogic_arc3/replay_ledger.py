from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .interventional_quotient import PartialInterventionalQuotient


SCHEMA = "arc3-exact-replay-ledger-v1"


def _json_outcome(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_outcome(item) for item in value]
    if isinstance(value, list):
        return [_json_outcome(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _json_outcome(item)
            for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    return value


def _freeze_outcome(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze_outcome(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            sorted((str(key), _freeze_outcome(item)) for key, item in value.items())
        )
    return value


def build_ledger(
    q: PartialInterventionalQuotient,
    prefixes: dict[str, tuple[tuple[int, int | None, int | None], ...]],
    *,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    nodes = {
        str(node): {
            "protected": _json_outcome(record.protected),
            "legal_actions": [int(action) for action in record.legal_actions],
        }
        for node, record in sorted(q.nodes.items(), key=lambda item: str(item[0]))
    }

    edges: list[dict[str, Any]] = []
    for source in sorted(q.edges, key=str):
        for action in sorted(q.edges[source], key=repr):
            for outcome, target in sorted(q.edges[source][action], key=repr):
                edges.append({
                    "source": str(source),
                    "action": _json_outcome(action),
                    "outcome": _json_outcome(outcome),
                    "target": str(target),
                })

    replay_prefixes = {
        str(node): [
            [
                int(action_id),
                None if x is None else int(x),
                None if y is None else int(y),
            ]
            for action_id, x, y in prefix
        ]
        for node, prefix in sorted(prefixes.items())
        if node in q.nodes
    }

    payload = {
        "schema": SCHEMA,
        "metadata": _json_outcome(dict(metadata)),
        "nodes": nodes,
        "edges": edges,
        "prefixes": replay_prefixes,
    }
    payload["content_sha256"] = content_sha256(payload)
    return payload


def content_sha256(payload: dict[str, Any]) -> str:
    clean = dict(payload)
    clean.pop("content_sha256", None)
    raw = json.dumps(
        clean,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return sha256(raw).hexdigest()


def validate_ledger(
    payload: dict[str, Any],
    *,
    expected_game_id: str | None = None,
    expected_agent_sha256: str | None = None,
) -> None:
    if payload.get("schema") != SCHEMA:
        raise ValueError("unsupported exact replay ledger schema")
    expected_digest = payload.get("content_sha256")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ValueError("missing replay ledger content hash")
    if content_sha256(payload) != expected_digest:
        raise ValueError("replay ledger content hash mismatch")

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("replay ledger metadata must be an object")

    if expected_game_id is not None and metadata.get("game_id") != expected_game_id:
        raise ValueError("replay ledger game mismatch")
    if (
        expected_agent_sha256 is not None
        and metadata.get("agent_sha256") != expected_agent_sha256
    ):
        raise ValueError("replay ledger agent mismatch")

    nodes = payload.get("nodes")
    edges = payload.get("edges")
    prefixes = payload.get("prefixes")
    if not isinstance(nodes, dict) or not isinstance(edges, list) or not isinstance(prefixes, dict):
        raise ValueError("malformed replay ledger tables")

    node_ids = set(nodes)
    if not set(prefixes) <= node_ids:
        raise ValueError("replay prefix references unknown node")

    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("malformed replay edge")
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            raise ValueError("replay edge endpoint absent from node table")


def restore_ledger(
    payload: dict[str, Any],
    *,
    expected_game_id: str | None = None,
    expected_agent_sha256: str | None = None,
) -> tuple[
    PartialInterventionalQuotient,
    dict[str, tuple[tuple[int, int | None, int | None], ...]],
]:
    validate_ledger(
        payload,
        expected_game_id=expected_game_id,
        expected_agent_sha256=expected_agent_sha256,
    )

    q = PartialInterventionalQuotient()
    for node, row in payload["nodes"].items():
        q.observe_node(
            node,
            protected=tuple(_freeze_outcome(row["protected"])),
            legal_actions=tuple(int(action) for action in row["legal_actions"]),
        )

    for row in payload["edges"]:
        action = _freeze_outcome(row["action"])
        q.observe_transition(
            row["source"],
            action,
            row["target"],
            outcome=_freeze_outcome(row["outcome"]),
        )

    prefixes = {
        node: tuple(
            (
                int(action_id),
                None if x is None else int(x),
                None if y is None else int(y),
            )
            for action_id, x, y in rows
        )
        for node, rows in payload["prefixes"].items()
    }
    return q, prefixes


def write_ledger(
    path: str | Path,
    q: PartialInterventionalQuotient,
    prefixes: dict[str, tuple[tuple[int, int | None, int | None], ...]],
    *,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    payload = build_ledger(q, prefixes, metadata=metadata)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return payload


def read_ledger(
    path: str | Path,
    *,
    expected_game_id: str | None = None,
    expected_agent_sha256: str | None = None,
):
    payload = json.loads(Path(path).read_text())
    q, prefixes = restore_ledger(
        payload,
        expected_game_id=expected_game_id,
        expected_agent_sha256=expected_agent_sha256,
    )
    return payload, q, prefixes
