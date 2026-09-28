from eval.compare import outcome_from_reps, summarise, transition


def test_unstable_not_improved():
    assert transition("FAIL", "UNSTABLE") == "UNSTABLE"
    assert outcome_from_reps([True, False]) == "UNSTABLE"


def test_improved_transition():
    assert transition("FAIL", "PASS") == "IMPROVED"


def test_summarise_positive():
    comps = [
        {
            "transition": "IMPROVED",
            "task_id": "a",
            "suite": "capability",
            "baseline_outcome": "FAIL",
            "candidate_outcome": "PASS",
            "baseline_passes": [False],
            "candidate_passes": [True],
        }
    ]
    s = summarise(comps)
    assert s["verdict"] == "POSITIVE"
