"""Restricted share unlock schedule."""

from hermes.api.eastmoney import em_get


def stock_unlock_schedule(code: str) -> dict:
    """Get upcoming restricted share unlock schedule. Returns dict with unlocks list."""
    url = f"http://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LIFT_STAGE&columns=ALL&filter=(SECURITY_CODE=\"{code.strip()}\")&pageSize=20&sortColumns=FREE_DATE&sortTypes=-1&source=WEB&client=WEB"
    data = em_get(url)
    if not data or not data.get("result") or not data["result"].get("data"):
        return {"error": "No unlock schedule found", "code": code}

    unlocks = []
    for row in data["result"]["data"]:
        unlocks.append({
            "free_date": str(row.get("FREE_DATE", ""))[:10],
            "free_shares_type": row.get("FREE_SHARES_TYPE", ""),
            "current_free_shares_wan": row.get("CURRENT_FREE_SHARES"),
            "able_free_shares_wan": row.get("ABLE_FREE_SHARES"),
            "lift_market_cap_wan": row.get("LIFT_MARKET_CAP"),
            "free_ratio_pct": row.get("FREE_RATIO"),
            "total_ratio_pct": row.get("TOTAL_RATIO"),
            "non_free_shares_wan": row.get("NON_FREE_SHARES"),
            "batch_holder_num": row.get("BATCH_HOLDER_NUM"),
        })

    return {"code": code, "count": len(unlocks), "unlocks": unlocks}