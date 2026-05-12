"""Market index data (Shanghai, Shenzhen, Chinext, STAR50, CSI300, CSI500, CSI1000)."""

from hermes.api.sina import fetch_kline, parse_klines

INDICES = {
    "shanghai": ("sh000001", "上证指数"),
    "shenzhen": ("sz399001", "深证成指"),
    "chinext": ("sz399006", "创业板指"),
    "star50": ("sh000688", "科创50"),
    "csi300": ("sh000300", "沪深300"),
    "csi500": ("sh000905", "中证500"),
    "csi1000": ("sh000852", "中证1000"),
}


def market_index(days: int = 60) -> dict:
    """Get recent market index data. Returns dict with all supported indices."""
    days = min(days, 500)
    result = {}

    for key, (symbol, label) in INDICES.items():
        raw = fetch_kline(symbol, days)
        if raw is None:
            continue
        parsed = parse_klines(raw)
        if parsed:
            latest = parsed[-1]
            result[key] = {
                "label": label,
                "symbol": symbol,
                "latest_close": latest["close"],
                "latest_date": latest["date"],
                "latest_change_pct": latest["change_pct"],
                "klines": parsed,
            }

    if not result:
        return {"error": "Failed to get market index data"}

    summary = {f"count_{k}": len(v["klines"]) for k, v in result.items()}
    return {**summary, **result}