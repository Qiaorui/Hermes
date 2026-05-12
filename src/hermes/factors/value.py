"""Value factor — BTOP + EARNYILD (Barra CNE5S).

Sub-factors:
  - PE percentile: lower PE → higher score (cheaper = better)
  - PB percentile: lower PB → higher score
  - PS percentile: lower PS → higher score
  - EP (earnings yield): higher EP → higher score
"""

from hermes.data.quote import stock_quote
from hermes.data.valuation import stock_valuation_history


def _invert_score(pct: float) -> float:
    """Invert percentile: low percentile (cheap) → high score."""
    return max(0, min(10, 10 * (1 - pct / 100)))


def value_factor(code: str) -> dict:
    """Compute value factor score (0-10). Lower valuation = higher score."""
    quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote", "code": code}

    val = stock_valuation_history(code)
    if "error" in val:
        return {"error": "Failed to get valuation history", "code": code}

    price_pct = val.get("price_pct_in_range", 50)
    pe = quote.get("pe_dynamic")
    pb = quote.get("pb")
    ps = quote.get("ps")

    # PE score: use percentile inversion
    pe_score = _invert_score(price_pct) if pe and pe > 0 else 0

    # PB score: absolute thresholds for A-share norms
    if pb is None:
        pb_score = 5.0  # neutral when missing
    elif pb < 1.0:
        pb_score = 9.0
    elif pb < 2.0:
        pb_score = 7.0
    elif pb < 4.0:
        pb_score = 4.0
    elif pb < 8.0:
        pb_score = 2.0
    else:
        pb_score = 0.5

    # PS score: absolute thresholds
    if ps is None:
        ps_score = 5.0
    elif ps < 2.0:
        ps_score = 9.0
    elif ps < 5.0:
        ps_score = 6.0
    elif ps < 10.0:
        ps_score = 3.0
    elif ps < 20.0:
        ps_score = 1.0
    else:
        ps_score = 0.5

    # EP (earnings yield = 1/PE), higher = better value
    if pe and pe > 0:
        ep = 1 / pe
        ep_score = min(10, ep * 100)  # EP=10% → score 10
    else:
        ep_score = 0  # negative PE → no value

    # Composite: equal weight
    scores = [pe_score, pb_score, ps_score, ep_score]
    composite = round(sum(scores) / len(scores), 1)

    return {
        "factor": "value",
        "score": composite,
        "details": {
            "pe_dynamic": pe,
            "pb": pb,
            "ps": ps,
            "price_pct_in_range": price_pct,
            "pe_score": round(pe_score, 1),
            "pb_score": round(pb_score, 1),
            "ps_score": round(ps_score, 1),
            "ep_score": round(ep_score, 1),
        },
    }