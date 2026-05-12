"""Northbound capital flow (北向资金) — daily net inflow from沪股通 + 深股通.

Source: akshare stock_hsgt_north_net_flow_in_em (East Money 北向资金数据).
Returns daily net flow data showing how much foreign capital is entering
A-share market through Shanghai and Shenzhen Connect channels.

Strict data policy: no fallback values. Missing data → explicit error.
"""

import logging

log = logging.getLogger(__name__)


def northbound_flow(days: int = 30) -> dict:
    """Get daily northbound capital net flow data.

    Args:
        days: Number of recent days (default 30, max 120).

    Returns dict with daily net flow, cumulative trend, and summary stats.
    """
    days = min(days, 120)

    try:
        import akshare as ak
        df = ak.stock_hsgt_north_net_flow_in_em(symbol="北向资金")
        if df is None or len(df) == 0:
            return {"error": "Northbound flow data unavailable", "days": days}

        # Take most recent `days` rows
        df = df.tail(days)

        entries = []
        for _, row in df.iterrows():
            try:
                # Common column names from akshare: 日期, 当日净流入(沪股通+深股通), 当日余额
                entry = {
                    "date": str(row.get("日期", "")),
                    "net_inflow": float(row.get("当日净流入", 0)) if row.get("当日净流入") else None,
                    "balance": float(row.get("当日余额", 0)) if row.get("当日余额") else None,
                }
                # Try alternative column names
                if entry["net_inflow"] is None:
                    net_col = row.get("当日资金净流入", row.get("净流入", None))
                    if net_col is not None:
                        entry["net_inflow"] = float(net_col)
                entries.append(entry)
            except (ValueError, TypeError):
                continue

        if not entries:
            return {"error": "No valid northbound flow entries", "days": days}

        # Compute summary stats
        inflows = [e["net_inflow"] for e in entries if e["net_inflow"] is not None]
        total_net = round(sum(inflows), 2) if inflows else None
        avg_daily = round(sum(inflows) / len(inflows), 2) if inflows else None
        positive_days = sum(1 for v in inflows if v > 0)
        positive_pct = round(positive_days / len(inflows) * 100, 1) if inflows else None

        return {
            "days": days,
            "count": len(entries),
            "flow": entries,
            "total_net_inflow": total_net,
            "avg_daily_net_inflow": avg_daily,
            "positive_days_pct": positive_pct,
            "source": "akshare",
        }
    except Exception as e:
        log.warning(f"akshare northbound_flow failed: {e}")
        return {"error": "Northbound flow data unavailable", "days": days}