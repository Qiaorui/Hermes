"""Quality factor — derived from LEVERAGE + profitability (Barra CNE5S).

Sub-factors:
  - ROE (approximated from net profit / equity)
  - Operating cash flow / net profit ratio (earnings quality)
  - Debt-to-asset ratio (financial health, inverted)
  - Gross margin stability
"""

from hermes.data.financial import stock_financial


def quality_factor(code: str) -> dict:
    """Compute quality factor score (0-10). Higher quality = higher score."""
    income = stock_financial(code, "income", 4)
    balance = stock_financial(code, "balance", 2)
    cashflow = stock_financial(code, "cashflow", 2)

    inc_periods = income.get("periods", [])
    bal_periods = balance.get("periods", [])
    cf_periods = cashflow.get("periods", [])

    if not inc_periods or not bal_periods:
        return {"error": "Insufficient financial data", "code": code}

    # Use latest period data
    latest_inc = inc_periods[0] if inc_periods else {}
    latest_bal = bal_periods[0] if bal_periods else {}
    latest_cf = cf_periods[0] if cf_periods else {}

    # 1. Debt ratio score (inverted: lower debt = higher quality)
    debt_ratio = latest_bal.get("DEBT_ASSET_RATIO")
    if debt_ratio is None:
        debt_score = 5.0
    elif debt_ratio < 30:
        debt_score = 9.0
    elif debt_ratio < 40:
        debt_score = 7.5
    elif debt_ratio < 50:
        debt_score = 6.0
    elif debt_ratio < 60:
        debt_score = 4.0
    elif debt_ratio < 70:
        debt_score = 2.0
    else:
        debt_score = 0.5

    # 2. Net profit margin (positive and reasonable = quality)
    net_margin = latest_inc.get("PARENT_NETPROFIT_RATIO")
    if net_margin is None:
        margin_score = 3.0
    elif net_margin < -20:
        margin_score = 0
    elif net_margin < 0:
        margin_score = 2
    elif net_margin < 5:
        margin_score = 4
    elif net_margin < 10:
        margin_score = 5
    elif net_margin < 20:
        margin_score = 7
    elif net_margin < 30:
        margin_score = 8
    else:
        margin_score = 9

    # 3. Operating cash flow / net profit ratio (earnings quality)
    # Ratio > 1 means cash earnings exceed accounting earnings (high quality)
    ocf = latest_cf.get("NETCASH_OPERATE")
    net_profit = latest_inc.get("PARENT_NETPROFIT")

    if ocf is not None and net_profit is not None and net_profit > 0:
        ocf_npf_ratio = ocf / net_profit
        if ocf_npf_ratio > 1.2:
            ocf_score = 9
        elif ocf_npf_ratio > 0.8:
            ocf_score = 7
        elif ocf_npf_ratio > 0.5:
            ocf_score = 5
        elif ocf_npf_ratio > 0:
            ocf_score = 3
        else:
            ocf_score = 1  # negative OCF despite positive profit = red flag
    elif net_profit is not None and net_profit <= 0:
        # Loss company: OCF still positive = some quality
        if ocf is not None and ocf > 0:
            ocf_score = 3
        else:
            ocf_score = 0
    else:
        ocf_score = 5  # neutral when data missing

    # 4. Profit consistency (positive profit in recent periods)
    profits = [p.get("PARENT_NETPROFIT") for p in inc_periods if p.get("PARENT_NETPROFIT") is not None]
    positive_count = sum(1 for p in profits if p > 0)
    if len(profits) >= 4:
        consistency = positive_count / len(profits)
        consistency_score = consistency * 10
    elif len(profits) >= 2:
        consistency_score = positive_count / len(profits) * 8
    else:
        consistency_score = 5

    # Composite: equal weight
    scores = [debt_score, margin_score, ocf_score, consistency_score]
    composite = round(sum(scores) / len(scores), 1)

    return {
        "factor": "quality",
        "score": composite,
        "details": {
            "debt_asset_ratio": debt_ratio,
            "net_profit_margin_pct": net_margin,
            "ocf_npf_ratio": round(ocf_npf_ratio, 2) if ocf is not None and net_profit is not None and net_profit > 0 else None,
            "profit_consistency": round(positive_count / len(profits), 2) if profits else None,
            "debt_score": round(debt_score, 1),
            "margin_score": round(margin_score, 1),
            "ocf_score": round(ocf_score, 1),
            "consistency_score": round(consistency_score, 1),
        },
    }