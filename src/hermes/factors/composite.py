"""Composite multi-factor combination.

Default weights follow academic consensus adapted for A-shares, oriented toward long-term investing:
  - Value, Growth, Quality, Dividend = four core factors (higher weight, 20+20+20+15=75%)
  - Momentum, Capital Flow = timing factors (lower weight, short-term oriented)
  - Volatility and Liquidity = risk/auxiliary factors (supplementary)

Default weights: value=0.20, growth=0.20, quality=0.20, dividend=0.15, momentum=0.06, capital_flow=0.06, volatility=0.06, liquidity=0.07
Signal thresholds:
  - score >= 7 → "buy"
  - score >= 5 → "hold"
  - score >= 3 → "watch"
  - score < 3 → "sell"

Strict data policy: None scores are excluded from weighted average with renormalized weights.
"""

from hermes.factors.value import value_factor
from hermes.factors.growth import growth_factor
from hermes.factors.quality import quality_factor
from hermes.factors.dividend import dividend_factor
from hermes.factors.momentum import momentum_factor
from hermes.factors.capital_flow import capital_flow_factor
from hermes.factors.volatility import volatility_factor
from hermes.factors.liquidity import liquidity_factor
from hermes.factors._utils import weighted_avg

ALL_FACTORS = ["value", "growth", "quality", "dividend", "momentum", "capital_flow", "volatility", "liquidity"]

FACTOR_FUNCS = {
    "value": value_factor,
    "growth": growth_factor,
    "quality": quality_factor,
    "dividend": dividend_factor,
    "momentum": momentum_factor,
    "capital_flow": capital_flow_factor,
    "volatility": volatility_factor,
    "liquidity": liquidity_factor,
}

DEFAULT_WEIGHTS = {
    "value": 0.20,
    "growth": 0.20,
    "quality": 0.20,
    "dividend": 0.15,
    "momentum": 0.06,
    "capital_flow": 0.06,
    "volatility": 0.06,
    "liquidity": 0.07,
}


def _get_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    """Resolve weights: explicit > config file > defaults."""
    if weights:
        return weights
    try:
        from hermes.config import get_factor_weights
        return get_factor_weights()
    except Exception:
        return DEFAULT_WEIGHTS


def composite_factor(code: str, weights: dict[str, float] | None = None) -> dict:
    """Compute composite multi-factor score with configurable weights."""
    w = _get_weights(weights)

    # Compute all factor scores
    factor_results = {}
    unavailable_factors = []
    missing_factors = []

    for name in ALL_FACTORS:
        func = FACTOR_FUNCS.get(name)
        if func:
            r = func(code)
            if "error" in r:
                missing_factors.append({"factor": name, "reason": r["error"]})
            else:
                factor_results[name] = r

    if not factor_results:
        return {"error": "Failed to compute any factor", "code": code}

    # Build scores dict (may include None for sub-factors that couldn't be computed)
    scores = {}
    for name, result in factor_results.items():
        score = result.get("score")
        scores[name] = score
        if score is None:
            unavailable_factors.append({"factor": name, "reason": "score is None — see details.unavailable"})

    # Compute composite with renormalized weights for available scores
    composite_score = weighted_avg(scores, w)

    if composite_score is None:
        return {"error": "No factor scores available for composite", "code": code}

    # Signal determination
    if composite_score >= 7:
        signal = "buy"
    elif composite_score >= 5:
        signal = "hold"
    elif composite_score >= 3:
        signal = "watch"
    else:
        signal = "sell"

    # Aggregate partial factor warnings (factors with unavailable sub-factors)
    partial_factors = []
    for name, r in factor_results.items():
        unavail = r.get("details", {}).get("unavailable", [])
        if unavail:
            partial_factors.append({
                "factor": name,
                "coverage_pct": r.get("coverage_pct", 100),
                "unavailable_sub_factors": unavail,
            })

    return {
        "factor": "composite",
        "score": composite_score,
        "signal": signal,
        "weights_used": {k: v for k, v in w.items() if k in scores and scores[k] is not None},
        "sub_factors": {name: {"score": r["score"], "coverage_pct": r.get("coverage_pct"), "details": r["details"]} for name, r in factor_results.items()},
        "missing_factors": missing_factors,
        "unavailable_factors": unavailable_factors,
        "partial_factors": partial_factors,
    }