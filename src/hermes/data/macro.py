"""Macro economic indicators for investment context.

Provides key macro data:
  - PMI (manufacturing + non-manufacturing)
  - CPI monthly rate
  - GDP quarterly growth
  - LPR interest rate (1Y + 5Y)
  - M2 money supply growth

Disk cache at .hermes/cache/macro_indicators.json (4-hour TTL).

Strict data policy: returns latest available data. Missing indicators → None.
"""

import logging
from hermes.config import CONFIG_DIR
from hermes.data.cache import DiskCache

log = logging.getLogger(__name__)

_cache = DiskCache(CONFIG_DIR / "cache", "macro_indicators.json", ttl=4 * 3600)


def _safe_float(val) -> float | None:
    """Convert value to float, treating None/NaN as None but preserving legitimate 0."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if str(val) in ("nan", "NaN") else f
    except (ValueError, TypeError):
        return None


def _fetch_pmi() -> dict | None:
    """Fetch latest PMI data."""
    try:
        import akshare as ak
        df = ak.macro_china_pmi()
        if df is None or len(df) == 0:
            return None
        latest = df.iloc[0]
        return {
            "manufacturing_pmi": _safe_float(latest.get("制造业-指数")),
            "manufacturing_yoy": _safe_float(latest.get("制造业-同比增长")),
            "non_manufacturing_pmi": _safe_float(latest.get("非制造业-指数")),
            "non_manufacturing_yoy": _safe_float(latest.get("非制造业-同比增长")),
            "date": str(latest.get("月份", "")),
        }
    except Exception as e:
        log.warning(f"PMI fetch failed: {e}")
        return None


def _fetch_cpi() -> dict | None:
    """Fetch latest CPI data."""
    try:
        import akshare as ak
        df = ak.macro_china_cpi_monthly()
        if df is None or len(df) == 0:
            return None
        # Filter for 中国CPI月率报告
        cpi_rows = df[df["商品"] == "中国CPI月率报告"]
        if len(cpi_rows) == 0:
            cpi_rows = df
        latest = cpi_rows.iloc[0]
        return {
            "cpi_monthly_rate": _safe_float(latest.get("今值")),
            "cpi_forecast": _safe_float(latest.get("预测值")),
            "cpi_previous": _safe_float(latest.get("前值")),
            "date": str(latest.get("日期", "")),
        }
    except Exception as e:
        log.warning(f"CPI fetch failed: {e}")
        return None


def _fetch_gdp() -> dict | None:
    """Fetch latest GDP data."""
    try:
        import akshare as ak
        df = ak.macro_china_gdp()
        if df is None or len(df) == 0:
            return None
        latest = df.iloc[0]
        return {
            "gdp_absolute": _safe_float(latest.get("国内生产总值-绝对值")),
            "gdp_yoy": _safe_float(latest.get("国内生产总值-同比增长")),
            "secondary_industry_yoy": _safe_float(latest.get("第二产业-同比增长")),
            "tertiary_industry_yoy": _safe_float(latest.get("第三产业-同比增长")),
            "date": str(latest.get("季度", "")),
        }
    except Exception as e:
        log.warning(f"GDP fetch failed: {e}")
        return None


def _fetch_lpr() -> dict | None:
    """Fetch latest LPR interest rate."""
    try:
        import akshare as ak
        df = ak.macro_china_lpr()
        if df is None or len(df) == 0:
            return None
        latest = df.iloc[0]
        return {
            "lpr_1y": _safe_float(latest.get("LPR1Y")),
            "lpr_5y": _safe_float(latest.get("LPR5Y")),
            "date": str(latest.get("TRADE_DATE", "")),
        }
    except Exception as e:
        log.warning(f"LPR fetch failed: {e}")
        return None


def _fetch_m2() -> dict | None:
    """Fetch latest M2 money supply data."""
    try:
        import akshare as ak
        df = ak.macro_china_money_supply()
        if df is None or len(df) == 0:
            return None
        latest = df.iloc[0]
        return {
            "m2_yoy": _safe_float(latest.get("货币和准货币(M2)-同比增长")),
            "m1_yoy": _safe_float(latest.get("货币(M1)-同比增长")),
            "date": str(latest.get("月份", "")),
        }
    except Exception as e:
        log.warning(f"M2 fetch failed: {e}")
        return None


def macro_indicators() -> dict:
    """Get latest macro economic indicators.

    Uses disk cache (4h TTL) to avoid repeated akshare API calls.
    Returns PMI, CPI, GDP, LPR, M2 data.
    """
    cached = _cache.load()
    if cached:
        return cached

    result = {
        "pmi": _fetch_pmi(),
        "cpi": _fetch_cpi(),
        "gdp": _fetch_gdp(),
        "lpr": _fetch_lpr(),
        "m2": _fetch_m2(),
    }

    # Cache even if some indicators failed
    _cache.save(result)
    return result