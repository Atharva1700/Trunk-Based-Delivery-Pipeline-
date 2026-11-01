from sample_app.app import health, price_with_tax


def test_tax_rounds_half_up():
    assert price_with_tax(1000, 10) == 1100
    assert price_with_tax(5, 50) == 8  # 2.5 rounds up to 3


def test_negative_inputs_rejected():
    import pytest
    with pytest.raises(ValueError):
        price_with_tax(-1, 10)


def test_health():
    assert health() == {"status": "ok"}
