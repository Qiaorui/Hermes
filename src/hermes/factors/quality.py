"""Quality factor — LEVERAGE + profitability (Barra CNE5S).

Sub-factors:
  - Debt-to-asset ratio (inverted: lower = better)
  - Net profit margin
  - OCF/net profit ratio (earnings quality)
  - Profit consistency
  - ROE stability
  - Accruals quality

Strict data policy: no fallback values. Missing data → None + unavailable label.
"""

from hermes.data.financial import stock_financial
from hermes.data.industry import get_industry_median_from_quote
from hermes.data.quote import stock_quote
from hermes.factors._utils import weighted_avg, unavailable_list, coverage_pct


def quality_factor(code: str, ctx=None) -> dict:
    """Compute quality factor score (0-10). No fallback defaults."""
    # Get industry context
    if ctx and ctx.has("quote"):
        quote = ctx.get("quote")
    else:
        quote = stock_quote(code)
    ind_bench = get_industry_median_from_quote(quote) if "error" not in quote else None
    ind_name = ind_bench.get("industry") if ind_bench else None

    if ctx and ctx.has("income"):
        income = ctx.get("income")
    else:
        income = stock_financial(code, "income", 4)
    if ctx and ctx.has("balance"):
        balance = ctx.get("balance")
    else:
        balance = stock_financial(code, "balance", 4)
    if ctx and ctx.has("cashflow"):
        cashflow = ctx.get("cashflow")
    else:
        cashflow = stock_financial(code, "cashflow", 2)

    inc_periods = income.get("periods", [])
    bal_periods = balance.get("periods", [])
    cf_periods = cashflow.get("periods", [])

    if not inc_periods or not bal_periods:
        return {"error": "Insufficient financial data", "code": code}

    latest_inc = inc_periods[0] if inc_periods else {}
    latest_bal = bal_periods[0] if bal_periods else {}
    latest_cf = cf_periods[0] if cf_periods else {}

    scores = {}
    reasons = {}

    # 1. Debt ratio score (inverted)
    debt_ratio = latest_bal.get("DEBT_ASSET_RATIO")
    if debt_ratio is None:
        scores["debt"] = None
        reasons["debt"] = "debt ratio data unavailable"
    elif debt_ratio < 30:
        scores["debt"] = 9.0
    elif debt_ratio < 40:
        scores["debt"] = 7.5
    elif debt_ratio < 50:
        scores["debt"] = 6.0
    elif debt_ratio < 60:
        scores["debt"] = 4.0
    elif debt_ratio < 70:
        scores["debt"] = 2.0
    else:
        scores["debt"] = 0.5

    # 2. Net profit margin
    net_margin = latest_inc.get("PARENT_NETPROFIT_RATIO")
    if net_margin is None:
        scores["margin"] = None
        reasons["margin"] = "net profit margin data unavailable"
    elif net_margin < -20:
        scores["margin"] = 0
    elif net_margin < 0:
        scores["margin"] = 2
    elif net_margin < 5:
        scores["margin"] = 4
    elif net_margin < 10:
        scores["margin"] = 5
    elif net_margin < 20:
        scores["margin"] = 7
    elif net_margin < 30:
        scores["margin"] = 8
    else:
        scores["margin"] = 9

    # 3. OCF/net profit ratio (earnings quality)
    ocf = latest_cf.get("NETCASH_OPERATE")
    net_profit = latest_inc.get("PARENT_NETPROFIT")
    ocf_npf_ratio = None

    if ocf is not None and net_profit is not None and net_profit > 0:
        ocf_npf_ratio = ocf / net_profit
        if ocf_npf_ratio > 1.2:
            scores["ocf"] = 9
        elif ocf_npf_ratio > 0.8:
            scores["ocf"] = 7
        elif ocf_npf_ratio > 0.5:
            scores["ocf"] = 5
        elif ocf_npf_ratio > 0:
            scores["ocf"] = 3
        else:
            scores["ocf"] = 1
    elif net_profit is not None and net_profit <= 0:
        if ocf is not None and ocf > 0:
            scores["ocf"] = 3
        else:
            scores["ocf"] = 0
    else:
        scores["ocf"] = None
        reasons["ocf"] = "OCF or net profit data unavailable"

    # 4. Profit consistency
    profits = [p.get("PARENT_NETPROFIT") for p in inc_periods if p.get("PARENT_NETPROFIT") is not None]
    if len(profits) >= 4:
        positive_count = sum(1 for p in profits if p > 0)
        scores["consistency"] = round(positive_count / len(profits) * 10, 1)
    elif len(profits) >= 2:
        positive_count = sum(1 for p in profits if p > 0)
        scores["consistency"] = round(positive_count / len(profits) * 8, 1)
    else:
        scores["consistency"] = None
        reasons["consistency"] = "fewer than 2 periods with profit data"

    # 5. ROE stability
    roe_values = []
    for i in range(min(len(inc_periods), len(bal_periods))):
        np = inc_periods[i].get("PARENT_NETPROFIT")
        p = bal_periods[i].get("PARENT_EQUITY")
        eq = p if p is not None else bal_periods[i].get("TOTAL_EQUITY")
        if np is not None and eq is not None and eq > 0:
            roe_values.append(np / eq * 100)

    if len(roe_values) >= 3:
        roe_mean = sum(roe_values) / len(roe_values)
        roe_std = (sum((r - roe_mean) ** 2 for r in roe_values) / len(roe_values)) ** 0.5
        if roe_mean < 0:
            scores["roe_stability"] = 1
        elif roe_std < 2:
            scores["roe_stability"] = 9
        elif roe_std < 5:
            scores["roe_stability"] = 7
        elif roe_std < 10:
            scores["roe_stability"] = 5
        elif roe_std < 20:
            scores["roe_stability"] = 3
        else:
            scores["roe_stability"] = 1
    else:
        scores["roe_stability"] = None
        reasons["roe_stability"] = "fewer than 3 periods with ROE data"

    # 6. Accruals quality
    accruals = None
    if net_profit is not None and ocf is not None and latest_bal.get("TOTAL_ASSETS") is not None and latest_bal["TOTAL_ASSETS"] > 0:
        accruals = (net_profit - ocf) / latest_bal["TOTAL_ASSETS"] * 100
        if accruals < -2:
            scores["accruals"] = 9.0
        elif accruals < 0:
            scores["accruals"] = 7.0
        elif accruals < 3:
            scores["accruals"] = 6.0
        elif accruals < 5:
            scores["accruals"] = 4.0
        elif accruals < 10:
            scores["accruals"] = 2.0
        else:
            scores["accruals"] = 0.5
    else:
        scores["accruals"] = None
        reasons["accruals"] = "net profit, OCF, or total assets data unavailable"

    weights = {"debt": 0.15, "margin": 0.15, "ocf": 0.20, "consistency": 0.15,
               "roe_stability": 0.20, "accruals": 0.15}
    composite = weighted_avg(scores, weights)

    if composite is None:
        return {"error": "No data available for quality factor", "code": code}

    return {
        "factor": "quality",
        "score": composite,
        "coverage_pct": coverage_pct(scores),
        "details": {
            "debt_asset_ratio": debt_ratio,
            "net_profit_margin_pct": net_margin,
            "ocf_npf_ratio": round(ocf_npf_ratio, 2) if ocf_npf_ratio is not None else None,
            "profit_consistency": round(positive_count / len(profits), 2) if len(profits) >= 2 else None,
            "roe_mean_pct": round(sum(roe_values) / len(roe_values), 2) if roe_values else None,
            "roe_std_pct": round((sum((r - sum(roe_values) / len(roe_values)) ** 2 for r in roe_values) / len(roe_values)) ** 0.5, 2) if len(roe_values) >= 3 else None,
            "accruals_pct": round(accruals, 2) if accruals is not None else None,
            "industry": ind_name,
            "debt_score": scores.get("debt"),
            "margin_score": scores.get("margin"),
            "ocf_score": scores.get("ocf"),
            "consistency_score": scores.get("consistency"),
            "roe_stability_score": scores.get("roe_stability"),
            "accruals_score": scores.get("accruals"),
            "unavailable": unavailable_list(scores, reasons),
        },
    }