"""Growth factor — GROWTH (Barra CNE5S), industry-neutralized.

Sub-factors:
  - Revenue YoY: industry-relative percentile when available
  - Net Profit YoY: industry-relative percentile when available
  - Revenue acceleration: time-series trend

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

from hermes.data.quote import stock_quote
from hermes.data.financial import stock_financial
from hermes.data.industry import get_industry_median_from_quote, industry_percentile
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def _growth_score(yoy: float) -> float:
    """Convert absolute YoY growth rate to 0-10 score. Only called with valid (non-None) values."""
    if yoy < -30:
        return 0
    elif yoy < -10:
        return 1
    elif yoy < 0:
        return 3
    elif yoy < 10:
        return 5
    elif yoy < 20:
        return 6
    elif yoy < 30:
        return 7
    elif yoy < 50:
        return 8
    elif yoy < 100:
        return 9
    else:
        return 10


def growth_factor(code: str) -> dict:
    """Compute growth factor score (0-10). Industry-neutralized, no fallbacks."""
    quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote", "code": code}

    revenue_yoy = quote.get("revenue_yoy")
    profit_yoy = quote.get("profit_yoy")

    # Convert decimal to percentage if needed
    if revenue_yoy is not None and abs(revenue_yoy) < 1:
        revenue_yoy_pct = revenue_yoy * 100
    elif revenue_yoy is not None:
        revenue_yoy_pct = revenue_yoy
    else:
        revenue_yoy_pct = None

    if profit_yoy is not None and abs(profit_yoy) < 1:
        profit_yoy_pct = profit_yoy * 100
    elif profit_yoy is not None:
        profit_yoy_pct = profit_yoy
    else:
        profit_yoy_pct = None

    # Get industry benchmarks
    ind_bench = get_industry_median_from_quote(quote)
    ind_name = ind_bench.get("industry") if ind_bench else None

    scores = {}
    reasons = {}

    # Revenue YoY score: industry-relative percentile, None when data unavailable
    if revenue_yoy_pct is not None:
        if ind_name:
            rev_pct = industry_percentile(revenue_yoy_pct, ind_name, "revenue_yoy")
            scores["revenue"] = rev_pct / 10 if rev_pct is not None else None
            if scores["revenue"] is None:
                reasons["revenue"] = "industry revenue YoY median unavailable"
        else:
            scores["revenue"] = None
            reasons["revenue"] = "industry benchmark unavailable"
    else:
        scores["revenue"] = None
        reasons["revenue"] = "revenue YoY data unavailable"

    # Profit YoY score: industry-relative percentile, None when data unavailable
    if profit_yoy_pct is not None:
        if ind_name:
            prof_pct = industry_percentile(profit_yoy_pct, ind_name, "profit_yoy")
            scores["profit"] = prof_pct / 10 if prof_pct is not None else None
            if scores["profit"] is None:
                reasons["profit"] = "industry profit YoY median unavailable"
        else:
            scores["profit"] = None
            reasons["profit"] = "industry benchmark unavailable"
    else:
        scores["profit"] = None
        reasons["profit"] = "profit YoY data unavailable"

    # Trend: time-series, None when insufficient data
    inc = stock_financial(code, "income", 4)
    periods = inc.get("periods", [])

    if len(periods) >= 3:
        recent_revs = [p.get("TOTAL_OPERATE_INCOME") for p in periods[-3:]]
        if all(v is not None and v > 0 for v in recent_revs):
            if recent_revs[0] > recent_revs[1] > recent_revs[2]:
                scores["trend"] = 2.0
            elif recent_revs[0] > recent_revs[1]:
                scores["trend"] = 1.0
            else:
                scores["trend"] = 0.0
        else:
            scores["trend"] = None
            reasons["trend"] = "insufficient revenue data for trend"
    else:
        scores["trend"] = None
        reasons["trend"] = "fewer than 3 financial periods"

    weights = {"profit": 0.60, "revenue": 0.30, "trend": 0.10}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for growth factor", "code": code}

    return {
        "factor": "growth",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            "revenue_yoy_pct": revenue_yoy_pct,
            "profit_yoy_pct": profit_yoy_pct,
            "industry": ind_name,
            "industry_revenue_yoy_median": ind_bench.get("revenue_yoy_median") if ind_bench else None,
            "industry_profit_yoy_median": ind_bench.get("profit_yoy_median") if ind_bench else None,
            "revenue_score": scores.get("revenue"),
            "profit_score": scores.get("profit"),
            "trend_score": scores.get("trend"),
            "periods_available": len(periods),
            "unavailable": unavailable_list(scores, reasons),
        },
    }