"""Daily fund flow data (main force net inflow by size category).

Primary source: push2.eastmoney.com (rate-limited, 30s cooldown).
Fallback source: akshare stock_individual_fund_flow (no rate limit, same data origin).

When both sources fail, returns explicit error dict — never returns empty
or default values per strict data policy.
"""

import logging
from hermes.api.eastmoney import em_get, parse_secid, push2_status

log = logging.getLogger(__name__)


def _safe_val(val) -> float | None:
    """Convert value to float, treating None/NaN as None but preserving legitimate 0."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if str(val) == "nan" or str(val) == "NaN" else f
    except (ValueError, TypeError):
        return None


def _fetch_from_push2(code: str, days: int) -> dict | None:
    """Fetch fund flow from push2 (primary, rate-limited)."""
    secid = parse_secid(code)
    url = (
        f"http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get?"
        f"lmt={days}&klt=101&fields1=f1,f2,f3,f7"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
        f"&secid={secid}&ut=7eea3edcaed734bea9cbfc24409ed989"
    )
    data = em_get(url)
    if not data or not data.get("data"):
        return None

    klines = data["data"].get("klines", [])
    result = []
    for k in klines:
        parts = k.split(",")
        if len(parts) >= 9:
            try:
                result.append({
                    "date": parts[0],
                    "main_net_inflow": float(parts[1]),
                    "small_net_inflow": float(parts[2]),
                    "medium_net_inflow": float(parts[3]),
                    "large_net_inflow": float(parts[4]),
                    "super_large_net_inflow": float(parts[5]),
                    "main_pct": float(parts[6]),
                    "small_pct": float(parts[7]),
                    "medium_pct": float(parts[8]),
                })
            except (ValueError, IndexError):
                continue

    if not result:
        return None
    return {"code": code, "count": len(result), "fund_flow": result, "source": "push2"}


def _fetch_from_akshare(code: str, days: int) -> dict | None:
    """Fetch fund flow from akshare (fallback, no rate limit)."""
    try:
        import akshare as ak
        market = "sh" if code.startswith("6") else "sz"
        df = ak.stock_individual_fund_flow(stock=code, market=market)
        if df is None or len(df) == 0:
            return None

        # Take only the most recent `days` rows
        df = df.tail(days)

        result = []
        for _, row in df.iterrows():
            try:
                entry = {
                    "date": str(row.get("日期", "")),
                    "main_net_inflow": _safe_val(row.get("主力净流入-净额")),
                    "small_net_inflow": _safe_val(row.get("小单净流入-净额")),
                    "medium_net_inflow": _safe_val(row.get("中单净流入-净额")),
                    "large_net_inflow": _safe_val(row.get("大单净流入-净额")),
                    "super_large_net_inflow": _safe_val(row.get("超大单净流入-净额")),
                    "main_pct": _safe_val(row.get("主力净流入-净占比")),
                    "small_pct": _safe_val(row.get("小单净流入-净占比")),
                    "medium_pct": _safe_val(row.get("中单净流入-净占比")),
                }
                result.append(entry)
            except (ValueError, TypeError):
                continue

        if not result:
            return None
        return {"code": code, "count": len(result), "fund_flow": result, "source": "akshare"}
    except Exception as e:
        log.warning(f"akshare fund flow failed for {code}: {e}")
        return None


def stock_fund_flow(code: str, days: int = 30) -> dict:
    """Get daily fund flow data. Returns dict with code, count, fund_flow.

    Tries push2 first (primary). Falls back to akshare when push2 unavailable.
    If both sources fail, returns explicit error dict.
    """
    days = min(days, 120)

    # Primary: push2
    result = _fetch_from_push2(code, days)
    if result:
        return result

    # Fallback: akshare
    log.info(f"push2 unavailable for fund flow {code} — using akshare fallback")
    result = _fetch_from_akshare(code, days)
    if result:
        return result

    # Both sources failed — explicit error, no silent defaults
    status = "push2 down" if push2_status() != "available" else "push2 failed"
    return {"error": "Fund flow data unavailable", "code": code, "source_status": f"{status}, akshare failed"}