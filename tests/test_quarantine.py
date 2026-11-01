from pipeline.quarantine import MIN_OBSERVATIONS, THRESHOLD, decide


def seq(test, results_per_commit, prefix="c"):
    return [(f"{prefix}{i:03d}", test, r) for i, r in enumerate(results_per_commit)]


def test_consistent_failure_is_never_quarantined():
    # fails every attempt on every commit: a real break, not flakiness
    d = decide(seq("t", [[False, False, False]] * 20))
    assert d["t"] == (False, 0.0)


def test_fail_then_pass_on_retry_is_flaky_evidence():
    d = decide(seq("t", [[False, True]] * 20))
    assert d["t"][0] is True and d["t"][1] == 1.0


def test_stable_passing_test_is_not_quarantined():
    d = decide(seq("t", [[True]] * 20))
    assert d["t"] == (False, 0.0)


def test_too_few_observations_block_quarantine():
    d = decide(seq("t", [[False, True]] * (MIN_OBSERVATIONS - 1)))
    assert d["t"][0] is False


def test_score_below_threshold_is_not_quarantined():
    # 1 flaky commit out of 20 = 0.05, below THRESHOLD 0.10
    rs = [[True]] * 19 + [[False, True]]
    d = decide(seq("t", rs))
    assert d["t"][1] == 0.05 and d["t"][0] is False


def test_threshold_is_inclusive():
    n = int(round(THRESHOLD * 20))  # 2 of 20 = 0.10 exactly
    rs = [[False, True]] * n + [[True]] * (20 - n)
    assert decide(seq("t", rs))["t"][0] is True


def test_window_only_uses_latest_commits():
    # old flakiness outside the 30-commit window must not count
    old = [[False, True]] * 20
    recent = [[True]] * 30
    d = decide(seq("t", old + recent))
    assert d["t"] == (False, 0.0)
