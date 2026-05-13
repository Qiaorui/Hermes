"""Northbound capital flow (北向资金) — daily net inflow from沪股通 + 深股通.

Source: akshare stock_hsgt_hist_em (East Money 北向资金数据).
Returns daily net flow data showing foreign capital entering A-share market.

Note: akshare northbound data may have NaN for recent dates (after Aug 2024).
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
        # Fetch 沪股通 + 深股通 separately, then combine
        total_data = ak.stock_hsgt_hist_em(symbol="北向资金")

        # Use total_data (北向资金) as primary, fall back to combined
        df = total_data if total_data is not None and len(total_data) > 0 else None

        if df is None:
            return {"error": "Northbound flow data unavailable", "days": days}

        # Filter rows with valid net purchase data (non-NaN)
        valid = df[df["当日成交净买额"].notna()].tail(days)
        if len(valid) == 0:
            return {"error": "Northbound flow: recent data is NaN (data source gap)", "days": days}

        entries = []
        for _, row in valid.iterrows():
            try:
                net_flow = float(row.get("当日成交净买额", 0)) if row.get("当日成交净买额") is not None else None
                cumulative = float(row.get("历史累计净买额", 0)) if row.get("历史累计净买额") is not None else None
                if net_flow is None:
                    continue
                entries.append({
                    "date": str(row.get("日期", "")),
                    "net_flow": net_flow,
                    "cumulative": cumulative,
                })
            except (ValueError, TypeError):
                continue

        if not entries:
            return {"error": "No valid northbound flow entries", "days": days}

        # Summary stats
        flows = [e["net_flow"] for e in entries]
        total_net = round(sum(flows), 2) if flows else None
        avg_daily = round(sum(flows) / len(flows), 2) if flows else None
        positive_days = sum(1 for v in flows if v > 0)
        positive_pct = round(positive_days / len(flows) * 100, 1) if flows else None
        cumulative_net = entries[-1].get("cumulative") if entries else None

        return {
            "days": days,
            "count": len(entries),
            "items": entries,
            "cumulative_net": cumulative_net,
            "total_net": total_net,
            "avg_daily_net": avg_daily,
            "positive_days_pct": positive_pct,
            "source": "akshare",
        }
    except AttributeError as e:
        log.warning(f"akshare northbound API changed: {e}")
        return {"error": "Northbound flow API unavailable (akshare update needed)", "days": days}
    except Exception as e:
        log.warning(f"akshare northbound_flow failed: {e}")
        return {"error": "Northbound flow data unavailable", "days": days}