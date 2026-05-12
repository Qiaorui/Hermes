"""Composite multi-factor combination.

Default weights follow academic consensus:
  - Value × Quality × Growth are the three core A-share factors (equal weight)
  - Momentum/Reversal is A-share specific (lower weight due to instability)
  - Volatility and Liquidity are risk/auxiliary factors (supplementary)

Default weights: value=0.20, growth=0.20, quality=0.25, momentum=0.15, volatility=0.10, liquidity=0.10
Signal thresholds:
  - score >= 7 → "buy"
  - score >= 5 → "hold"
  - score >= 3 → "watch"
  - score < 3 → "sell"
"""

from hermes.factors.value import value_factor
from hermes.factors.growth import growth_factor
from hermes.factors.quality import quality_factor
from hermes.factors.momentum import momentum_factor
from hermes.factors.volatility import volatility_factor
from hermes.factors.liquidity import liquidity_factor

ALL_FACTORS = ["value", "growth", "quality", "momentum", "volatility", "liquidity"]

FACTOR_FUNCS = {
    "value": value_factor,
    "growth": growth_factor,
    "quality": quality_factor,
    "momentum": momentum_factor,
    "volatility": volatility_factor,
    "liquidity": liquidity_factor,
}

DEFAULT_WEIGHTS = {
    "value": 0.20,
    "growth": 0.20,
    "quality": 0.25,
    "momentum": 0.15,
    "volatility": 0.10,
    "liquidity": 0.10,
}


def composite_factor(code: str, weights: dict[str, float] | None = None) -> dict:
    """Compute composite multi-factor score with configurable weights."""
    w = weights or DEFAULT_WEIGHTS

    # Compute all factor scores
    factor_results = {}
    for name in ALL_FACTORS:
        func = FACTOR_FUNCS.get(name)
        if func:
            r = func(code)
            if "error" not in r:
                factor_results[name] = r

    if not factor_results:
        return {"error": "Failed to compute any factor", "code": code}

    # Apply weights
    weighted_sum = 0
    total_weight = 0
    for name, result in factor_results.items():
        weight = w.get(name, 0)
        score = result.get("score", 0)
        weighted_sum += score * weight
        total_weight += weight

    composite_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0

    # Signal determination
    if composite_score >= 7:
        signal = "buy"
    elif composite_score >= 5:
        signal = "hold"
    elif composite_score >= 3:
        signal = "watch"
    else:
        signal = "sell"

    return {
        "factor": "composite",
        "score": composite_score,
        "signal": signal,
        "weights_used": {k: v for k, v in w.items() if k in factor_results},
        "sub_factors": {name: {"score": r["score"], "details": r["details"]} for name, r in factor_results.items()},
        "missing_factors": [f for f in ALL_FACTORS if f not in factor_results],
    }