"""Value factor — BTOP + EARNYILD + PEG (Barra CNE5S), industry-neutralized.

Sub-factors:
  - PE: industry-relative percentile (lower vs industry median → higher score)
  - PB: industry-relative percentile (lower vs industry median → higher score)
  - PS: absolute thresholds (no industry PS median available)
  - EP (earnings yield): absolute scoring (1/PE)
  - PEG: PE / profit_yoy (lower → better value; handles negative/zero growth)

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

from hermes.data.quote import stock_quote
from hermes.data.valuation import stock_valuation_history
from hermes.data.industry import get_industry_median_from_quote, industry_percentile
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def _invert_score(pct: float) -> float:
    """Invert percentile: low percentile (cheap) → high score."""
    return max(0, min(10, 10 * (1 - pct / 100)))


def _ps_score(ps: float | None) -> float | None:
    """PS absolute scoring. Returns None when ps is None."""
    if ps is None:
        return None
    elif ps < 2.0:
        return 9.0
    elif ps < 5.0:
        return 6.0
    elif ps < 10.0:
        return 3.0
    elif ps < 20.0:
        return 1.0
    else:
        return 0.5


def _peg_score(pe: float | None, profit_yoy: float | None) -> float | None:
    """PEG scoring: PE / profit_yoy %. Lower PEG = better value.
    Returns None when data unavailable or growth is negative/zero.
    """
    if pe is None or profit_yoy is None:
        return None
    if pe <= 0 or profit_yoy <= 0:
        return None
    peg = pe / profit_yoy
    if peg < 0.5:
        return 9.0
    elif peg < 1.0:
        return 7.0
    elif peg < 1.5:
        return 5.0
    elif peg < 2.0:
        return 3.0
    elif peg < 3.0:
        return 1.5
    else:
        return 0.5


def value_factor(code: str, ctx=None) -> dict:
    """Compute value factor score (0-10). Industry-neutralized, no fallbacks."""
    if ctx and ctx.has("quote"):
        quote = ctx.get("quote")
    else:
        quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote", "code": code}

    if ctx and ctx.has("valuation"):
        val = ctx.get("valuation")
    else:
        val = stock_valuation_history(code)
    if "error" in val:
        return {"error": "Failed to get valuation history", "code": code}

    price_pct = val.get("price_pct_in_range", 50)
    pe = quote.get("pe_dynamic")  # pe_dynamic = PE(TTM) from push2, consistent with pe_ttm_median
    pb = quote.get("pb")
    ps = quote.get("ps")
    profit_yoy = quote.get("profit_yoy")

    # Get industry benchmarks
    ind_bench = get_industry_median_from_quote(quote)
    ind_name = ind_bench.get("industry") if ind_bench else None

    scores = {}
    reasons = {}

    # PE score: industry-relative percentile, None when data unavailable
    if pe is not None and pe > 0:
        if ind_name:
            pe_pct = industry_percentile(pe, ind_name, "pe")
            scores["pe"] = _invert_score(pe_pct) if pe_pct is not None else None
            if scores["pe"] is None:
                reasons["pe"] = "industry PE median unavailable"
        else:
            scores["pe"] = None
            reasons["pe"] = "industry benchmark unavailable"
    else:
        scores["pe"] = None
        reasons["pe"] = "PE data unavailable or negative"

    # PB score: industry-relative percentile, None when data unavailable
    if pb is not None:
        if ind_name:
            pb_pct = industry_percentile(pb, ind_name, "pb")
            scores["pb"] = _invert_score(pb_pct) if pb_pct is not None else None
            if scores["pb"] is None:
                reasons["pb"] = "industry PB median unavailable"
        else:
            scores["pb"] = None
            reasons["pb"] = "industry benchmark unavailable"
    else:
        scores["pb"] = None
        reasons["pb"] = "PB data unavailable"

    # PS score: absolute thresholds, None when data unavailable
    scores["ps"] = _ps_score(ps)
    if scores["ps"] is None:
        reasons["ps"] = "PS data unavailable"

    # EP (earnings yield = 1/PE), None when PE unavailable
    if pe is not None and pe > 0:
        ep = 1 / pe
        scores["ep"] = min(10, ep * 100)
    else:
        scores["ep"] = None
        reasons["ep"] = "PE unavailable, cannot compute earnings yield"

    # PEG (PE / profit_yoy %), None when growth negative/zero or PE unavailable
    scores["peg"] = _peg_score(pe, profit_yoy)
    if scores["peg"] is None:
        if pe is None or pe <= 0:
            reasons["peg"] = "PE unavailable or negative"
        elif profit_yoy is None:
            reasons["peg"] = "profit_yoy unavailable"
        else:
            reasons["peg"] = "profit_yoy negative or zero, PEG undefined"

    weights = {"pe": 0.20, "pb": 0.20, "ps": 0.15, "ep": 0.15, "peg": 0.30}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for value factor", "code": code}

    return {
        "factor": "value",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            "pe_dynamic": pe,
            "pb": pb,
            "ps": ps,
            "price_pct_in_range": price_pct,
            "industry": ind_name,
            "industry_pe_median": ind_bench.get("pe_median") if ind_bench else None,
            "industry_pb_median": ind_bench.get("pb_median") if ind_bench else None,
            "pe_score": scores.get("pe"),
            "pb_score": scores.get("pb"),
            "ps_score": scores.get("ps"),
            "ep_score": scores.get("ep"),
            "peg_score": scores.get("peg"),
            "profit_yoy": profit_yoy,
            "unavailable": unavailable_list(scores, reasons),
        },
    }