"""Open-ended blind worker backend for the recursive discovery compiler.

The backend receives ONLY BlindPacket.public_view(). It has no access to KnowledgeState,
global target, previous synthesis, or controller internals. Output is structured JSON and
remains untrusted until an external verifier accepts it.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from recursive_discovery_compiler import WorkerResult


SYSTEM = """You are a blind local research worker. Solve only the supplied local question.
Do not infer or speculate about a larger hidden objective. Use only the supplied facts and
constraints. Return JSON with keys: answer (object), claims (array of strings), and
subquestions (array of strings). Claims must be precise and falsifiable. If the local facts
are insufficient, say so explicitly in answer.status and propose discriminating subquestions.
"""


def _extract_text(response: dict[str, Any]) -> str:
    # Responses API convenience field is not guaranteed in raw HTTP responses.
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def openai_worker(packet: dict[str, Any]) -> WorkerResult:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    model = os.environ.get("DISCOVERY_WORKER_MODEL", "gpt-5.6")
    role = packet.get("role", "analysis")
    prompt = json.dumps({"role": role, "local_packet": packet}, sort_keys=True)
    body = json.dumps({
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "text": {"format": {"type": "json_object"}},
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"OpenAI worker HTTP {e.code}: {detail[:1000]}") from e
    parsed = json.loads(_extract_text(raw))
    answer = dict(parsed.get("answer", {}))
    if parsed.get("subquestions"):
        answer["subquestions"] = list(parsed["subquestions"])
    return WorkerResult(
        packet_id=packet["id"],
        answer=answer,
        claims=tuple(str(x) for x in parsed.get("claims", [])),
    )
