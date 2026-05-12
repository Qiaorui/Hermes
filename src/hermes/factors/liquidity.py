"""Liquidity factor — LIQUIDTY (Barra CNE5S).

Sub-factors:
  - Turnover rate: higher → more liquid → better for entry/exit
  - Average daily volume (20-day): larger → more liquid
  - Volume trend: increasing volume → improving liquidity
"""

from hermes.data.quote import stock_quote
from hermes.data.kline import stock_kline


def liquidity_factor(code: str) -> dict:
    """Compute liquidity factor score (0-10). Higher liquidity = higher score."""
    quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote", "code": code}

    kline = stock_kline(code, 60)
    if "error" in kline:
        return {"error": "Failed to get kline data", "code": code}

    klines = kline.get("klines", [])
    if len(klines) < 20:
        return {"error": "Insufficient kline data", "code": code}

    # 1. Turnover rate score
    turnover = quote.get("turnover_rate")
    # A-share turnover: <1% very low, 1-3% moderate, 3-5% good, 5-10% high, >10% very active
    # Note: turnover_rate from quote can be negative (data issue), treat as 0
    turnover_val = max(0, turnover) if turnover is not None else 0

    if turnover_val < 0.5:
        turnover_score = 2
    elif turnover_val < 1:
        turnover_score = 4
    elif turnover_val < 2:
        turnover_score = 5
    elif turnover_val < 3:
        turnover_score = 6
    elif turnover_val < 5:
        turnover_score = 7
    elif turnover_val < 8:
        turnover_score = 8
    elif turnover_val < 12:
        turnover_score = 9
    else:
        turnover_score = 10

    # 2. Average volume (20-day)
    recent = klines[-20:]
    avg_volume = sum(k.get("volume", 0) for k in recent) / len(recent)

    # Volume scoring based on market cap context
    market_cap = quote.get("market_cap")
    if market_cap and avg_volume > 0:
        # Volume-to-market-cap ratio (higher = more liquid)
        vol_mc_ratio = avg_volume * quote.get("price", 1) / market_cap * 100
        if vol_mc_ratio < 0.1:
            volume_score = 2
        elif vol_mc_ratio < 0.3:
            volume_score = 4
        elif vol_mc_ratio < 0.5:
            volume_score = 5
        elif vol_mc_ratio < 1:
            volume_score = 7
        elif vol_mc_ratio < 2:
            volume_score = 8
        else:
            volume_score = 9
    else:
        volume_score = 5

    # 3. Volume trend: increasing volume = improving liquidity
    if len(klines) >= 40:
        vol_old = sum(k.get("volume", 0) for k in klines[-40:-20]) / 20
        vol_new = sum(k.get("volume", 0) for k in klines[-20:]) / 20
        if vol_old > 0:
            vol_change = (vol_new - vol_old) / vol_old * 100
            if vol_change > 50:
                trend_score = 9  # volume surging
            elif vol_change > 20:
                trend_score = 7
            elif vol_change > 0:
                trend_score = 5
            elif vol_change > -20:
                trend_score = 4
            elif vol_change > -50:
                trend_score = 3
            else:
                trend_score = 2
        else:
            trend_score = 5
    else:
        trend_score = 5

    # Composite: turnover 40%, volume 35%, trend 25%
    composite = round(turnover_score * 0.4 + volume_score * 0.35 + trend_score * 0.25, 1)

    return {
        "factor": "liquidity",
        "score": composite,
        "details": {
            "turnover_rate": turnover_val,
            "avg_volume_20d": round(avg_volume),
            "vol_change_pct": round(vol_change, 2) if len(klines) >= 40 else None,
            "turnover_score": round(turnover_score, 1),
            "volume_score": round(volume_score, 1),
            "trend_score": round(trend_score, 1),
        },
    }