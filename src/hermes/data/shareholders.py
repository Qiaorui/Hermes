"""Top shareholders and tradable shareholders."""

from hermes.api.eastmoney import em_get, em_prefix


def stock_shareholders(code: str, top_n: int = 10) -> dict:
    """Get top shareholders and top tradable shareholders. Returns dict with both lists."""
    top_n = min(top_n, 10)
    prefix_code = em_prefix(code)

    shareholders = None
    tradable = None
    for date in ["2025-12-31", "2024-12-31"]:
        if shareholders is None:
            url1 = f"http://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageSDGD?code={prefix_code}&date={date}"
            d1 = em_get(url1)
            if d1 and d1.get("sdgd"):
                shareholders = d1["sdgd"][:top_n]
        if tradable is None:
            url2 = f"http://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageSDLTGD?code={prefix_code}&date={date}"
            d2 = em_get(url2)
            if d2 and d2.get("sdltgd"):
                tradable = d2["sdltgd"][:top_n]
        if shareholders and tradable:
            break

    if not shareholders and not tradable:
        return {"error": "Failed to get shareholder data", "code": code}

    sh_list = []
    for e in (shareholders or []):
        sh_list.append({
            "name": e.get("HOLDER_NAME", ""),
            "hold_num": e.get("HOLD_NUM"),
            "hold_ratio_pct": e.get("HOLD_NUM_RATIO"),
            "change": e.get("HOLD_NUM_CHANGE", ""),
            "change_ratio_pct": e.get("CHANGE_RATIO"),
        })

    tr_list = []
    for e in (tradable or []):
        tr_list.append({
            "name": e.get("HOLDER_NAME", ""),
            "hold_num": e.get("HOLD_NUM"),
            "free_hold_ratio_pct": e.get("FREE_HOLDNUM_RATIO"),
            "holder_type": e.get("HOLDER_TYPE", ""),
            "change": e.get("HOLD_NUM_CHANGE", ""),
            "change_ratio_pct": e.get("CHANGE_RATIO"),
        })

    return {"code": code, "shareholders": sh_list, "tradable_shareholders": tr_list}