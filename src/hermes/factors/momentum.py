"""Momentum/reversal factor — MOMENTUM (Barra CNE5S), adapted for A-share.

A-share specific: cross-sectional momentum is weak/negative, but short-term
reversal and medium-term trend are useful signals.

Sub-factors:
  - Short-term reversal (5-day): recent sharp rise → reversal risk (score low)
  - Medium-term trend (20-day): sustained rise → momentum (score high)
  - Long-term trend (60-day): persistent direction → conviction
  - MA deviation: price vs MA20, extreme deviation → overbought/oversold signal
"""

from hermes.data.kline import stock_kline
from hermes.data.valuation import stock_valuation_history


def momentum_factor(code: str) -> dict:
    """Compute momentum/reversal factor score (0-10) for A-share."""
    kline = stock_kline(code, 120)
    if "error" in kline:
        return {"error": "Failed to get kline data", "code": code}

    klines = kline.get("klines", [])
    if len(klines) < 20:
        return {"error": "Insufficient kline data", "code": code}

    # Calculate cumulative returns over different windows
    def _cum_return(n: int) -> float | None:
        """Cumulative return over last n trading days."""
        if len(klines) < n:
            return None
        recent = klines[-n:]
        start_close = recent[0]["close"]
        end_close = recent[-1]["close"]
        if start_close <= 0:
            return None
        return (end_close - start_close) / start_close * 100

    ret_5d = _cum_return(5)
    ret_20d = _cum_return(20)
    ret_60d = _cum_return(60)

    # Short-term reversal score: if 5-day return is extreme, reversal risk
    # Moderate positive (2-8%) → decent momentum, not overbought → score 7-8
    # Extreme positive (>15%) → likely reversal → score low
    # Moderate negative → oversold bounce opportunity → score 5-6
    if ret_5d is None:
        reversal_score = 5
    elif -5 <= ret_5d <= 5:
        reversal_score = 8  # stable, no extreme
    elif 5 < ret_5d <= 10:
        reversal_score = 6  # decent short-term momentum
    elif 10 < ret_5d <= 15:
        reversal_score = 4  # getting overbought
    elif ret_5d > 15:
        reversal_score = 2  # likely reversal
    elif -5 > ret_5d >= -10:
        reversal_score = 5  # oversold, potential bounce
    elif -10 > ret_5d >= -20:
        reversal_score = 4  # deep correction
    else:
        reversal_score = 2  # crash zone

    # Medium-term trend score: sustained direction
    if ret_20d is None:
        trend_score = 5
    elif ret_20d > 20:
        trend_score = 9  # very strong upward trend
    elif ret_20d > 10:
        trend_score = 7
    elif ret_20d > 5:
        trend_score = 6
    elif ret_20d > 0:
        trend_score = 5
    elif ret_20d > -5:
        trend_score = 4
    elif ret_20d > -10:
        trend_score = 3
    elif ret_20d > -20:
        trend_score = 2
    else:
        trend_score = 1

    # Long-term conviction: 60-day direction
    if ret_60d is None:
        long_score = 5
    elif ret_60d > 30:
        long_score = 8
    elif ret_60d > 15:
        long_score = 7
    elif ret_60d > 5:
        long_score = 6
    elif ret_60d > 0:
        long_score = 5
    elif ret_60d > -10:
        long_score = 4
    elif ret_60d > -20:
        long_score = 3
    else:
        long_score = 2

    # MA deviation score: moderate deviation is healthy, extreme is risky
    val = stock_valuation_history(code)
    if "error" not in val:
        price_vs_ma20 = val.get("price_vs_ma20", 0)
        # 0-10% deviation → healthy trend → 7-8
        # 10-20% → stretched → 4-5
        # >20% → extreme → 2
        # <0 (below MA) → potential bottom → depends on context
        if -5 <= price_vs_ma20 <= 10:
            deviation_score = 7
        elif 10 < price_vs_ma20 <= 20:
            deviation_score = 4
        elif price_vs_ma20 > 20:
            deviation_score = 2
        elif -10 <= price_vs_ma20 < -5:
            deviation_score = 5
        elif -20 <= price_vs_ma20 < -10:
            deviation_score = 6  # below MA, potential buy
        else:
            deviation_score = 3
    else:
        deviation_score = 5

    # Composite: reversal 25%, trend 30%, long 25%, deviation 20%
    composite = round(
        reversal_score * 0.25 + trend_score * 0.30 + long_score * 0.25 + deviation_score * 0.20, 1
    )

    return {
        "factor": "momentum",
        "score": composite,
        "details": {
            "return_5d_pct": round(ret_5d, 2) if ret_5d else None,
            "return_20d_pct": round(ret_20d, 2) if ret_20d else None,
            "return_60d_pct": round(ret_60d, 2) if ret_60d else None,
            "price_vs_ma20_pct": val.get("price_vs_ma20") if "error" not in val else None,
            "reversal_score": round(reversal_score, 1),
            "trend_score": round(trend_score, 1),
            "long_score": round(long_score, 1),
            "deviation_score": round(deviation_score, 1),
        },
    }