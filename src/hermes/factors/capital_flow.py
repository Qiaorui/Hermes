"""Capital flow factor — institutional fund flow trend and direction.

Sub-factors:
  - Main force trend: 20-day cumulative main net inflow (positive → institutional buying)
  - Institutional concentration: (super_large + large) % of total flow
  - Flow direction consistency: % of days where main force has same direction in last 10 days

Default weights: trend 40%, concentration 30%, consistency 30%

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

from hermes.data.fund_flow import stock_fund_flow
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def _trend_score(cumulative_main_pct: float | None) -> float | None:
    """Score cumulative main force net inflow ratio over 20 days.
    Higher positive → institutional buying → higher score.
    Returns None when data unavailable.
    """
    if cumulative_main_pct is None:
        return None
    # cumulative_main_pct = sum(main_pct) over 20 days
    if cumulative_main_pct >= 50:
        return 9.0
    elif cumulative_main_pct >= 20:
        return 7.0
    elif cumulative_main_pct >= 5:
        return 5.0
    elif cumulative_main_pct >= 0:
        return 3.0
    elif cumulative_main_pct >= -20:
        return 2.0
    elif cumulative_main_pct >= -50:
        return 1.0
    else:
        return 0.5


def _concentration_score(inst_pct: float | None) -> float | None:
    """Score institutional concentration (super_large + large % of total flow).
    Higher concentration → stronger institutional signal → higher score.
    Returns None when data unavailable.
    """
    if inst_pct is None:
        return None
    if inst_pct >= 40:
        return 9.0
    elif inst_pct >= 25:
        return 7.0
    elif inst_pct >= 15:
        return 5.0
    elif inst_pct >= 5:
        return 3.0
    elif inst_pct >= 0:
        return 1.0
    else:
        return 0.5


def _consistency_score(consistency_pct: float | None) -> float | None:
    """Score flow direction consistency (% of days with same direction in last 10).
    Higher consistency → clearer institutional intent → higher score.
    Returns None when data unavailable.
    """
    if consistency_pct is None:
        return None
    if consistency_pct >= 80:
        return 9.0
    elif consistency_pct >= 60:
        return 7.0
    elif consistency_pct >= 40:
        return 4.0
    elif consistency_pct >= 20:
        return 2.0
    else:
        return 1.0


def capital_flow_factor(code: str, ctx=None) -> dict:
    """Compute capital flow factor score (0-10). Based on fund flow data, no fallbacks."""
    if ctx is not None and ctx.has("fund_flow"):
        flow = ctx.get("fund_flow")
    else:
        flow = stock_fund_flow(code, 30)
    if "error" in flow:
        return {"error": "Fund flow data unavailable", "code": code}

    entries = flow.get("fund_flow", [])
    if not entries:
        return {"error": "No fund flow entries", "code": code}

    scores = {}
    reasons = {}
    derived = {}

    # Sub-factor 1: Main force trend (20-day cumulative)
    recent_20 = entries[-20:] if len(entries) >= 20 else entries
    cumulative_main_pct = None
    if recent_20:
        try:
            main_pcts = [e.get("main_pct") for e in recent_20]
            valid_pcts = [p for p in main_pcts if p is not None]
            if valid_pcts:
                cumulative_main_pct = round(sum(valid_pcts), 2)
        except (ValueError, TypeError):
            pass

    scores["trend"] = _trend_score(cumulative_main_pct)
    if scores["trend"] is None:
        reasons["trend"] = "main force trend data unavailable"
    derived["cumulative_main_pct_20d"] = cumulative_main_pct

    # Sub-factor 2: Institutional concentration (super_large + large %)
    # Use average of recent 10 days
    recent_10 = entries[-10:] if len(entries) >= 10 else entries
    inst_pct = None
    if recent_10:
        try:
            # super_large_pct + large_pct; compute from absolute values
            inst_net_inflows = []
            total_net_inflows = []
            for e in recent_10:
                sl = e.get("super_large_net_inflow") or 0
                lg = e.get("large_net_inflow") or 0
                main = e.get("main_net_inflow") or 0
                inst_net_inflows.append(abs(sl) + abs(lg))
                total_net_inflows.append(abs(sl) + abs(lg) + abs(e.get("medium_net_inflow") or 0) + abs(e.get("small_net_inflow") or 0))
            total_inst = sum(inst_net_inflows)
            total_all = sum(total_net_inflows)
            if total_all > 0:
                inst_pct = round(total_inst / total_all * 100, 1)
        except (ValueError, TypeError):
            pass

    scores["concentration"] = _concentration_score(inst_pct)
    if scores["concentration"] is None:
        reasons["concentration"] = "institutional concentration data unavailable"
    derived["inst_concentration_pct"] = inst_pct

    # Sub-factor 3: Flow direction consistency
    # % of recent 10 days where main force has same sign direction
    consistency_pct = None
    if recent_10:
        try:
            directions = []
            for e in recent_10:
                main = e.get("main_net_inflow")
                if main is not None:
                    directions.append(1 if main > 0 else -1)
            if len(directions) >= 3:
                positive_count = sum(1 for d in directions if d == 1)
                negative_count = len(directions) - positive_count
                dominant = max(positive_count, negative_count)
                consistency_pct = round(dominant / len(directions) * 100, 1)
                # Score direction: positive consistency (buying) > negative consistency (selling)
                if positive_count < negative_count:
                    # Selling consistency → lower score adjustment
                    consistency_pct = consistency_pct * 0.5
        except (ValueError, TypeError):
            pass

    scores["consistency"] = _consistency_score(consistency_pct)
    if scores["consistency"] is None:
        reasons["consistency"] = "flow direction consistency data unavailable"
    derived["direction_consistency_pct"] = consistency_pct

    weights = {"trend": 0.40, "concentration": 0.30, "consistency": 0.30}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for capital flow factor", "code": code}

    return {
        "factor": "capital_flow",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            **derived,
            "trend_score": scores.get("trend"),
            "concentration_score": scores.get("concentration"),
            "consistency_score": scores.get("consistency"),
            "unavailable": unavailable_list(scores, reasons),
        },
    }