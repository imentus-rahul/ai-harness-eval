"""OpenRouter model selection and fallback chain."""

from __future__ import annotations

import os

DEFAULT_MODEL = "google/gemini-3-flash-preview"

# Cheaper first when falling back from credit / afford 402 errors.
DEFAULT_FALLBACK_MODELS = (
    "google/gemini-2.5-flash-lite",
    "google/gemini-3-flash-preview",
    "anthropic/claude-haiku-4.5",
)


def model_chain(primary: str) -> list[str]:
    extra = os.environ.get("OPENROUTER_FALLBACK_MODELS", "")
    from_env = [m.strip() for m in extra.split(",") if m.strip()]
    chain: list[str] = []
    for m in [primary, *from_env, *DEFAULT_FALLBACK_MODELS]:
        if m and m not in chain:
            chain.append(m)
    return chain


def afford_credit_error(detail: str) -> bool:
    dl = detail.lower()
    return "can only afford" in dl or "requires more credits" in dl
