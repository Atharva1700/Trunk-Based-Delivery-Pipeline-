import time

from pipeline import metrics
from pipeline.quarantine import refresh
from pipeline.store import PipelineStore


def test_refresh_writes_quarantine_from_stored_attempts(tmp_path):
    store = PipelineStore(str(tmp_path / "p.sqlite"))
    for i in range(20):
        sha = f"s{i:03d}"
        store.add_commit(sha, time.time() + i * 0.001)
        store.add_attempt(sha, "t", 0, False)
        store.add_attempt(sha, "t", 1, True)
    decisions = refresh(store)
    assert decisions["t"][0] is True
    assert store.con.execute("SELECT test FROM quarantine").fetchall() == [("t",)]
    store.close()


def test_metrics_lead_time_and_frequency(tmp_path):
    store = PipelineStore(str(tmp_path / "m.sqlite"))
    day = 86400
    for i, lag in enumerate([60, 120, 180]):
        store.add_commit(f"c{i}", 1000.0 + i * day)
        store.add_deploy(f"c{i}", "staging", 1000.0 + i * day + lag)
    s = metrics.summary(store)
    assert s["deployed_commits"] == 3
    assert s["lead_time_seconds"]["median"] == 120
    assert abs(s["deployments_per_day"] - 1.5) < 0.01  # 3 deploys over 2 days
    store.close()
