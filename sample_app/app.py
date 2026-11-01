"""The deployed service: a tiny pricing function plus a health check."""


def price_with_tax(cents: int, rate_percent: int) -> int:
    if cents < 0 or rate_percent < 0:
        raise ValueError("negative input")
    return cents + (cents * rate_percent + 50) // 100


def health() -> dict:
    return {"status": "ok"}
