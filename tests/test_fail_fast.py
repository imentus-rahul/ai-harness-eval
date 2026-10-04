from eval.debug_break import candidate_must_pass


def test_good_candidate_must_pass():
    assert candidate_must_pass("good", "candidate")
    assert not candidate_must_pass("good", "baseline")
    assert not candidate_must_pass("bad", "candidate")
