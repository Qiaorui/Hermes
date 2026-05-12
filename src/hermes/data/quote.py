"""Real-time stock quote with valuation metrics."""

from hermes.api.eastmoney import em_get, parse_secid


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
        "price": d.get("f43", 0) / 100,
        "high": d.get("f44", 0) / 100,
        "low": d.get("f45", 0) / 100,
        "open": d.get("f46", 0) / 100,
        "volume": d.get("f47", 0),
        "amount": d.get("f48", 0),
        "turnover_rate": d.get("f55", 0),
        "pe_dynamic": d.get("f162", 0) / 100,
        "pe_static": d.get("f163", 0) / 100,
        "pb": d.get("f23", 0) / 100 if d.get("f23") else None,
        "ps": d.get("f167", 0) / 100,
        "market_cap": d.get("f84", 0),
        "total_shares": d.get("f116", 0),
        "circulating_shares": d.get("f117", 0),
        "revenue_yoy": d.get("f169", 0) / 100 if d.get("f169") else None,
        "profit_yoy": d.get("f170", 0) / 100 if d.get("f170") else None,
        "industry": d.get("f100", ""),
    }