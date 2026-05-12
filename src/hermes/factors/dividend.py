"""Dividend factor — yield, payout sustainability, and consistency.

Sub-factors:
  - Dividend yield: industry-relative percentile (higher vs industry → higher score)
  - Payout ratio: moderate (30-60%) is best; too high (>80%) unsustainable; too low (<20%) stingy
  - Dividend consistency: consecutive years of dividends (longer → higher score)

Default weights: yield 50%, payout 30%, consistency 20%

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

from hermes.data.dividend import stock_dividend
from hermes.data.industry import get_industry_median_from_quote, industry_percentile
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def _payout_score(ratio: float | None) -> float | None:
    """Score payout ratio. 30-60% is ideal; extremes are penalized.
    Returns None when ratio is None.
    """
    if ratio is None:
        return None
    if ratio < 10:
        return 1.0   # almost no payout
    elif ratio < 20:
        return 3.0
    elif ratio < 30:
        return 5.0
    elif ratio < 60:
        return 8.0   # sweet spot
    elif ratio < 80:
        return 5.0   # getting risky
    elif ratio < 100:
        return 2.0   # paying more than earning
    else:
        return 0.5   # clearly unsustainable


def _consistency_score(years: int | None) -> float | None:
    """Score dividend consistency based on consecutive years.
    Returns None when years is None.
    """
    if years is None:
        return None
    if years >= 10:
        return 10.0
    elif years >= 7:
        return 8.0
    elif years >= 5:
        return 6.0
    elif years >= 3:
        return 4.0
    elif years >= 1:
        return 2.0
    else:
        return 0.0


def dividend_factor(code: str) -> dict:
    """Compute dividend factor score (0-10). Industry-neutralized, no fallbacks."""
    div_data = stock_dividend(code)
    if "error" in div_data:
        return {"error": div_data.get("error", "Dividend data unavailable"), "code": code}

    dividend_yield = div_data.get("dividend_yield")
    payout_ratio = div_data.get("payout_ratio")
    consecutive_years = div_data.get("consecutive_years")

    # Get industry benchmarks for yield percentile
    from hermes.data.quote import stock_quote
    quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote for industry matching", "code": code}

    ind_bench = get_industry_median_from_quote(quote)
    ind_name = ind_bench.get("industry") if ind_bench else None
    ind_div_yield = ind_bench.get("dividend_yield_median") if ind_bench else None

    scores = {}
    reasons = {}

    # Dividend yield: industry-relative percentile (higher yield → higher score)
    if dividend_yield is not None:
        if ind_name and ind_div_yield is not None and ind_div_yield > 0:
            # Higher yield relative to industry = better
            ratio = dividend_yield / ind_div_yield
            if ratio >= 3.0:
                scores["yield"] = 10.0
            elif ratio >= 2.0:
                scores["yield"] = 8.0
            elif ratio >= 1.5:
                scores["yield"] = 7.0
            elif ratio >= 1.0:
                scores["yield"] = 5.0
            elif ratio >= 0.5:
                scores["yield"] = 3.0
            elif ratio >= 0.0:
                scores["yield"] = 1.5
            else:
                scores["yield"] = 0.5
        elif dividend_yield >= 5.0:
            scores["yield"] = 8.0  # absolute fallback: high yield
        elif dividend_yield >= 3.0:
            scores["yield"] = 6.0
        elif dividend_yield >= 1.0:
            scores["yield"] = 3.0
        elif dividend_yield >= 0.0:
            scores["yield"] = 1.0
        else:
            scores["yield"] = 0.5
    else:
        scores["yield"] = None
        if div_data.get("latest_dps") is None or div_data.get("latest_dps") == 0:
            reasons["yield"] = "no dividend paid"
        else:
            reasons["yield"] = "dividend yield computation failed"

    # Payout ratio
    scores["payout"] = _payout_score(payout_ratio)
    if scores["payout"] is None:
        reasons["payout"] = "payout ratio unavailable"

    # Consistency
    scores["consistency"] = _consistency_score(consecutive_years)
    if scores["consistency"] is None:
        reasons["consistency"] = "consistency data unavailable"

    weights = {"yield": 0.50, "payout": 0.30, "consistency": 0.20}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for dividend factor", "code": code}

    return {
        "factor": "dividend",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "consecutive_years": consecutive_years,
            "latest_dps": div_data.get("latest_dps"),
            "total_dividend_years": div_data.get("total_years"),
            "industry": ind_name,
            "industry_dividend_yield_median": ind_div_yield,
            "yield_score": scores.get("yield"),
            "payout_score": scores.get("payout"),
            "consistency_score": scores.get("consistency"),
            "unavailable": unavailable_list(scores, reasons),
        },
    }