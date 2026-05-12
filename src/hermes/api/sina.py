"""Sina Finance API helpers."""

import json
import requests
from hermes.api.eastmoney import FETCH_HEADERS


def fetch_kline(symbol: str, days: int = 120) -> list[dict] | None:
    """Fetch K-line data from Sina Finance. Returns list of raw dicts or None on error."""
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}"
    try:
        r = requests.get(url, headers=FETCH_HEADERS, timeout=15)
        r.raise_for_status()
        return json.loads(r.text)
    except Exception:
        return None


def parse_klines(raw: list[dict]) -> list[dict]:
    """Parse raw Sina K-line data into standardized format with change_pct."""
    result = []
    prev_close = None
    for k in raw:
        close = float(k.get("close", 0))
        change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close and prev_close > 0 else None
        result.append({
            "date": k.get("day", ""),
            "open": float(k.get("open", 0)),
            "high": float(k.get("high", 0)),
            "low": float(k.get("low", 0)),
            "close": close,
            "volume": int(float(k.get("volume", 0))),
            "change_pct": change_pct,
        })
        prev_close = close
    return result