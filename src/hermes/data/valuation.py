"""Historical PE/PB percentile for valuation context."""

from hermes.data.quote import stock_quote
from hermes.data.kline import stock_kline


def stock_valuation_history(code: str) -> dict:
    """Get historical valuation percentile. Calculates from K-line + quote data."""
    quote = stock_quote(code)
    if "error" in quote:
        return {"error": quote["error"], "code": code}

    pe_now = quote.get("pe_dynamic")
    pb_now = quote.get("pb")
    ps_now = quote.get("ps")
    price_now = quote.get("price")

    kline_data = stock_kline(code, days=250)
    if "error" in kline_data:
        return {"error": kline_data["error"], "code": code}

    klines = kline_data.get("klines", [])
    if not klines:
        return {"error": "No kline data", "code": code}

    prices = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]

    price_52w_high = max(highs)
    price_52w_low = min(lows)
    price_avg = sum(prices) / len(prices)

    if price_52w_high > price_52w_low:
        price_pct = round((price_now - price_52w_low) / (price_52w_high - price_52w_low) * 100, 1)
    else:
        price_pct = 50.0

    recent_5 = prices[-5:] if len(prices) >= 5 else prices
    recent_20 = prices[-20:] if len(prices) >= 20 else prices
    avg_5 = sum(recent_5) / len(recent_5)
    avg_20 = sum(recent_20) / len(recent_20)

    return {
        "code": code,
        "name": quote.get("name", ""),
        "price_now": price_now,
        "pe_dynamic": pe_now,
        "pb": pb_now,
        "ps": ps_now,
        "market_cap_billion": quote.get("market_cap", 0),
        "price_52w_high": price_52w_high,
        "price_52w_low": price_52w_low,
        "price_avg_250d": round(price_avg, 2),
        "price_pct_in_range": price_pct,
        "ma5": round(avg_5, 2),
        "ma20": round(avg_20, 2),
        "price_vs_ma5": round(price_now / avg_5 * 100 - 100, 2) if price_now and avg_5 else None,
        "price_vs_ma20": round(price_now / avg_20 * 100 - 100, 2) if price_now and avg_20 else None,
        "revenue_yoy": quote.get("revenue_yoy"),
        "profit_yoy": quote.get("profit_yoy"),
    }