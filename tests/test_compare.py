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


def test_phase1_unchanged_fail_is_negative():
    comps = [
        {
            "transition": "UNCHANGED",
            "task_id": "auth-vs-log",
            "suite": "capability",
            "baseline_outcome": "FAIL",
            "candidate_outcome": "FAIL",
            "baseline_passes": [False, False],
            "candidate_passes": [False, False],
        },
        {
            "transition": "UNCHANGED",
            "task_id": "keep-suite",
            "suite": "regression",
            "baseline_outcome": "PASS",
            "candidate_outcome": "PASS",
            "baseline_passes": [True, True],
            "candidate_passes": [True, True],
        },
    ]
    assert summarise(comps, phase="phase-1")["verdict"] == "NEGATIVE"
