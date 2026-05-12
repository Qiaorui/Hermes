"""Industry benchmark data for factor neutralization.

Primary source: akshare Shenwan (申万) industry classification — provides 131
secondary industries with PE/PB/dividend_yield computed by Shenwan directly.
Uses a different API endpoint than push2.eastmoney.com, immune to push2 anti-scraping.

Fallback source: push2 clist API (rate-limited, 31s between requests).

Disk cache at .hermes/cache/industry_benchmarks.json with 4-hour TTL.
When push2 is down, akshare ensures benchmarks are still available.
"""

import json
import time
import logging
import statistics
from hermes.api.eastmoney import em_get
from hermes.config import CONFIG_DIR

log = logging.getLogger(__name__)

CACHE_DIR = CONFIG_DIR / "cache"
CACHE_FILE = CACHE_DIR / "industry_benchmarks.json"
CACHE_TTL = 4 * 3600  # 4 hours


def _fetch_from_akshare() -> dict:
    """Fetch industry benchmarks via akshare Shenwan API (primary source).
    Returns {industry_name: {pe_median, pb_median, ...}}
    """
    try:
        import akshare as ak
        df = ak.sw_index_second_info()
        result = {}
        for _, row in df.iterrows():
            name = row["行业名称"]
            result[name] = {
                "pe_median": row["静态市盈率"] if row["静态市盈率"] else None,
                "pe_ttm_median": row["TTM(滚动)市盈率"] if row["TTM(滚动)市盈率"] else None,
                "pb_median": row["市净率"] if row["市净率"] else None,
                "dividend_yield_median": row["静态股息率"] if row["静态股息率"] else None,
                "count": int(row["成份个数"]) if row["成份个数"] else 0,
                "parent_industry": row["上级行业"] if row.get("上级行业") else None,
            }
        # Also add first-level industries for broader matching
        df1 = ak.sw_index_first_info()
        for _, row in df1.iterrows():
            name = row["行业名称"]
            if name not in result:
                result[name] = {
                    "pe_median": row["静态市盈率"] if row["静态市盈率"] else None,
                    "pe_ttm_median": row["TTM(滚动)市盈率"] if row["TTM(滚动)市盈率"] else None,
                    "pb_median": row["市净率"] if row["市净率"] else None,
                    "dividend_yield_median": row["静态股息率"] if row["静态股息率"] else None,
                    "count": int(row["成份个数"]) if row["成份个数"] else 0,
                    "parent_industry": None,
                }
        log.info(f"akshare: {len(result)} industries (131 secondary + 31 primary)")
        return result
    except Exception as e:
        log.warning(f"akshare Shenwan fetch failed: {e}")
        return {}


def _fetch_from_push2() -> dict:
    """Fetch via push2 clist API (fallback, rate-limited)."""
    all_items = []
    for page in [1, 2]:
        url = (
            f"http://push2.eastmoney.com/api/qt/clist/get?pn={page}&pz=500&po=1&np=1&fltt=2"
            "&invt=2&fs=m:1+t:2,m:0+t:6,m:0+t:80,m:1+t:23"
            "&fields=f2,f3,f7,f9,f12,f14,f20,f23,f100,f115,f169,f170"
        )
        data = em_get(url, timeout=20)
        if data and data.get("data") and data["data"].get("diff"):
            all_items.extend(data["data"]["diff"])
        else:
            break

    if not all_items:
        return {}

    benchmarks = {}
    for item in all_items:
        ind = item.get("f100")
        if not ind or ind == "-":
            continue
        if ind not in benchmarks:
            benchmarks[ind] = {"pe": [], "pb": [], "turnover": [], "profit_yoy": [], "revenue_yoy": [], "count": 0}
        try:
            pe_val = float(item.get("f9", "-")) if item.get("f9") != "-" else None
            pb_val = float(item.get("f23", "-")) if item.get("f23") != "-" else None
            to_val = float(item.get("f7", "-")) if item.get("f7") != "-" else None
            py_val = float(item.get("f115", "-")) if item.get("f115") != "-" else None
            ry_val = float(item.get("f169", "-")) if item.get("f169") != "-" else None
            if pe_val and pe_val > 0:
                benchmarks[ind]["pe"].append(pe_val)
            if pb_val and pb_val > 0:
                benchmarks[ind]["pb"].append(pb_val)
            if to_val is not None and to_val > 0:
                benchmarks[ind]["turnover"].append(to_val)
            if py_val is not None:
                benchmarks[ind]["profit_yoy"].append(py_val)
            if ry_val is not None:
                benchmarks[ind]["revenue_yoy"].append(ry_val)
        except (ValueError, TypeError):
            pass
        benchmarks[ind]["count"] += 1

    result = {}
    for ind, data in benchmarks.items():
        if data["count"] < 3:
            continue
        result[ind] = {
            "pe_median": statistics.median(data["pe"]) if len(data["pe"]) >= 3 else None,
            "pb_median": statistics.median(data["pb"]) if len(data["pb"]) >= 3 else None,
            "turnover_median": statistics.median(data["turnover"]) if len(data["turnover"]) >= 3 else None,
            "profit_yoy_median": statistics.median(data["profit_yoy"]) if len(data["profit_yoy"]) >= 3 else None,
            "revenue_yoy_median": statistics.median(data["revenue_yoy"]) if len(data["revenue_yoy"]) >= 3 else None,
            "count": data["count"],
        }
    log.info(f"push2: {len(result)} industries from {len(all_items)} stocks")
    return result


def _merge_benchmarks(akshare_data: dict, push2_data: dict) -> dict:
    """Merge akshare and push2 data. akshare is primary, push2 fills gaps."""
    merged = dict(akshare_data)  # start with akshare

    # Add push2 fields (turnover, profit_yoy, revenue_yoy) that akshare doesn't have
    for ind, data in push2_data.items():
        # Find matching industry in merged
        matched_key = None
        if ind in merged:
            matched_key = ind
        else:
            for mk in merged:
                if ind in mk or mk in ind:
                    matched_key = mk
                    break

        if matched_key:
            # Add push2-specific fields to existing entry
            for field in ["turnover_median", "profit_yoy_median", "revenue_yoy_median"]:
                if data.get(field) and not merged[matched_key].get(field):
                    merged[matched_key][field] = data[field]
        else:
            # New industry not in akshare
            merged[ind] = data

    return merged


def _save_disk_cache(data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.time(), "source": "akshare+push2", "benchmarks": data}
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False))
    log.info(f"Saved {len(data)} industry benchmarks to {CACHE_FILE}")


def _load_disk_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        payload = json.loads(CACHE_FILE.read_text())
        ts = payload.get("timestamp", 0)
        if time.time() - ts > CACHE_TTL:
            log.info("Industry benchmarks cache expired (>4h)")
            return None
        data = payload.get("benchmarks", {})
        if not data:
            return None
        age = int(time.time() - ts)
        log.info(f"Loaded {len(data)} industry benchmarks from cache (age: {age}s, source: {payload.get('source')})")
        return data
    except Exception:
        return None


def get_industry_benchmarks() -> dict:
    """Get industry benchmarks: disk cache → akshare (primary) → push2 (fallback)."""
    cached = _load_disk_cache()
    if cached:
        return cached

    # Primary: akshare Shenwan data
    ak_data = _fetch_from_akshare()
    if ak_data:
        # Try push2 for supplementary data (turnover, YoY growth)
        push2_data = _fetch_from_push2()
        if push2_data:
            merged = _merge_benchmarks(ak_data, push2_data)
            _save_disk_cache(merged)
            return merged
        else:
            _save_disk_cache(ak_data)
            return ak_data

    # akshare failed — try push2 alone
    push2_data = _fetch_from_push2()
    if push2_data:
        _save_disk_cache(push2_data)
        return push2_data

    log.warning("All industry benchmark sources failed — factor scores will show unavailable")
    return {}


def _match_industry(industry: str, benchmarks: dict) -> str | None:
    """Find matching benchmark key for a given industry name.
    Uses direct match, suffix-stripped match, substring match, and keyword match.
    """
    if not industry:
        return None
    # Direct match
    if industry in benchmarks:
        return industry
    # Strip Shenwan suffixes (Ⅱ, Ⅲ)
    query = industry.replace("Ⅱ", "").replace("Ⅲ", "").strip()
    # Exact match after stripping
    for key in benchmarks:
        base = key.replace("Ⅱ", "").replace("Ⅲ", "").strip()
        if query == base:
            return key
    # Substring match (either direction)
    for key in benchmarks:
        base = key.replace("Ⅱ", "").replace("Ⅲ", "").strip()
        if query in base or base in query:
            return key
    # Keyword overlap: split both names into keywords and find best overlap
    query_words = set(query.replace("、", " ").replace(",", " ").split())
    best_key = None
    best_overlap = 0
    for key in benchmarks:
        base = key.replace("Ⅱ", "").replace("Ⅲ", "").strip()
        base_words = set(base.replace("、", " ").replace(",", " ").split())
        overlap = len(query_words & base_words)
        if overlap > best_overlap and overlap >= 1:
            best_overlap = overlap
            best_key = key
    return best_key


def get_industry_median(code: str) -> dict | None:
    """Get industry median benchmarks for a specific stock."""
    from hermes.data.quote import stock_quote

    q = stock_quote(code)
    if "error" in q:
        return None

    industry = q.get("industry", "")
    if not industry:
        return None

    benchmarks = get_industry_benchmarks()
    matched = _match_industry(industry, benchmarks)
    if matched:
        return {"industry": matched, **benchmarks[matched]}
    return None


def get_industry_median_from_quote(quote: dict) -> dict | None:
    """Get industry median benchmarks using a pre-fetched quote dict.
    Tries industry name first, then industry_group (broader classification) as fallback.
    """
    benchmarks = get_industry_benchmarks()
    for field in ["industry", "industry_group"]:
        name = quote.get(field, "")
        if name:
            matched = _match_industry(name, benchmarks)
            if matched:
                return {"industry": matched, **benchmarks[matched]}
    return None


def industry_percentile(value: float | None, industry: str, metric: str) -> float | None:
    """Compute where a value falls within its industry distribution (0-100 percentile).
    Returns None when benchmarks unavailable or metric unrecognized.
    """
    benchmarks = get_industry_benchmarks()
    bench = benchmarks.get(industry)
    if not bench or value is None:
        return None

    # Use pe_ttm_median for PE percentile (more accurate than static PE)
    median_key = "pe_ttm_median" if metric == "pe" else f"{metric}_median"
    median = bench.get(median_key)
    # Fallback to pe_median if pe_ttm not available
    if metric == "pe" and median is None:
        median = bench.get("pe_median")
    if median is None:
        return None

    lower_is_better = metric in ["pe", "pb"]
    higher_is_better = metric in ["profit_yoy", "revenue_yoy", "turnover"]

    if median == 0:
        return None

    ratio = value / median

    if lower_is_better:
        if ratio <= 0.3: return 95.0
        elif ratio <= 0.5: return 80.0
        elif ratio <= 0.8: return 70.0
        elif ratio <= 1.0: return 55.0
        elif ratio <= 1.5: return 35.0
        elif ratio <= 2.0: return 20.0
        elif ratio <= 3.0: return 10.0
        else: return 5.0
    elif higher_is_better:
        if ratio >= 3.0: return 95.0
        elif ratio >= 2.0: return 80.0
        elif ratio >= 1.5: return 70.0
        elif ratio >= 1.0: return 55.0
        elif ratio >= 0.5: return 35.0
        elif ratio >= 0.0: return 20.0
        elif ratio >= -0.5: return 10.0
        else: return 5.0
    else:
        return None