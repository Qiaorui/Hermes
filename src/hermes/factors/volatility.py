"""Volatility factor — RESVOL (Barra CNE5S).

Sub-factors:
  - Daily return standard deviation (20-day): lower = higher score
  - Max drawdown (60-day): smaller drawdown = higher score
  - Days with extreme moves (>5% daily change): fewer = higher score
"""

import math
from hermes.data.kline import stock_kline


def volatility_factor(code: str) -> dict:
    """Compute volatility factor score (0-10). Lower volatility = higher score."""
    kline = stock_kline(code, 60)
    if "error" in kline:
        return {"error": "Failed to get kline data", "code": code}

    klines = kline.get("klines", [])
    if len(klines) < 20:
        return {"error": "Insufficient kline data", "code": code}

    # 1. Standard deviation of daily returns (20-day window)
    recent = klines[-20:]
    changes = [k["change_pct"] for k in recent if k["change_pct"] is not None]
    if not changes:
        return {"error": "No change_pct data", "code": code}

    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / len(changes)
    std_dev = math.sqrt(variance)

    # A-share daily std: <1% very low, 1-2% moderate, 2-3% elevated, >3% high
    if std_dev < 1.0:
        std_score = 9
    elif std_dev < 1.5:
        std_score = 7
    elif std_dev < 2.0:
        std_score = 5
    elif std_dev < 3.0:
        std_score = 3
    elif std_dev < 4.0:
        std_score = 2
    else:
        std_score = 1

    # 2. Max drawdown in available period
    closes = [k["close"] for k in klines]
    peak = closes[0]
    max_dd = 0
    for c in closes:
        if c > peak:
            peak = c
        dd = (peak - c) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # Smaller drawdown = better
    if max_dd < 5:
        dd_score = 9
    elif max_dd < 10:
        dd_score = 7
    elif max_dd < 15:
        dd_score = 5
    elif max_dd < 20:
        dd_score = 3
    elif max_dd < 30:
        dd_score = 2
    else:
        dd_score = 1

    # 3. Extreme move days (daily change > 5%)
    extreme_days = sum(1 for c in changes if abs(c) > 5)
    extreme_ratio = extreme_days / len(changes)

    if extreme_ratio < 0.05:
        extreme_score = 9
    elif extreme_ratio < 0.1:
        extreme_score = 7
    elif extreme_ratio < 0.2:
        extreme_score = 4
    elif extreme_ratio < 0.3:
        extreme_score = 2
    else:
        extreme_score = 1

    # Composite: std 40%, drawdown 35%, extreme 25%
    composite = round(std_score * 0.4 + dd_score * 0.35 + extreme_score * 0.25, 1)

    return {
        "factor": "volatility",
        "score": composite,
        "details": {
            "daily_std_pct": round(std_dev, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "extreme_days_5_pct": extreme_days,
            "extreme_ratio": round(extreme_ratio, 2),
            "std_score": round(std_score, 1),
            "dd_score": round(dd_score, 1),
            "extreme_score": round(extreme_score, 1),
        },
    }