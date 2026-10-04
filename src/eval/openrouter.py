"""OpenAI-compatible chat client for OpenRouter."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .log_util import info, warn
from .models import afford_credit_error, model_chain
from .pricing import normalize_cost

MAX_CHAT_RETRIES = 6
DEFAULT_RETRY_SLEEP_S = 5.0
DEFAULT_MAX_TOKENS = 1024


@dataclass
class ChatResult:
    content: str
    tool_calls: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    ttft_ms: int | None
    duration_ms: int
    model: str = ""


def _http_retryable(code: int, detail: str) -> bool:
    dl = detail.lower()
    if code in (429, 503):
        return True
    if code == 402:
        if "in_flight" in dl or "in-flight" in dl:
            return True
        if "retry after" in dl:
            return True
        return False
    return False


def _shrink_max_tokens(payload: dict[str, Any], detail: str) -> bool:
    m = re.search(r"can only afford\s+(\d+)", detail, re.I)
    if not m:
        return False
    afford = int(m.group(1))
    if afford < 128:
        return False
    payload["max_tokens"] = max(128, afford - 64)
    return True


def _retry_sleep_seconds(
    exc: urllib.error.HTTPError,
    attempt: int,
    detail: str,
) -> float:
    raw = exc.headers.get("Retry-After") if exc.headers else None
    if raw:
        try:
            return min(float(raw), 120.0)
        except ValueError:
            pass
    m = re.search(r'"Retry-After"\s*:\s*"?(\d+)"?', detail)
    if m:
        return min(float(m.group(1)), 120.0)
    return min(DEFAULT_RETRY_SLEEP_S * (attempt + 1), 30.0)


def _chat_once(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
    *,
    stream: bool,
) -> ChatResult:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    started = time.monotonic()
    ttft_ms: int | None = None
    chunks: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    usage: dict[str, Any] = {}

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if not stream:
            body = json.load(resp)
            choice = body["choices"][0]["message"]
            u = body.get("usage") or {}
            model_id = payload.get("model", "")
            in_tok = int(u.get("prompt_tokens") or 0)
            out_tok = int(u.get("completion_tokens") or 0)
            raw_cost = u.get("cost")
            reported = float(raw_cost) if raw_cost is not None else None
            cost_usd, _ = normalize_cost(model_id, reported, in_tok, out_tok)
            return ChatResult(
                content=choice.get("content") or "",
                tool_calls=choice.get("tool_calls") or [],
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=cost_usd,
                ttft_ms=None,
                duration_ms=int((time.monotonic() - started) * 1000),
                model=model_id,
            )

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

    model_id = payload.get("model", "")
    in_tok = int(usage.get("prompt_tokens") or 0)
    out_tok = int(usage.get("completion_tokens") or 0)
    raw_cost = usage.get("cost")
    reported = float(raw_cost) if raw_cost is not None else None
    cost_usd, _src = normalize_cost(model_id, reported, in_tok, out_tok)

    return ChatResult(
        content="".join(chunks),
        tool_calls=tool_calls,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost_usd=cost_usd,
        ttft_ms=ttft_ms,
        duration_ms=int((time.monotonic() - started) * 1000),
        model=model_id,
    )


def _chat_with_retries(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
) -> ChatResult:
    last_err: Exception | None = None
    for attempt in range(MAX_CHAT_RETRIES):
        try:
            result = _chat_once(url, payload, headers, timeout, stream=True)
            empty = (
                not result.tool_calls
                and not (result.content or "").strip()
                and result.input_tokens == 0
                and result.output_tokens == 0
            )
            if empty and attempt < MAX_CHAT_RETRIES - 1:
                warn("OpenRouter returned empty completion; retrying")
                time.sleep(min(DEFAULT_RETRY_SLEEP_S * (attempt + 1), 15.0))
                continue
            model_id = payload["model"]
            cost, src = normalize_cost(
                model_id, result.cost_usd, result.input_tokens, result.output_tokens
            )
            result.cost_usd = cost
            info(
                f"OpenRouter chat | model={model_id} | in={result.input_tokens} "
                f"out={result.output_tokens} | cost=${cost:.6f} ({src})"
            )
            return result
        except urllib.error.HTTPError as exc:
            last_err = exc
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 402 and _shrink_max_tokens(payload, detail) and attempt < MAX_CHAT_RETRIES - 1:
                warn(f"OpenRouter 402: lowering max_tokens to {payload['max_tokens']}")
                continue
            if _http_retryable(exc.code, detail) and attempt < MAX_CHAT_RETRIES - 1:
                wait = _retry_sleep_seconds(exc, attempt, detail)
                warn(
                    f"OpenRouter HTTP {exc.code} (attempt {attempt + 1}/{MAX_CHAT_RETRIES}); "
                    f"sleep {wait:.0f}s"
                )
                time.sleep(wait)
                continue
            raise RuntimeError(f"chat HTTP {exc.code}: {detail[:500]}") from exc
    raise RuntimeError(f"chat failed after retries: {last_err}")


def chat(
    endpoint: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    api_key: str,
    timeout: int = 120,
) -> ChatResult:
    url = endpoint.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/harness-eval-simple",
    }

    last_err: Exception | None = None
    for model_id in model_chain(model):
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            return _chat_with_retries(url, payload, headers, timeout)
        except RuntimeError as exc:
            last_err = exc
            msg = str(exc)
            if "HTTP 402" in msg and afford_credit_error(msg) and model_id != model_chain(model)[-1]:
                warn(f"OpenRouter credits tight on {model_id}; trying next fallback model")
                continue
            raise
    raise RuntimeError(f"chat failed on all models: {last_err}")


def rubric_chat(
    endpoint: str,
    model: str,
    api_key: str,
    system: str,
    user: str,
) -> tuple[str, float | None, int, int]:
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
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    last_err: Exception | None = None
    chain = model_chain(model)
    for model_id in chain:
        payload["model"] = model_id
        for attempt in range(MAX_CHAT_RETRIES):
            try:
                result = _chat_once(url, payload, headers, 60, stream=False)
                cost, src = normalize_cost(
                    model_id, result.cost_usd, result.input_tokens, result.output_tokens
                )
                info(
                    f"OpenRouter rubric | model={model_id} | in={result.input_tokens} "
                    f"out={result.output_tokens} | cost=${cost:.6f} ({src})"
                )
                return (
                    result.content.strip(),
                    cost,
                    result.input_tokens,
                    result.output_tokens,
                )
            except urllib.error.HTTPError as exc:
                last_err = exc
                detail = exc.read().decode("utf-8", errors="replace")
                if _http_retryable(exc.code, detail) and attempt < MAX_CHAT_RETRIES - 1:
                    wait = _retry_sleep_seconds(exc, attempt, detail)
                    warn(f"rubric HTTP {exc.code}; sleep {wait:.0f}s")
                    time.sleep(wait)
                    continue
                if exc.code == 402 and afford_credit_error(detail) and model_id != chain[-1]:
                    warn(f"rubric credits tight on {model_id}; trying next fallback model")
                    break
                raise RuntimeError(f"rubric HTTP {exc.code}: {detail[:500]}") from exc
    raise RuntimeError(f"rubric failed after retries: {last_err}")
