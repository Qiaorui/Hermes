"""Stock screening — fetch and filter A-share stocks from push2 API."""

from hermes.api.eastmoney import em_get


def screen_stocks(
    industry: str = "",
    pe_max: float = 0,
    pe_min: float = 0,
    pb_max: float = 0,
    pb_min: float = 0,
    cap_min: float = 0,
    cap_max: float = 0,
    turnover_min: float = 0,
    profit_yoy_min: float = 0,
    revenue_yoy_min: float = 0,
    limit: int = 20,
) -> list[dict]:
    """Screen A-share stocks by criteria. Returns filtered ranked list.

    Args:
        industry: Industry name filter (empty = all).
        pe_max: PE upper limit (0 = no limit).
        pe_min: PE lower limit (0 = no limit).
        pb_max: PB upper limit (0 = no limit).
        pb_min: PB lower limit (0 = no limit).
        cap_min: Market cap minimum in 亿元 (0 = no limit).
        cap_max: Market cap maximum in 亿元 (0 = no limit).
        turnover_min: Turnover rate minimum % (0 = no limit).
        profit_yoy_min: Net profit YoY growth minimum % (0 = no limit).
        revenue_yoy_min: Revenue YoY growth minimum % (0 = no limit).
        limit: Maximum number of results (default 20).
    """
    stocks = []
    # f9=PE, f23=PB, f20=market_cap, f55=turnover, f115=profit_yoy, f169=revenue_yoy, f170=profit_yoy(alternate)
    for fs in ["m:1+t:2,m:0+t:6,m:0+t:80,m:1+t:23"]:
        url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit*3}&po=1&np=1&fltt=2&invt=2&fs={fs}&fields=f2,f3,f12,f14,f9,f20,f23,f55,f100,f115,f169,f170"
        data = em_get(url)
        if data and data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                name = item.get("f14", "")
                code = item.get("f12", "")
                price = item.get("f2", "-")
                change_pct = item.get("f3", "-")
                pe = item.get("f9", "-")
                market_cap = item.get("f20", "-")
                pb = item.get("f23", "-")
                turnover_rate = item.get("f55", "-")
                profit_yoy_pct = item.get("f115", "-")
                revenue_yoy_pct = item.get("f169", "-")
                industry_name = item.get("f100", "")

                if price == "-" or pe == "-" or code == "":
                    continue

                try:
                    pe_val = float(pe)
                    if pe_max > 0 and pe_val > pe_max:
                        continue
                    if pe_min > 0 and pe_val < pe_min:
                        continue
                except (ValueError, TypeError):
                    continue

                if pb_max > 0 or pb_min > 0:
                    try:
                        pb_val = float(pb)
                        if pb_max > 0 and pb_val > pb_max:
                            continue
                        if pb_min > 0 and pb_val < pb_min:
                            continue
                    except (ValueError, TypeError):
                        continue

                if cap_min > 0 or cap_max > 0:
                    try:
                        cap_yi = float(market_cap) / 1e8
                        if cap_min > 0 and cap_yi < cap_min:
                            continue
                        if cap_max > 0 and cap_yi > cap_max:
                            continue
                    except (ValueError, TypeError):
                        continue

                if turnover_min > 0:
                    try:
                        if float(turnover_rate) < turnover_min:
                            continue
                    except (ValueError, TypeError):
                        continue

                if profit_yoy_min > 0:
                    try:
                        if float(profit_yoy_pct) < profit_yoy_min:
                            continue
                    except (ValueError, TypeError):
                        continue

                if revenue_yoy_min > 0:
                    try:
                        if float(revenue_yoy_pct) < revenue_yoy_min:
                            continue
                    except (ValueError, TypeError):
                        continue

                if industry and industry_name != industry:
                    continue

                stocks.append({
                    "code": code, "name": name, "price": price,
                    "change_pct": change_pct, "pe": pe, "pb": pb,
                    "market_cap_yi": round(float(market_cap) / 1e8, 1) if market_cap != "-" else 0,
                    "turnover_rate": turnover_rate,
                    "profit_yoy_pct": profit_yoy_pct, "revenue_yoy_pct": revenue_yoy_pct,
                    "industry": industry_name,
                })

    stocks.sort(key=lambda x: float(x.get("profit_yoy_pct", 0)) if x.get("profit_yoy_pct", "-") != "-" else -999, reverse=True)
    return stocks[:limit]