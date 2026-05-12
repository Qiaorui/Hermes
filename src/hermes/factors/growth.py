"""Growth factor — GROWTH (Barra CNE5S).

Sub-factors:
  - Revenue YoY: higher → better growth
  - Net Profit YoY: higher → better growth
  - Revenue acceleration: improving trend → bonus
"""

from hermes.data.quote import stock_quote
from hermes.data.financial import stock_financial


def _growth_score(yoy: float | None) -> float:
    """Convert YoY growth rate to 0-10 score based on A-share norms."""
    if yoy is None:
        return 0
    # A-share growth distribution: -30% → 0, 0% → 3, 10% → 5, 20% → 7, 50% → 9, 100% → 10
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
    """Compute growth factor score (0-10). Higher growth = higher score."""
    quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote", "code": code}

    # Latest YoY from quote (these are in percent, e.g. -0.27 means -27%)
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

    # Check growth trend from financial statements
    inc = stock_financial(code, "income", 4)
    periods = inc.get("periods", [])

    trend_score = 0
    if len(periods) >= 3:
        # Check if recent revenue growth is improving
        recent_revs = [p.get("TOTAL_OPERATE_INCOME") for p in periods[-3:]]
        if all(v is not None and v > 0 for v in recent_revs):
            # If revenue is growing quarter over quarter
            if recent_revs[0] > recent_revs[1] > recent_revs[2]:
                trend_score = 2  # accelerating
            elif recent_revs[0] > recent_revs[1]:
                trend_score = 1  # recovering

    revenue_score = _growth_score(revenue_yoy_pct)
    profit_score = _growth_score(profit_yoy_pct)

    # Composite: profit YoY weight 60%, revenue 30%, trend 10%
    composite = round(profit_score * 0.6 + revenue_score * 0.3 + trend_score * 0.1, 1)
    composite = max(0, min(10, composite))

    return {
        "factor": "growth",
        "score": composite,
        "details": {
            "revenue_yoy_pct": revenue_yoy_pct,
            "profit_yoy_pct": profit_yoy_pct,
            "revenue_score": round(revenue_score, 1),
            "profit_score": round(profit_score, 1),
            "trend_score": trend_score,
            "periods_available": len(periods),
        },
    }