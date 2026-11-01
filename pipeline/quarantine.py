"""Flaky-test quarantine.

A commit shows flakiness for a test when a failed attempt is followed by a pass on a retry
(same commit, same code). A test that fails every attempt is a real break, not flaky, and is
never quarantined: quarantining it would hide a real failure.

Flake score = commits with flaky evidence / commits where the test ran, over the last WINDOW
commits. A test is quarantined when it has at least MIN_OBSERVATIONS commits in the window and
score >= THRESHOLD, and it passed at least once in the window.
"""
from collections import defaultdict

WINDOW = 30
MIN_OBSERVATIONS = 10
THRESHOLD = 0.10


def _is_flaky(results):
    """A failed attempt followed by a pass on a retry."""
    return False in results and True in results[results.index(False):]


def decide(attempts_in_order):
    """attempts_in_order: list of (sha, test, [bool...]) in commit order. Returns {test: (quarantine, score)}."""
    per = defaultdict(lambda: defaultdict(list))
    order = []
    for sha, test, results in attempts_in_order:
        if sha not in order:
            order.append(sha)
        per[test][sha] = results
    decisions = {}
    window = set(order[-WINDOW:])
    for test, by_sha in per.items():
        seen = [s for s in by_sha if s in window]
        if len(seen) < MIN_OBSERVATIONS:
            decisions[test] = (False, 0.0)
            continue
        flaky_count = sum(1 for s in seen if _is_flaky(by_sha[s]))
        passed_once = any(True in by_sha[s] for s in seen)
        score = flaky_count / len(seen)
        decisions[test] = (passed_once and score >= THRESHOLD, round(score, 3))
    return decisions


def refresh(store):
    """Recompute quarantine from stored attempts and write it back. Returns the decisions."""
    rows = store.con.execute(
        "SELECT ta.sha, ta.test, ta.attempt, ta.passed FROM test_attempts ta "
        "JOIN commits c ON c.sha = ta.sha ORDER BY c.committed_at, ta.sha, ta.test, ta.attempt").fetchall()
    grouped = {}
    order = []
    for sha, test, attempt, passed in rows:
        key = (sha, test)
        if key not in grouped:
            grouped[key] = []
            if sha not in order:
                order.append(sha)
        grouped[key].append(bool(passed))
    seq = [(sha, test, res) for (sha, test), res in grouped.items()]
    decisions = decide(seq)
    store.con.execute("DELETE FROM quarantine")
    import time
    for test, (q, score) in decisions.items():
        if q:
            store.con.execute("INSERT INTO quarantine VALUES (?, ?, ?)", (test, time.time(), score))
    store.con.commit()
    return decisions
