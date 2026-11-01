"""A deliberately flaky dependency check. Its outcome depends on RUN_SEED, so each pipeline
run sees a different result. It is used to exercise retries and quarantine end to end."""
import os
import random


def upstream_reachable(flake_rate: float = 0.3) -> bool:
    seed = os.environ.get("RUN_SEED", "0")
    return random.Random(seed).random() >= flake_rate
