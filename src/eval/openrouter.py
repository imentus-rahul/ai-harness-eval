"""OpenAI-compatible chat client for OpenRouter."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ChatResult:
    content: str
    tool_calls: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    ttft_ms: int | None
    duration_ms: int


def chat(
    endpoint: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    api_key: str,
    timeout: int = 120,
) -> ChatResult:
    url = endpoint.rstrip("/") + "/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2048,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/harness-eval-simple",
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    started = time.monotonic()
    ttft_ms: int | None = None
    chunks: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                piece = line[5:].strip()
                if piece == "[DONE]":
                    break
                try:
                    event = json.loads(piece)
                except json.JSONDecodeError:
                    continue
                if ttft_ms is None and event.get("choices"):
                    ttft_ms = int((time.monotonic() - started) * 1000)
                if event.get("usage"):
                    usage = event["usage"]
                delta = (event.get("choices") or [{}])[0].get("delta") or {}
                if delta.get("content"):
                    chunks.append(delta["content"])
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        while len(tool_calls) <= idx:
                            tool_calls.append(
                                {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )
                        if tc.get("id"):
                            tool_calls[idx]["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            tool_calls[idx]["function"]["name"] = fn["name"]
                        if fn.get("arguments"):
                            tool_calls[idx]["function"]["arguments"] += fn["arguments"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"chat HTTP {exc.code}: {detail}") from exc

    cost = usage.get("cost")
    if cost is not None:
        cost = float(cost)

    return ChatResult(
        content="".join(chunks),
        tool_calls=tool_calls,
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
        cost_usd=cost,
        ttft_ms=ttft_ms,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def rubric_chat(
    endpoint: str,
    model: str,
    api_key: str,
    system: str,
    user: str,
) -> tuple[str, float | None, int, int]:
    """Single non-tool completion for model grading."""
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": 256,
    }
    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    usage = body.get("usage") or {}
    text = (body["choices"][0]["message"].get("content") or "").strip()
    cost = usage.get("cost")
    return (
        text,
        float(cost) if cost is not None else None,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
    )
