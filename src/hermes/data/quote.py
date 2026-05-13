"""Real-time stock quote with valuation metrics.

Primary source: push2.eastmoney.com (rate-limited, 30s between requests).
Fallback sources when push2 is unavailable:
  - akshare stock_value_em: PE, PB, PS, market_cap, price (datacenter-based, no rate limit)
  - emweb CompanySurvey: industry, company name
  - datacenter MAINFINADATA: revenue YoY, profit YoY, financial ratios

In-memory cache (60s TTL) prevents redundant calls during a single evaluation run.
"""

import time
import logging
from hermes.api.eastmoney import em_get, emweb_get, parse_secid

log = logging.getLogger(__name__)

# In-memory cache to prevent redundant quote calls across factor modules
_quote_cache: dict[str, tuple[float, dict]] = {}
_QUOTE_CACHE_TTL = 60  # seconds for success
_QUOTE_ERROR_CACHE_TTL = 15  # shorter TTL for errors


def _val(d: dict, key: str) -> float | int | None:
    raw = d.get(key)
    if raw is None or raw == "-":
        return None
    try:
        v = float(raw)
        return int(v) if v == int(v) else v
    except (ValueError, TypeError):
        return None


def _fen(d: dict, key: str) -> float | None:
    v = _val(d, key)
    return v / 100 if v is not None else None


def _pct(d: dict, key: str) -> float | None:
    v = _val(d, key)
    return v / 100 if v is not None else None


def _fetch_from_push2(code: str) -> dict | None:
    """Fetch quote from push2 (primary, rate-limited)."""
    secid = parse_secid(code)
    url = (
        f"http://push2.eastmoney.com/api/qt/stock/get?ut=bd_1_dac_1_12345"
        f"&fields=f9,f23,f37,f43,f44,f45,f46,f47,f48,f50,f55,f57,f58,f84,"
        f"f100,f127,f128,f116,f117,f152,f162,f163,f167,f168,f169,f170,f171,f177"
        f"&secid={secid}"
    )
    data = em_get(url)
    if not data or not data.get("data"):
        return None

    d = data["data"]
    return {
        "code": d.get("f57", code),
        "name": d.get("f58", ""),
        "price": _fen(d, "f43"),
        "high": _fen(d, "f44"),
        "low": _fen(d, "f45"),
        "open": _fen(d, "f46"),
        "volume": _val(d, "f47"),
        "amount": _val(d, "f48"),
        "turnover_rate": _val(d, "f55"),
        "pe_dynamic": _fen(d, "f162"),
        "pe_static": _fen(d, "f163"),
        "pb": _fen(d, "f23"),
        "ps": _fen(d, "f167"),
        "market_cap": _val(d, "f84"),
        "total_shares": _val(d, "f116"),
        "circulating_shares": _val(d, "f117"),
        "revenue_yoy": _pct(d, "f169"),
        "profit_yoy": _pct(d, "f170"),
        "industry": d.get("f127", d.get("f100", "")),
        "region": d.get("f128", ""),
        "source": "push2",
    }


def _fetch_from_fallback(code: str) -> dict | None:
    """Fetch quote from akshare + emweb + datacenter (no push2 dependency)."""
    result = {"code": code, "source": "akshare+datacenter"}

    # 1. akshare stock_value_em — valuation + price + market cap
    try:
        import akshare as ak
        df = ak.stock_value_em(symbol=code)
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            result["price"] = _val(latest, "当日收盘价") or result.get("price")
            result["pe_dynamic"] = _val(latest, "PE(TTM)") or result.get("pe_dynamic")
            result["pe_static"] = _val(latest, "PE(静)") or result.get("pe_static")
            result["pb"] = _val(latest, "市净率") or result.get("pb")
            result["ps"] = _val(latest, "市销率") or result.get("ps")
            result["market_cap"] = _val(latest, "总市值") or result.get("market_cap")
            ts = _val(latest, "总股本")
            result["total_shares"] = int(ts) if ts is not None else result.get("total_shares")
            cs = _val(latest, "流通股本")
            result["circulating_shares"] = int(cs) if cs is not None else result.get("circulating_shares")
    except Exception as e:
        log.warning(f"akshare stock_value_em failed for {code}: {e}")

    # 2. emweb CompanySurvey — industry + company name
    try:
        market = "SZ" if not code.startswith("6") else "SH"
        url = f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax?code={market}{code}"
        data = emweb_get(url)
        if data and data.get("jbzl"):
            jbzl = data["jbzl"]
            item = jbzl[0] if isinstance(jbzl, list) else jbzl
            result["name"] = item.get("SECURITY_NAME_ABBR", "")
            # EM2016 format: "交通运输-物流-物流" → store full hierarchy
            # Use last segment as primary industry, but also store middle segment for broader matching
            em_industry = item.get("EM2016", "")
            if em_industry:
                segments = em_industry.split("-")
                result["industry"] = segments[-1] if segments else ""
                result["industry_group"] = segments[-2] if len(segments) >= 2 else segments[-1] if segments else ""
            result["region"] = item.get("PROVINCE", "")
    except Exception as e:
        log.warning(f"emweb CompanySurvey failed for {code}: {e}")

    # 3. datacenter MAINFINADATA — YoY growth ratios
    try:
        url = (
            f"https://datacenter-web.eastmoney.com/api/data/v1/get?"
            f"sortColumns=REPORT_DATE_NAME&sortTypes=-1&pageSize=1&pageNumber=1"
            f"&reportName=RPT_F10_FINANCE_MAINFINADATA&columns=ALL"
            f"&filter=(SECURITY_CODE=%22{code}%22)"
        )
        data = emweb_get(url)
        if data and data.get("result") and data.get("result").get("data"):
            item = data["result"]["data"][0]
            yoy_rev = item.get("TOTALOPERATEREVETZ")
            yoy_profit = item.get("PARENTNETPROFITTZ")
            if yoy_rev is not None:
                result["revenue_yoy"] = float(yoy_rev)
            if yoy_profit is not None:
                result["profit_yoy"] = float(yoy_profit)
    except Exception as e:
        log.warning(f"datacenter YoY failed for {code}: {e}")

    # 4. Compute turnover_rate from kline volume + circulating shares
    try:
        from hermes.data.kline import stock_kline
        circ = result.get("circulating_shares")
        kdata = stock_kline(code)
        if circ and "error" not in kdata and kdata.get("klines"):
            latest_kline = kdata["klines"][-1]
            volume = latest_kline.get("volume")
            if volume and circ > 0:
                result["turnover_rate"] = round(volume / circ * 100, 2)
                result["volume"] = volume
    except Exception as e:
        log.warning(f"kline turnover computation failed for {code}: {e}")

    # Check if we got minimum essential data
    has_price = result.get("price") is not None and result.get("price") > 0
    has_valuation = result.get("pe_dynamic") is not None or result.get("pe_static") is not None
    if not has_price and not has_valuation:
        return None

    # Mark fields that fallback sources don't provide
    result.setdefault("turnover_rate", None)
    result.setdefault("volume", None)
    result.setdefault("amount", None)
    result.setdefault("high", None)
    result.setdefault("low", None)
    result.setdefault("open", None)

    return result


def stock_quote(code: str) -> dict:
    """Get real-time stock quote. Returns dict with price, PE, PB, PS, market cap, YoY etc.

    Uses in-memory cache (60s TTL) to prevent redundant calls across factor modules.
    """
    # Check cache first
    now = time.time()
    cached = _quote_cache.get(code)
    if cached:
        ttl = _QUOTE_ERROR_CACHE_TTL if "error" in cached[1] else _QUOTE_CACHE_TTL
        if now - cached[0] < ttl:
            return cached[1]

    # Primary: push2
    result = _fetch_from_push2(code)
    if result:
        _quote_cache[code] = (now, result)
        return result

    # Fallback: akshare + datacenter + emweb
    log.info(f"push2 unavailable for {code} — using fallback sources")
    result = _fetch_from_fallback(code)
    if result:
        _quote_cache[code] = (now, result)
        return result

    err = {"error": "Failed to get quote", "code": code}
    _quote_cache[code] = (now, err)
    return err