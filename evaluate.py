"""Two evaluations of flaky-test quarantine.

1. Real: 40 commits through the actual pipeline (pytest, retries, SQLite). Ground truth: the
   flaky test in sample_app/flaky_net.py fails for some seeds; test_app tests never fail.
2. Simulated: 300 tests over 60 commits with planted behaviour and seeded retries. Labels:
   flaky (per-attempt failure rate >= 0.2), stable, or broken from a commit onward.

Writes results/evaluation.json.
"""
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from pipeline.quarantine import decide, refresh  # noqa: E402
from pipeline.run import run_commit  # noqa: E402
from pipeline.store import PipelineStore  # noqa: E402
from pipeline import metrics  # noqa: E402


def real_run(db_path, n_commits=40, n_after=20):
    store = PipelineStore(db_path)
    t0 = time.time()
    for seed in range(n_commits):
        sha = f"real{seed:04d}"
        store.add_commit(sha, time.time())
        quarantined = {r[0] for r in store.con.execute("SELECT test FROM quarantine")}
        run_commit(store, sha, seed, quarantined)
    decisions = refresh(store)
    blocked_before = store.con.execute(
        "SELECT COUNT(*) FROM stage_runs WHERE stage='test' AND status='failed'").fetchone()[0]
    # after quarantine: the same flaky test should no longer block
    after_block = 0
    for seed in range(n_commits, n_commits + n_after):
        sha = f"real{seed:04d}"
        store.add_commit(sha, time.time())
        quarantined = {r[0] for r in store.con.execute("SELECT test FROM quarantine")}
        res = run_commit(store, sha, seed, quarantined)
        after_block += res["test"]["status"] == "failed"
    out = {
        "commits_before_quarantine": n_commits,
        "test_stage_failures_before": blocked_before,
        "decisions": {k: {"quarantine": v[0], "flake_score": v[1]} for k, v in decisions.items()
                      if v[1] > 0 or v[0]},
        "commits_after_quarantine": n_after,
        "test_stage_blocks_after": after_block,
        "seconds_total": round(time.time() - t0, 2),
        "metrics": metrics.summary(store),
    }
    store.close()
    return out


def simulate(seed=20261101, n_tests=300, n_commits=60):
    rng = random.Random(seed)
    tests = {}
    for i in range(n_tests):
        r = rng.random()
        if r < 0.15:
            tests[i] = {"kind": "flaky", "p": rng.choice([0.2, 0.3, 0.4])}
        elif r < 0.20:
            tests[i] = {"kind": "low_flake", "p": 0.05}
        elif r < 0.23:
            tests[i] = {"kind": "broken", "from": rng.randint(5, 50)}
        else:
            tests[i] = {"kind": "stable", "p": 0.0}
    attempts = []
    for c in range(n_commits):
        sha = f"sim{c:03d}"
        for i, t in tests.items():
            if t["kind"] == "broken" and c >= t["from"]:
                results = [False, False, False]
            else:
                first_fail = rng.random() < t.get("p", 0.0)
                if not first_fail:
                    results = [True]
                else:
                    results = [False]
                    for _ in range(2):
                        ok = rng.random() >= t.get("p", 0.0)
                        results.append(ok)
                        if ok:
                            break
            attempts.append((sha, f"t{i}", results))
    decisions = decide(attempts)
    truth_flaky = {f"t{i}" for i, t in tests.items() if t["kind"] == "flaky"}
    pred = {t for t, (q, _) in decisions.items() if q}
    tp = len(pred & truth_flaky)
    fp = len(pred - truth_flaky)
    fn = len(truth_flaky - pred)
    broken_quarantined = [t for t in pred if tests[int(t[1:])]["kind"] == "broken"]
    return {
        "tests": n_tests, "commits": n_commits,
        "labels": {k: sum(1 for t in tests.values() if t["kind"] == k)
                   for k in ("flaky", "low_flake", "stable", "broken")},
        "quarantine_precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "quarantine_recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "tp": tp, "fp": fp, "fn": fn,
        "broken_tests_quarantined": len(broken_quarantined),
    }


if __name__ == "__main__":
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    db = results_dir / "pipeline.sqlite"
    db.unlink(missing_ok=True)
    real = real_run(str(db))
    out = {"real": real, "simulated": simulate()}
    (results_dir / "evaluation.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
