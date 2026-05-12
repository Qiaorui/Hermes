"""Real-time stock quote with valuation metrics."""

from hermes.api.eastmoney import em_get, parse_secid


def _val(d: dict, key: str) -> float | int | None:
    """Extract a value from API data, returning None if missing instead of 0."""
    raw = d.get(key)
    if raw is None or raw == "-":
        return None
    try:
        v = float(raw)
        return int(v) if v == int(v) else v
    except (ValueError, TypeError):
        return None


def _fen(d: dict, key: str) -> float | None:
    """Convert fen unit to yuan (÷100), return None if missing."""
    v = _val(d, key)
    return v / 100 if v is not None else None


def _pct(d: dict, key: str) -> float | None:
    """Convert 1/100-percent to percent (÷100), return None if missing."""
    v = _val(d, key)
    return v / 100 if v is not None else None


def stock_quote(code: str) -> dict:
    """Get real-time stock quote. Returns dict with price, PE, PB, PS, market cap, YoY etc."""
    secid = parse_secid(code)
    url = f"http://push2.eastmoney.com/api/qt/stock/get?ut=bd_1_dac_1_12345&fields=f9,f23,f37,f43,f44,f45,f46,f47,f48,f50,f55,f57,f58,f84,f100,f116,f117,f152,f162,f163,f167,f168,f169,f170,f171,f177&secid={secid}"
    data = em_get(url)
    if not data or not data.get("data"):
        return {"error": "Failed to get quote", "code": code}

    d = data["data"]
    return {
        "code": d.get("f57", code),
        "name": d.get("f58", ""),
        "price": _fen(d, "f43"),
        "high": _fen(d, "f44"),
        "low": _fen(d, "f45"),
        "open": _fen(d, "f46"),
        "volume": _val(d, "f47"),
        "amount": _val(d, "f48"),
        "turnover_rate": _val(d, "f55"),
        "pe_dynamic": _fen(d, "f162"),
        "pe_static": _fen(d, "f163"),
        "pb": _fen(d, "f23"),
        "ps": _fen(d, "f167"),
        "market_cap": _val(d, "f84"),
        "total_shares": _val(d, "f116"),
        "circulating_shares": _val(d, "f117"),
        "revenue_yoy": _pct(d, "f169"),
        "profit_yoy": _pct(d, "f170"),
        "industry": d.get("f100", ""),
    }