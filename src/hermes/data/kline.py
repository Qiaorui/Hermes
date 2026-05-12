"""Daily K-line data (OHLCV + change%)."""

from hermes.api.sina import fetch_kline, parse_klines


def stock_kline(code: str, days: int = 120) -> dict:
    """Get daily K-line data. Returns dict with code, count, klines."""
    days = min(days, 500)
    code_clean = code.strip()
    prefix = "sh" if code_clean.startswith("6") else "sz"
    symbol = f"{prefix}{code_clean}"

    raw = fetch_kline(symbol, days)
    if raw is None:
        return {"error": f"K-line fetch failed", "code": code}
    if not raw:
        return {"error": "No kline data returned", "code": code}

    klines = parse_klines(raw)
    return {"code": code, "count": len(klines), "klines": klines}