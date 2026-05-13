"""Corporate event calendar — upcoming earnings, dividend, and key dates.

Primary source: akshare stock_em_disclosure (业绩披露时间表).
Disk cache at .hermes/cache/event_calendar.json with 2-hour TTL.

Strict data policy: no fallback values. Missing data → None.
"""

import logging
from hermes.config import CONFIG_DIR
from hermes.data.cache import DiskCache

log = logging.getLogger(__name__)

_cache = DiskCache(CONFIG_DIR / "cache", "event_calendar.json", ttl=2 * 3600)


def _fetch_disclosure(code: str) -> dict | None:
    """Fetch upcoming earnings disclosure dates for a stock."""
    try:
        import akshare as ak
        df = ak.stock_em_disclosure(date="")
        if df is None or len(df) == 0:
            return None
        row = df[df["股票代码"] == code]
        if len(row) == 0:
            return None
        r = row.iloc[0]
        return {
            "earnings_date": str(r.get("预约披露日期", "")),
            "earnings_period": str(r.get("预约披露类型", "")),
            "actual_date": str(r.get("实际披露日期", "")),
            "quarter": str(r.get("报告期", "")),
        }
    except Exception as e:
        log.warning(f"Disclosure fetch failed for {code}: {e}")
        return None


def _fetch_dividend_schedule(code: str) -> dict | None:
    """Fetch upcoming dividend payment dates."""
    try:
        from hermes.data.dividend import stock_dividend
        div = stock_dividend(code)
        if "error" in div:
            return None
        dividends = div.get("dividends", [])
        if not dividends:
            return None
        latest = dividends[0]
        return {
            "dividend_year": latest.get("year", ""),
            "dividend_plan": latest.get("plan", ""),
            "dividend_progress": latest.get("progress", ""),
            "dividend_dps": latest.get("dps"),
        }
    except Exception as e:
        log.warning(f"Dividend schedule fetch failed for {code}: {e}")
        return None


def corporate_events(code: str) -> dict:
    """Get upcoming corporate events for a stock (earnings dates, dividend schedule).

    Returns dict with earnings disclosure and dividend payment info.
    """
    cached = _cache.load()
    if cached and code in cached:
        return cached[code]

    result = {
        "code": code,
        "earnings": _fetch_disclosure(code),
        "dividend": _fetch_dividend_schedule(code),
    }

    # Cache result
    if cached is None:
        cached = {}
    cached[code] = result
    _cache.save(cached)
    return result