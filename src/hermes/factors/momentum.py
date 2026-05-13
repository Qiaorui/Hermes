"""Momentum/reversal factor — MOMENTUM (Barra CNE5S), A-share adapted.

Sub-factors:
  - Short-term reversal (5-day)
  - Medium-term trend (20-day)
  - Long-term conviction (60-day)
  - MA deviation: price vs MA20
  - Relative momentum: stock return vs CSI300

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

from hermes.data.kline import stock_kline
from hermes.data.valuation import stock_valuation_history
from hermes.data.market import market_index
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def _cum_return(klines: list, n: int) -> float | None:
    if len(klines) < n:
        return None
    recent = klines[-n:]
    start_close = recent[0]["close"]
    end_close = recent[-1]["close"]
    if start_close <= 0:
        return None
    return (end_close - start_close) / start_close * 100


def _index_cum_return(index_klines: list, n: int) -> float | None:
    if not index_klines or len(index_klines) < n:
        return None
    recent = index_klines[-n:]
    start = recent[0]["close"]
    end = recent[-1]["close"]
    if start <= 0:
        return None
    return (end - start) / start * 100


def momentum_factor(code: str, ctx=None) -> dict:
    """Compute momentum/reversal factor score (0-10). No fallback defaults."""
    if ctx is not None and ctx.has("kline"):
        kline = ctx.get("kline")
    else:
        kline = stock_kline(code, 120)
    if "error" in kline:
        return {"error": "Failed to get kline data", "code": code}

    klines = kline.get("klines", [])
    if len(klines) < 5:
        return {"error": "Insufficient kline data (need at least 5 days)", "code": code}

    ret_5d = _cum_return(klines, 5)
    ret_20d = _cum_return(klines, 20)
    ret_60d = _cum_return(klines, 60)

    scores = {}
    reasons = {}

    # Short-term reversal
    if ret_5d is None:
        scores["reversal"] = None
        reasons["reversal"] = "insufficient kline data for 5-day return"
    elif -5 <= ret_5d <= 5:
        scores["reversal"] = 8
    elif 5 < ret_5d <= 10:
        scores["reversal"] = 6
    elif 10 < ret_5d <= 15:
        scores["reversal"] = 4
    elif ret_5d > 15:
        scores["reversal"] = 2
    elif -5 > ret_5d >= -10:
        scores["reversal"] = 5
    elif -10 > ret_5d >= -20:
        scores["reversal"] = 4
    else:
        scores["reversal"] = 2

    # Medium-term trend
    if ret_20d is None:
        scores["trend"] = None
        reasons["trend"] = "insufficient kline data for 20-day return"
    elif ret_20d > 20:
        scores["trend"] = 9
    elif ret_20d > 10:
        scores["trend"] = 7
    elif ret_20d > 5:
        scores["trend"] = 6
    elif ret_20d > 0:
        scores["trend"] = 5
    elif ret_20d > -5:
        scores["trend"] = 4
    elif ret_20d > -10:
        scores["trend"] = 3
    elif ret_20d > -20:
        scores["trend"] = 2
    else:
        scores["trend"] = 1

    # Long-term conviction
    if ret_60d is None:
        scores["long"] = None
        reasons["long"] = "insufficient kline data for 60-day return"
    elif ret_60d > 30:
        scores["long"] = 8
    elif ret_60d > 15:
        scores["long"] = 7
    elif ret_60d > 5:
        scores["long"] = 6
    elif ret_60d > 0:
        scores["long"] = 5
    elif ret_60d > -10:
        scores["long"] = 4
    elif ret_60d > -20:
        scores["long"] = 3
    else:
        scores["long"] = 2

    # MA deviation
    if ctx is not None and ctx.has("valuation"):
        val = ctx.get("valuation")
    else:
        val = stock_valuation_history(code)
    if "error" not in val:
        price_vs_ma20 = val.get("price_vs_ma20")
        if price_vs_ma20 is not None:
            if -5 <= price_vs_ma20 <= 10:
                scores["deviation"] = 7
            elif 10 < price_vs_ma20 <= 20:
                scores["deviation"] = 4
            elif price_vs_ma20 > 20:
                scores["deviation"] = 2
            elif -10 <= price_vs_ma20 < -5:
                scores["deviation"] = 5
            elif -20 <= price_vs_ma20 < -10:
                scores["deviation"] = 6
            else:
                scores["deviation"] = 3
        else:
            scores["deviation"] = None
            reasons["deviation"] = "MA20 deviation data unavailable"
    else:
        scores["deviation"] = None
        reasons["deviation"] = "valuation history data unavailable"

    # Relative momentum: stock return vs CSI300
    mkt = market_index(120)
    csi300_klines = mkt.get("csi300", {}).get("klines", [])
    rel_20d = None

    if ret_20d is not None and csi300_klines and len(csi300_klines) >= 20:
        idx_ret_20d = _index_cum_return(csi300_klines, 20)
        if idx_ret_20d is not None:
            rel_20d = ret_20d - idx_ret_20d
            if rel_20d > 15:
                scores["relative"] = 9
            elif rel_20d > 8:
                scores["relative"] = 7
            elif rel_20d > 3:
                scores["relative"] = 6
            elif rel_20d > -3:
                scores["relative"] = 5
            elif rel_20d > -8:
                scores["relative"] = 4
            elif rel_20d > -15:
                scores["relative"] = 3
            else:
                scores["relative"] = 1
            # If idx_ret_20d is None but csi300 klines exist
        else:
            scores["relative"] = None
            reasons["relative"] = "CSI300 20-day return unavailable"
    else:
        scores["relative"] = None
        reasons["relative"] = "CSI300 kline data unavailable or insufficient"

    weights = {"reversal": 0.20, "trend": 0.25, "long": 0.20,
               "deviation": 0.15, "relative": 0.20}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for momentum factor", "code": code}

    return {
        "factor": "momentum",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            "return_5d_pct": round(ret_5d, 2) if ret_5d else None,
            "return_20d_pct": round(ret_20d, 2) if ret_20d else None,
            "return_60d_pct": round(ret_60d, 2) if ret_60d else None,
            "relative_20d_pct": round(rel_20d, 2) if rel_20d is not None else None,
            "price_vs_ma20_pct": val.get("price_vs_ma20") if "error" not in val else None,
            "reversal_score": scores.get("reversal"),
            "trend_score": scores.get("trend"),
            "long_score": scores.get("long"),
            "deviation_score": scores.get("deviation"),
            "relative_score": scores.get("relative"),
            "unavailable": unavailable_list(scores, reasons),
        },
    }