"""Daily K-line data (OHLCV + change%).

Primary: Sina Finance API.
Fallback: akshare stock_zh_a_hist (East Money historical data).
"""

import logging

from hermes.api.sina import fetch_kline, parse_klines

log = logging.getLogger(__name__)


def stock_kline(code: str, days: int = 120) -> dict:
    """Get daily K-line data. Returns dict with code, count, klines."""
    days = min(days, 500)
    code_clean = code.strip()
    prefix = "sh" if code_clean.startswith("6") else "sz"
    symbol = f"{prefix}{code_clean}"

    # Primary: Sina
    raw = fetch_kline(symbol, days)
    if raw and len(raw) > 0:
        klines = parse_klines(raw)
        return {"code": code, "count": len(klines), "klines": klines}

    # Fallback: akshare
    log.info(f"Sina kline failed for {code} — trying akshare fallback")
    try:
        import akshare as ak
        from datetime import date, timedelta

        end_date = date.today().strftime("%Y%m%d")
        start_date = (date.today() - timedelta(days=days * 2)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(symbol=code_clean, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is not None and len(df) > 0:
            df = df.tail(days)
            klines = []
            for _, row in df.iterrows():
                try:
                    klines.append({
                        "date": str(row.get("日期", "")),
                        "open": float(row.get("开盘", 0)) if row.get("开盘") else None,
                        "high": float(row.get("最高", 0)) if row.get("最高") else None,
                        "low": float(row.get("最低", 0)) if row.get("最低") else None,
                        "close": float(row.get("收盘", 0)) if row.get("收盘") else None,
                        "volume": float(row.get("成交量", 0)) if row.get("成交量") else None,
                        "amount": float(row.get("成交额", 0)) if row.get("成交额") else None,
                        "change_pct": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                    })
                except (ValueError, TypeError):
                    continue
            if klines:
                return {"code": code, "count": len(klines), "klines": klines}
    except Exception as e:
        log.warning(f"akshare kline fallback failed for {code}: {e}")

    return {"error": "K-line fetch failed (Sina + akshare)", "code": code}