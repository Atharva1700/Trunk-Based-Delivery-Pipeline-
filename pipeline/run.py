"""Local trunk pipeline: lint, test (retries, quarantine), container build, local staging copy.

Container build runs only if a Docker daemon answers; otherwise it is recorded as 'skipped'.
The staging step copies the app into results/staging. It does not reach a real environment.

Usage: python -m pipeline.run --sha <sha> --seed <n> [--db results/pipeline.sqlite]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline.store import PipelineStore

ROOT = Path(__file__).resolve().parent.parent
RETRIES = 2


def sh(cmd, env=None):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)


def stage_lint():
    r = sh([sys.executable, "-m", "pyflakes", "sample_app", "pipeline"])
    return "passed" if r.returncode == 0 else "failed"


def run_tests(sha, seed, store, quarantined):
    """Run the suite, retry each failure up to RETRIES times with a new seed, store every attempt.

    Returns 'failed' only for a failure that survives its retries and is not quarantined.
    """
    junit = ROOT / "results" / "junit.xml"
    sh([sys.executable, "-m", "pytest", "-q", "sample_app/tests", f"--junitxml={junit}",
        "-p", "no:cacheprovider"], env={**os.environ, "RUN_SEED": f"{seed}:0"})
    outcomes, paths = {}, {}
    for case in ET.parse(junit).getroot().iter("testcase"):
        test_id = f"{case.get('classname')}::{case.get('name')}"
        ok = case.find("failure") is None and case.find("error") is None
        outcomes[test_id] = [ok]
        paths[test_id] = case.get("classname").replace(".", "/") + ".py"
    for test_id in list(outcomes):
        if outcomes[test_id][0]:
            continue
        for k in range(1, RETRIES + 1):
            env = {**os.environ, "RUN_SEED": f"{seed}:{k}"}
            r = sh([sys.executable, "-m", "pytest", "-q", f"{paths[test_id]}::{test_id.split('::')[1]}",
                    "-p", "no:cacheprovider"], env=env)
            outcomes[test_id].append(r.returncode == 0)
            if r.returncode == 0:
                break
    for test_id, results in outcomes.items():
        for i, passed in enumerate(results):
            store.add_attempt(sha, test_id, i, passed)
    blocking = [t for t, res in outcomes.items()
                if res[-1] is False and t not in quarantined]
    return "failed" if blocking else "passed"


def stage_build():
    if sh(["docker", "info"]).returncode != 0:
        return "skipped"
    return "passed" if sh(["docker", "build", "-t", "sample-app", "."]).returncode == 0 else "failed"


def stage_staging(sha):
    target = ROOT / "results" / "staging"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(ROOT / "sample_app", target / "sample_app",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    (target / "VERSION").write_text(sha)
    return "passed"


def run_commit(store, sha, seed, quarantined):
    timings = {}

    def timed(name, fn):
        t0 = time.perf_counter()
        status = fn()
        secs = time.perf_counter() - t0
        timings[name] = {"status": status, "seconds": round(secs, 3)}
        store.add_stage(sha, name, status, secs)
        return status

    timed("lint", stage_lint)
    tests = timed("test", lambda: run_tests(sha, seed, store, quarantined))
    timed("build", stage_build)
    if tests == "passed" and timings["lint"]["status"] == "passed":
        timed("deploy_staging", lambda: stage_staging(sha))
        store.add_deploy(sha, "staging", time.time())
    return timings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "results" / "pipeline.sqlite"))
    ap.add_argument("--sha", required=True)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    store = PipelineStore(args.db)
    store.add_commit(args.sha, time.time())
    quarantined = {r[0] for r in store.con.execute("SELECT test FROM quarantine")}
    print(json.dumps(run_commit(store, args.sha, args.seed, quarantined), indent=2))
    store.close()


if __name__ == "__main__":
    main()
