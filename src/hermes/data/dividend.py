"""Stock dividend history — dividend per share, yield, payout ratio, consistency.

Primary source: akshare stock_fhps_detail_em (分红配送详情, East Money based).
Fallback source: East Money datacenter RPT_F10_DIVIDEND.

Returns dividend history with computed yield and consistency metrics.

Strict data policy: no fallback values. Missing data → None + explicit unavailable label.
"""

import logging
from hermes.api.eastmoney import em_get

log = logging.getLogger(__name__)


def _fetch_from_akshare(code: str) -> dict | None:
    """Fetch dividend history from akshare stock_fhps_detail_em (primary source)."""
    try:
        import akshare as ak
        df = ak.stock_fhps_detail_em(symbol=code)
        if df is None or len(df) == 0:
            return None

        records = []
        for _, row in df.iterrows():
            try:
                # Key column: 现金分红-现金分红比例 (每10股派X元, DPS = X/10)
                cash_div = row.get("现金分红-现金分红比例")
                if cash_div is None:
                    continue
                dps = float(cash_div) / 10  # Convert "10派1.6元" → 0.16元/股
                if dps <= 0:
                    continue
                year = str(row.get("报告期", ""))[:4]
                dividend_yield_raw = row.get("现金分红-股息率")
                yield_pct = float(dividend_yield_raw) * 100 if dividend_yield_raw is not None and str(dividend_yield_raw) not in ("", "-", "nan") else None
                plan_desc = str(row.get("现金分红-现金分红比例描述", ""))
                records.append({
                    "year": year,
                    "dps": dps,
                    "yield_pct": yield_pct,
                    "plan": plan_desc,
                    "progress": str(row.get("方案进度", "")),
                })
            except (ValueError, TypeError):
                continue

        if not records:
            return None
        return {"code": code, "count": len(records), "dividends": records, "source": "akshare"}
    except Exception as e:
        log.warning(f"akshare dividend failed for {code}: {e}")
        return None


def _fetch_from_datacenter(code: str) -> dict | None:
    """Fetch dividend data from East Money datacenter (fallback)."""
    url = (
        f"https://datacenter-web.eastmoney.com/api/data/v1/get?"
        f"sortColumns=REPORT_DATE&sortTypes=-1&pageSize=10&pageNumber=1"
        f"&reportName=RPT_F10_DIVIDEND&columns=ALL"
        f"&filter=(SECURITY_CODE=%22{code}%22)"
    )
    data = em_get(url)
    if not data or not data.get("result") or not data["result"].get("data"):
        return None

    records = []
    for row in data["result"]["data"]:
        dps = row.get("EQUITY_DIVIDEND")  # 每股分红
        if dps is None:
            continue
        try:
            dps = float(dps)
            if dps <= 0:
                continue
            year = str(row.get("REPORT_DATE", ""))[:4]
            records.append({
                "year": year,
                "dps": dps / 10,  # datacenter returns in 角, convert to 元
                "plan": str(row.get("DIVIDEND_PLAN", "")),
            })
        except (ValueError, TypeError):
            continue

    if not records:
        return None
    return {"code": code, "count": len(records), "dividends": records, "source": "datacenter"}


def stock_dividend(code: str, quote: dict | None = None) -> dict:
    """Get dividend history for a stock. Returns yield, payout ratio, consistency.

    Args:
        code: Stock code.
        quote: Optional pre-fetched quote dict (avoids redundant stock_quote call).
    """
    def _get_quote():
        if quote and "error" not in quote:
            return quote
        from hermes.data.quote import stock_quote
        return stock_quote(code)

    # Primary: akshare
    result = _fetch_from_akshare(code)
    if result:
        # Compute derived metrics
        dividends = result["dividends"]
        latest_dps = dividends[0]["dps"] if dividends else None
        years_with_dividends = len(dividends)

        # Consecutive years (from most recent)
        consecutive = 0
        for d in dividends:
            if d["dps"] > 0:
                consecutive += 1
            else:
                break

        # Dividend yield = latest DPS / current price
        dividend_yield = None
        if latest_dps:
            q = _get_quote()
            if "error" not in q and q.get("price"):
                dividend_yield = round(latest_dps / q["price"] * 100, 2)

        # Payout ratio = DPS / EPS
        payout_ratio = None
        if latest_dps:
            from hermes.data.financial import stock_financial
            income = stock_financial(code, "income", 1)
            if "error" not in income and income.get("periods"):
                latest = income["periods"][0]
                q = _get_quote()
                if "error" not in q:
                    total_shares = q.get("total_shares")
                    np_val = latest.get("PARENT_NETPROFIT")
                    if total_shares and np_val and np_val > 0:
                        eps = np_val / (total_shares / 10000)
                        if eps > 0:
                            payout_ratio = round(latest_dps / eps * 100, 2)

        result["latest_dps"] = latest_dps
        result["dividend_yield"] = dividend_yield
        result["payout_ratio"] = payout_ratio
        result["consecutive_years"] = consecutive
        result["total_years"] = years_with_dividends
        return result

    # Fallback: datacenter
    log.info(f"akshare dividend unavailable for {code} — using datacenter fallback")
    result = _fetch_from_datacenter(code)
    if result:
        dividends = result["dividends"]
        latest_dps = dividends[0]["dps"] if dividends else None
        consecutive = 0
        for d in dividends:
            if d["dps"] > 0:
                consecutive += 1
            else:
                break
        dividend_yield = None
        if latest_dps:
            q = _get_quote()
            if "error" not in q and q.get("price"):
                dividend_yield = round(latest_dps / q["price"] * 100, 2)
        result["latest_dps"] = latest_dps
        result["dividend_yield"] = dividend_yield
        result["payout_ratio"] = None
        result["consecutive_years"] = consecutive
        result["total_years"] = len(dividends)
        return result

    return {"error": "Dividend data unavailable", "code": code}