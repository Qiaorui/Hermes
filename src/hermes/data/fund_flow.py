"""Daily fund flow data."""

from hermes.api.eastmoney import em_get, parse_secid


def stock_fund_flow(code: str, days: int = 30) -> dict:
    """Get daily fund flow data. Returns dict with code, count, fund_flow."""
    days = min(days, 120)
    secid = parse_secid(code)
    url = f"http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt={days}&klt=101&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65&secid={secid}&ut=7eea3edcaed734bea9cbfc24409ed989"
    data = em_get(url)
    if not data or not data.get("data"):
        return {"error": "Failed to get fund flow", "code": code}

    klines = data["data"].get("klines", [])
    result = []
    for k in klines:
        parts = k.split(",")
        if len(parts) >= 9:
            result.append({
                "date": parts[0],
                "main_net_inflow": float(parts[1]),
                "small_net_inflow": float(parts[2]),
                "medium_net_inflow": float(parts[3]),
                "large_net_inflow": float(parts[4]),
                "super_large_net_inflow": float(parts[5]),
                "main_pct": float(parts[6]),
                "small_pct": float(parts[7]),
                "medium_pct": float(parts[8]),
            })

    return {"code": code, "count": len(result), "fund_flow": result}