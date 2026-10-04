from eval.models import afford_credit_error, model_chain
from eval.pricing import normalize_cost


def test_normalize_cost_prefers_reported():
    cost, src = normalize_cost("google/gemini-2.5-flash-lite", 0.0012, 100, 50)
    assert cost == 0.0012
    assert src == "reported"


def test_normalize_cost_computes_when_missing():
    cost, src = normalize_cost("google/gemini-2.5-flash-lite", None, 1_000_000, 0)
    assert cost > 0
    assert src == "computed"


def test_model_chain_dedupes():
    chain = model_chain("google/gemini-2.5-flash-lite")
    assert chain[0] == "google/gemini-2.5-flash-lite"
    assert len(chain) == len(set(chain))


def test_afford_credit_error():
    assert afford_credit_error("can only afford 43 tokens")
    assert not afford_credit_error("openrouter_in_flight_budget")
