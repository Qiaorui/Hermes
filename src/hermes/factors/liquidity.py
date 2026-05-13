"""Liquidity factor — LIQUIDTY (Barra CNE5S), industry-neutralized.

Sub-factors:
  - Turnover rate: industry-relative percentile when available
  - Average daily volume (20-day): volume/market-cap ratio
  - Volume trend: increasing volume → improving liquidity

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

from hermes.data.quote import stock_quote
from hermes.data.kline import stock_kline
from hermes.data.industry import get_industry_median_from_quote, industry_percentile
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def _turnover_score(turnover: float) -> float | None:
    """Absolute turnover scoring. Returns None when turnover is None or <= 0."""
    if turnover is None or turnover <= 0:
        return None
    if turnover < 0.5:
        return 2
    elif turnover < 1:
        return 4
    elif turnover < 2:
        return 5
    elif turnover < 3:
        return 6
    elif turnover < 5:
        return 7
    elif turnover < 8:
        return 8
    elif turnover < 12:
        return 9
    else:
        return 10


def liquidity_factor(code: str, ctx=None) -> dict:
    """Compute liquidity factor score (0-10). Industry-neutralized, no fallbacks."""
    if ctx is not None and ctx.has("quote"):
        quote = ctx.get("quote")
    else:
        quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote", "code": code}

    if ctx is not None and ctx.has("kline"):
        kline_raw = ctx.get("kline")
        klines_raw = kline_raw.get("klines", [])
        # ctx stores kline with 120 days; liquidity needs 60 — take last 60 entries
        klines_truncated = klines_raw[-60:] if len(klines_raw) > 60 else klines_raw
        kline = {**kline_raw, "klines": klines_truncated}
    else:
        kline = stock_kline(code, 60)
    if "error" in kline:
        return {"error": "Failed to get kline data", "code": code}

    klines = kline.get("klines", [])
    if len(klines) < 20:
        return {"error": "Insufficient kline data", "code": code}

    # Get industry benchmarks
    ind_bench = get_industry_median_from_quote(quote)
    ind_name = ind_bench.get("industry") if ind_bench else None

    scores = {}
    reasons = {}

    # 1. Turnover rate: industry-relative percentile, None when data unavailable
    turnover = quote.get("turnover_rate")

    if turnover is not None and turnover > 0:
        if ind_name:
            to_pct = industry_percentile(turnover, ind_name, "turnover")
            scores["turnover"] = to_pct / 10 if to_pct is not None else None
            if scores["turnover"] is None:
                reasons["turnover"] = "industry turnover median unavailable"
        else:
            scores["turnover"] = None
            reasons["turnover"] = "industry benchmark unavailable"
    else:
        scores["turnover"] = None
        reasons["turnover"] = "turnover rate data unavailable or zero"

    # 2. Average volume (20-day): volume/market-cap ratio
    recent = klines[-20:]
    avg_volume = sum(k.get("volume", 0) for k in recent) / len(recent)
    market_cap = quote.get("market_cap")
    vol_mc_ratio = None

    if market_cap is not None and market_cap > 0 and avg_volume > 0:
        price = quote.get("price")
        if price and price > 0:
            vol_mc_ratio = avg_volume * price / market_cap * 100
            if vol_mc_ratio < 0.1:
                scores["volume"] = 2
            elif vol_mc_ratio < 0.3:
                scores["volume"] = 4
            elif vol_mc_ratio < 0.5:
                scores["volume"] = 5
            elif vol_mc_ratio < 1:
                scores["volume"] = 7
            elif vol_mc_ratio < 2:
                scores["volume"] = 8
            else:
                scores["volume"] = 9
        else:
            scores["volume"] = None
            reasons["volume"] = "price data unavailable"
    else:
        scores["volume"] = None
        reasons["volume"] = "market cap or volume data unavailable"

    # 3. Volume trend
    vol_change = None
    if len(klines) >= 40:
        vol_old = sum(k.get("volume", 0) for k in klines[-40:-20]) / 20
        vol_new = sum(k.get("volume", 0) for k in klines[-20:]) / 20
        if vol_old > 0:
            vol_change = (vol_new - vol_old) / vol_old * 100
            if vol_change > 50:
                scores["trend"] = 9
            elif vol_change > 20:
                scores["trend"] = 7
            elif vol_change > 0:
                scores["trend"] = 5
            elif vol_change > -20:
                scores["trend"] = 4
            elif vol_change > -50:
                scores["trend"] = 3
            else:
                scores["trend"] = 2
        else:
            scores["trend"] = None
            reasons["trend"] = "prior 20-day volume is zero"
    else:
        scores["trend"] = None
        reasons["trend"] = "insufficient kline data (need 40 days)"

    weights = {"turnover": 0.40, "volume": 0.35, "trend": 0.25}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for liquidity factor", "code": code}

    return {
        "factor": "liquidity",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            "turnover_rate": turnover,
            "avg_volume_20d": round(avg_volume),
            "vol_mc_ratio": round(vol_mc_ratio, 4) if vol_mc_ratio else None,
            "vol_change_pct": round(vol_change, 2) if vol_change is not None else None,
            "industry": ind_name,
            "industry_turnover_median": ind_bench.get("turnover_median") if ind_bench else None,
            "turnover_score": scores.get("turnover"),
            "volume_score": scores.get("volume"),
            "trend_score": scores.get("trend"),
            "unavailable": unavailable_list(scores, reasons),
        },
    }