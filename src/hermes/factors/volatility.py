"""Volatility factor — RESVOL (Barra CNE5S), market-relative.

Sub-factors:
  - Daily return std (20-day): lower = higher score
  - Max drawdown (60-day): smaller drawdown = higher score
  - Extreme move frequency (>5% daily change): fewer = higher score
  - Relative volatility: stock std vs CSI300 std

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

import math
from hermes.data.kline import stock_kline
from hermes.data.market import market_index
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def volatility_factor(code: str) -> dict:
    """Compute volatility factor score (0-10). No fallback defaults."""
    kline = stock_kline(code, 60)
    if "error" in kline:
        return {"error": "Failed to get kline data", "code": code}

    klines = kline.get("klines", [])
    if len(klines) < 20:
        return {"error": "Insufficient kline data", "code": code}

    scores = {}
    reasons = {}

    # 1. Daily return std (20-day)
    recent = klines[-20:]
    changes = [k["change_pct"] for k in recent if k["change_pct"] is not None]
    if not changes:
        return {"error": "No change_pct data", "code": code}

    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / len(changes)
    std_dev = math.sqrt(variance)

    if std_dev < 1.0:
        scores["std"] = 9
    elif std_dev < 1.5:
        scores["std"] = 7
    elif std_dev < 2.0:
        scores["std"] = 5
    elif std_dev < 3.0:
        scores["std"] = 3
    elif std_dev < 4.0:
        scores["std"] = 2
    else:
        scores["std"] = 1

    # 2. Max drawdown
    closes = [k["close"] for k in klines]
    peak = closes[0]
    max_dd = 0
    for c in closes:
        if c > peak:
            peak = c
        dd = (peak - c) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)

    if max_dd < 5:
        scores["dd"] = 9
    elif max_dd < 10:
        scores["dd"] = 7
    elif max_dd < 15:
        scores["dd"] = 5
    elif max_dd < 20:
        scores["dd"] = 3
    elif max_dd < 30:
        scores["dd"] = 2
    else:
        scores["dd"] = 1

    # 3. Extreme move days
    extreme_days = sum(1 for c in changes if abs(c) > 5)
    extreme_ratio = extreme_days / len(changes)

    if extreme_ratio < 0.05:
        scores["extreme"] = 9
    elif extreme_ratio < 0.1:
        scores["extreme"] = 7
    elif extreme_ratio < 0.2:
        scores["extreme"] = 4
    elif extreme_ratio < 0.3:
        scores["extreme"] = 2
    else:
        scores["extreme"] = 1

    # 4. Relative volatility: stock std vs CSI300 std
    mkt = market_index(60)
    csi300_klines = mkt.get("csi300", {}).get("klines", [])
    relative_ratio = None

    if csi300_klines and len(csi300_klines) >= 20:
        idx_recent = csi300_klines[-20:]
        idx_changes = [k["change_pct"] for k in idx_recent if k["change_pct"] is not None]
        if idx_changes:
            idx_mean = sum(idx_changes) / len(idx_changes)
            idx_var = sum((c - idx_mean) ** 2 for c in idx_changes) / len(idx_changes)
            idx_std = math.sqrt(idx_var)
            if idx_std > 0:
                relative_ratio = std_dev / idx_std
                if relative_ratio < 0.5:
                    scores["relative"] = 9
                elif relative_ratio < 0.8:
                    scores["relative"] = 7
                elif relative_ratio < 1.2:
                    scores["relative"] = 5
                elif relative_ratio < 1.5:
                    scores["relative"] = 4
                elif relative_ratio < 2.0:
                    scores["relative"] = 3
                elif relative_ratio < 3.0:
                    scores["relative"] = 2
                else:
                    scores["relative"] = 1
            else:
                scores["relative"] = None
                reasons["relative"] = "CSI300 std is zero"
        else:
            scores["relative"] = None
            reasons["relative"] = "CSI300 change_pct data unavailable"
    else:
        scores["relative"] = None
        reasons["relative"] = "CSI300 kline data unavailable or insufficient"

    weights = {"std": 0.30, "dd": 0.30, "extreme": 0.20, "relative": 0.20}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for volatility factor", "code": code}

    return {
        "factor": "volatility",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            "daily_std_pct": round(std_dev, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "extreme_days_5_pct": extreme_days,
            "extreme_ratio": round(extreme_ratio, 2),
            "relative_vol_ratio": round(relative_ratio, 2) if relative_ratio else None,
            "std_score": scores.get("std"),
            "dd_score": scores.get("dd"),
            "extreme_score": scores.get("extreme"),
            "relative_score": scores.get("relative"),
            "unavailable": unavailable_list(scores, reasons),
        },
    }