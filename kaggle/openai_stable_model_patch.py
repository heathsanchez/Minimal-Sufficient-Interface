from __future__ import annotations

import argparse
from pathlib import Path


def patch(root: Path) -> None:
    root = root.resolve()
    target = root / "inference" / "utils" / "openai_compat.py"
    if not target.is_file():
        raise SystemExit(f"missing Duck openai_compat.py under {root}")

    text = target.read_text(encoding="utf-8")

    old = '''def normalize_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in {"", "openai", "openai-compatible", "compat"}:
        return "vllm"
    if provider in {"openrouter", "router"}:
        return "openrouter"
    return provider
'''
    new = '''def normalize_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower()
    if provider in {"openai"}:
        return "openai"
    if provider in {"", "openai-compatible", "compat", "vllm"}:
        return "vllm"
    if provider in {"openrouter", "router"}:
        return "openrouter"
    return provider
'''
    if old not in text and new not in text:
        raise SystemExit("normalize_provider anchor changed")
    text = text.replace(old, new, 1)

    old_block = '''    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "top_p": top_p,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if tools:
        payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

    normalized = normalize_provider(provider)
    if normalized == "vllm":
        if top_k > 0:
            payload["top_k"] = top_k
        payload["chat_template_kwargs"] = {"enable_thinking": bool(thinking)}
        if seed is not None and seed >= 0:
            payload["seed"] = seed

    return payload
'''
    new_block = '''    normalized = normalize_provider(provider)

    if normalized == "openai":
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "reasoning_effort": "medium",
        }
        if max_tokens is not None:
            payload["max_completion_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        return payload

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "top_p": top_p,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if tools:
        payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

    if normalized == "vllm":
        if top_k > 0:
            payload["top_k"] = top_k
        payload["chat_template_kwargs"] = {"enable_thinking": bool(thinking)}
        if seed is not None and seed >= 0:
            payload["seed"] = seed

    return payload
'''
    if old_block not in text and new_block not in text:
        raise SystemExit("build_chat_payload anchor changed")
    text = text.replace(old_block, new_block, 1)

    target.write_text(text, encoding="utf-8")
    compile(text, str(target), "exec")
    print("OPENAI_STABLE_MODEL_PATCH=PASS")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    args = p.parse_args()
    patch(args.root)


if __name__ == "__main__":
    main()
