"""Recent company announcements."""

from hermes.api.eastmoney import em_get


def stock_announcements(code: str, count: int = 20) -> dict:
    """Get recent company announcements. Returns dict with code, count, announcements."""
    count = min(count, 50)
    url = f"https://np-anotice-stock.eastmoney.com/api/security/ann?page_size={count}&page_index=1&ann_type=A&stock_list={code}&f_node=0&s_node=0"
    data = em_get(url)
    if not data or not data.get("data"):
        return {"error": "Failed to get announcements", "code": code}

    items = data["data"].get("list", [])
    result = []
    for item in items:
        columns = item.get("columns", [])
        category = columns[0].get("column_name", "") if columns else ""
        result.append({
            "date": item.get("notice_date", ""),
            "category": category,
            "title": item.get("title", ""),
            "art_code": item.get("art_code", ""),
        })

    return {"code": code, "count": len(result), "announcements": result}