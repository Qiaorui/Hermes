"""Dragon-tiger list (龙虎榜) — hot money and institutional activity tracker.

Source: akshare stock_lhb_detail_em (East Money 龙虎榜详情).
Returns stocks that hit dragon-tiger list on a given trading day, with
buying/selling brokerage seats, amounts, and reason for listing.

Strict data policy: no fallback values. Missing data → explicit error.
"""

import logging
from datetime import date, timedelta

log = logging.getLogger(__name__)


def _safe_float(val) -> float | None:
    """Convert value to float, treating None/NaN as None but preserving legitimate 0."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if str(val) != "nan" else None
    except (ValueError, TypeError):
        return None


def _find_latest_date() -> str:
    """Find the most recent trading day with dragon-tiger data.
    Walks backwards up to 5 days from today.
    """
    today = date.today()
    # Skip weekends (dragon-tiger only on trading days)
    for i in range(7):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # Mon-Fri
            return d.strftime("%Y%m%d")
    return today.strftime("%Y%m%d")


def dragon_tiger_list(date_str: str = "") -> dict:
    """Get dragon-tiger list (龙虎榜) for a trading day.

    Args:
        date_str: Trading date in YYYYMMDD format (empty = most recent trading day).

    Returns dict with stocks that appeared on dragon-tiger list, including
    buying/selling amounts, brokerage seats, and reason for listing.
    """
    if not date_str:
        date_str = _find_latest_date()

    try:
        import akshare as ak
        df = ak.stock_lhb_detail_em(date=date_str)
        if df is None or len(df) == 0:
            return {"error": f"No dragon-tiger data for {date_str}", "date": date_str}

        entries = []
        for _, row in df.iterrows():
            try:
                entry = {
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "close_price": _safe_float(row.get("收盘价")),
                    "change_pct": _safe_float(row.get("涨跌幅")),
                    "reason": str(row.get("上榜原因", "")),
                    "buy_amount": _safe_float(row.get("买入额")),
                    "sell_amount": _safe_float(row.get("卖出额")),
                    "net_amount": _safe_float(row.get("净额")),
                    "buy_broker": str(row.get("买入营业部", "")),
                    "sell_broker": str(row.get("卖出营业部", "")),
                }
                if entry["code"]:
                    entries.append(entry)
            except (ValueError, TypeError):
                continue

        if not entries:
            return {"error": f"No valid dragon-tiger entries for {date_str}", "date": date_str}

        return {
            "date": date_str,
            "count": len(entries),
            "entries": entries,
            "source": "akshare",
        }
    except Exception as e:
        log.warning(f"akshare dragon_tiger failed for {date_str}: {e}")
        return {"error": f"Dragon-tiger data unavailable for {date_str}", "date": date_str}


def dragon_tiger_for_stock(code: str) -> dict | None:
    """Get dragon-tiger data for a specific stock. Returns None if stock not on list.

    Fetches the full list for the most recent trading day, then filters for the stock code.
    Most stocks are not on the list any given day, so this returns None quickly.
    """
    full = dragon_tiger_list()
    if "error" in full:
        return None

    for entry in full.get("entries", []):
        if entry.get("code") == code:
            return {"date": full["date"], "entry": entry}
    return None