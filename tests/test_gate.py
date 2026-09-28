from eval.gate import phase2_blocked_reason, phase2_eligible


def test_phase2_blocked_on_regression():
    comparisons = [
        {
            "task_id": "keep-suite",
            "suite": "regression",
            "transition": "REGRESSED",
            "candidate_outcome": "FAIL",
        },
    ]
    assert not phase2_eligible(comparisons, [])
    reason = phase2_blocked_reason(comparisons, [])
    assert reason is not None
    assert "keep-suite" in reason


def test_phase2_allowed_when_promoted():
    comparisons = [
        {
            "task_id": "auth-vs-log",
            "suite": "capability",
            "transition": "IMPROVED",
            "candidate_outcome": "PASS",
        },
        {
            "task_id": "keep-suite",
            "suite": "regression",
            "transition": "UNCHANGED",
            "candidate_outcome": "PASS",
        },
    ]
    assert phase2_eligible(comparisons, ["auth-vs-log"])
