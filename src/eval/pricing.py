"""OpenRouter cost normalization when usage.cost is missing."""

from __future__ import annotations

# USD per 1M tokens (input, output) — estimates for cost_source=computed
ESTIMATE_PER_M: dict[str, tuple[float, float]] = {
    "google/gemini-2.5-flash-lite": (0.075, 0.30),
    "google/gemini-3-flash-preview": (0.15, 0.60),
    "anthropic/claude-haiku-4.5": (0.80, 4.00),
    "anthropic/claude-3.5-haiku": (0.80, 4.00),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    key = model
    for slug, rates in ESTIMATE_PER_M.items():
        if slug in model or model.endswith(slug.split("/")[-1]):
            key = slug
            break
    inp_m, out_m = ESTIMATE_PER_M.get(key, (0.50, 1.50))
    return (input_tokens / 1_000_000) * inp_m + (output_tokens / 1_000_000) * out_m


def normalize_cost(
    model: str,
    reported: float | None,
    input_tokens: int,
    output_tokens: int,
) -> tuple[float, str]:
    if reported is not None and reported >= 0:
        return float(reported), "reported"
    if input_tokens or output_tokens:
        return estimate_cost_usd(model, input_tokens, output_tokens), "computed"
    return 0.0, "unknown"
