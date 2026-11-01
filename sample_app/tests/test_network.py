from sample_app.flaky_net import upstream_reachable


def test_upstream_is_reachable():
    # flaky by design: fails for some RUN_SEED values (see flaky_net.py)
    assert upstream_reachable()
