# Trunk-Based Delivery Pipeline (prototype)

A local trunk pipeline in Python with a SQLite store. It runs lint, tests with retries and
flaky-test quarantine, an optional container build, and a copy to a local staging folder. It
records deployments and delivery metrics. Some parts of the resume bullet cannot be measured
here, and those are marked below.

## What was measured, and what was not

| Claim in the resume bullet | Status |
|---|---|
| Automated linting | **Built and run.** pyflakes stage, 60 runs, all passed. |
| Container builds | **Not run.** `Dockerfile` written; no Docker daemon in the sandbox, so the build stage is recorded as `skipped`. |
| Staging deployments | **Simulated only.** The "deploy" copies the app into `results/staging`. No real environment exists here. |
| Automated flaky-test quarantine | **Built and measured.** Real: the flaky test is quarantined after 40 commits. Simulated history: precision 0.96, recall 0.98. |
| Lead time and deployment frequency tracked | **Built.** The formulas are tested. The values in this build come from local runs and simulation, not from a real delivery history. |
| Sub-8-minute commit-to-staging latency | **Not measured.** The sandbox has no GitHub runner and no staging environment. Local stage timings are below, but they are not that metric. |
| GitHub Actions and Docker Compose | **Written, not run.** `.github/workflows/trunk.yml` and `docker-compose.yml`. |

## Measured numbers

Quarantine, real pipeline (40 commits, seeds 0–39; `results/evaluation.json`):

- The flaky test (`sample_app/tests/test_network.py`) got flake score 0.33 and was quarantined.
- The first 40 commits had 0 test-stage failures, because retries with a new seed rescued every
  failure. No real break was present to test blocking.
- 20 commits after quarantine: 0 test-stage blocks.

Quarantine, simulated history (300 tests, 60 commits, seeded):

| Labels | Precision | Recall | Broken tests quarantined |
|---|---|---|---|
| 47 flaky (per-attempt failure rate 0.2–0.4), 229 stable, 17 low-flake (0.05), 7 broken from some commit | **0.958** (46 TP, 2 FP) | **0.979** (1 FN) | **0** |

Local stage timings, 60 runs (median, seconds): lint 0.048, test 0.48 (max 1.5, with retries),
build 0.047 (skipped), deploy to local folder 0.001.

Delivery metrics on the 60 local runs: the "deployments per day" figure (about 118,000) is correct
arithmetic over a 44-second window and is meaningless as a delivery rate. The lead time (median
0.58 s) measures local pipeline time from the start of the run, not commit-to-staging time.

## How quarantine works

- A failed attempt followed by a pass on a retry (new seed each time) is flaky evidence for that
  commit.
- A test that fails every attempt is a real break. It is never quarantined, because that would
  hide a real failure.
- Over the last 30 commits, a test is quarantined when it was observed in at least 10 commits,
  its flake score is at least 0.10, and it passed at least once.
- Quarantined tests still run and are still recorded, but they do not block.

The thresholds (30, 10, 0.10) were set before the evaluation and not tuned against it.

## Limits

- **The real flaky test is a single test with one seed rule.** Its failure rate depends on
  `RUN_SEED`, not on real timing or network behaviour. It shows the mechanism works, not the
  rate of flakiness in a real suite.
- **The simulated retries are independent.** Real flakiness is often correlated across retries
  (same host, same time), which would make retries rescue less than they do here.
- **Staging is a folder copy**, so the staging stage proves nothing about deployment health.
- **Container build, GitHub Actions and Docker Compose were not run.**
- **Thresholds are not tuned to real data.** They were chosen once and kept.

## Run it

```
pip install pyflakes pytest
python -m pytest -q tests                   # 9 tests
python -m pytest -q sample_app/tests        # the app's tests; the network test is flaky by design
python -m pipeline.run --sha $(git rev-parse HEAD 2>/dev/null || echo local) --seed 7
python evaluate.py                          # real 40-commit run plus simulated history
```

## Files

- `pipeline/store.py`: SQLite schema (commits, stage runs, deployments, test attempts, quarantine)
- `pipeline/run.py`: lint, test with retries, build (skipped without Docker), staging copy
- `pipeline/quarantine.py`: flake score, decision rule, refresh from the store
- `pipeline/metrics.py`: lead time and deployment frequency
- `sample_app/`: the deployed app, its tests, and the flaky network check
- `evaluate.py`: real and simulated evaluation
- `tests/`: quarantine rule and store/metrics tests
- `results/evaluation.json`, `results/pipeline.sqlite`
- `Dockerfile` (not built), `docker-compose.yml` (not run), `.github/workflows/trunk.yml` (not run)
