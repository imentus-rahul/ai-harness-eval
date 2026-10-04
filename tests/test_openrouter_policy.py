from eval.openrouter import _http_retryable, _shrink_max_tokens
from eval.run import credits_exhausted_message


def test_in_flight_402_is_retryable():
    detail = '{"reason":"openrouter_in_flight_budget"}'
    assert _http_retryable(402, detail)


def test_credit_cap_402_not_retryable():
    detail = "can only afford 43 tokens"
    assert not _http_retryable(402, detail)


def test_shrink_max_tokens_from_error():
    payload = {"max_tokens": 1024}
    detail = "can only afford 1622"
    assert _shrink_max_tokens(payload, detail)
    assert payload["max_tokens"] == 1558


def test_credits_exhausted_detect():
    assert credits_exhausted_message("can only afford 43")
