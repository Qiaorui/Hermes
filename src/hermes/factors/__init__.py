"""Quantitative factor scoring modules.

Each factor module returns a dict with:
  - "factor": factor name
  - "score": 0-10 score
  - "details": sub-factor breakdown

Factors reference Barra CNE5S style factor framework, adapted for A-share market.
8 factors: value, growth, quality, dividend, momentum, capital_flow, volatility, liquidity
"""

from hermes.factors.value import value_factor
from hermes.factors.growth import growth_factor
from hermes.factors.quality import quality_factor
from hermes.factors.dividend import dividend_factor
from hermes.factors.momentum import momentum_factor
from hermes.factors.capital_flow import capital_flow_factor
from hermes.factors.volatility import volatility_factor
from hermes.factors.liquidity import liquidity_factor
from hermes.factors.composite import composite_factor, ALL_FACTORS, FACTOR_FUNCS


def factor_score(code: str, factors: list[str] | None = None, ctx=None) -> dict:
    """Compute specified factor scores for a stock. Returns dict with all factor results."""
    names = factors or ALL_FACTORS
    results = {}
    for name in names:
        func = FACTOR_FUNCS.get(name)
        if func:
            r = func(code, ctx=ctx) if ctx is not None else func(code)
            if "error" not in r:
                results[name] = r
    return {"code": code, "factors": results, "count": len(results)}