"""MCP server — thin wrapper over data modules, returns JSON strings."""

import json
from mcp.server.fastmcp import FastMCP

from hermes.api.search import search_text, search_news, fetch_page, BACKENDS
from hermes.data.quote import stock_quote
from hermes.data.kline import stock_kline
from hermes.data.fund_flow import stock_fund_flow
from hermes.data.announcements import stock_announcements
from hermes.data.valuation import stock_valuation_history
from hermes.data.financial import stock_financial
from hermes.data.shareholders import stock_shareholders
from hermes.data.unlock import stock_unlock_schedule
from hermes.data.market import market_index

mcp = FastMCP("web-search")


# ── Web search tools ──

@mcp.tool()
def web_search(query: str, max_results: int = 10, backend: str = "google") -> str:
    """Search the web. Returns search results with titles, URLs, and descriptions.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 10, max 20).
        backend: Search backend, 'google' (default) or 'lite'. Try 'lite' if 'google' fails.
    """
    if backend not in BACKENDS:
        backend = "google"
    max_results = min(max_results, 20)
    results = search_text(query, max_results, backend)
    if not results:
        return json.dumps({"error": "No results found", "query": query}, ensure_ascii=False)
    return json.dumps({"query": query, "count": len(results), "results": results}, ensure_ascii=False)


@mcp.tool()
def web_search_news(query: str, max_results: int = 10) -> str:
    """Search news articles. Returns recent news with titles, URLs, descriptions, source and date.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 10, max 20).
    """
    max_results = min(max_results, 20)
    results = search_news(query, max_results)
    if not results:
        return json.dumps({"error": "No news results found", "query": query}, ensure_ascii=False)
    return json.dumps({"query": query, "count": len(results), "results": results}, ensure_ascii=False)


@mcp.tool()
def web_fetch_page(url: str, keywords: list[str] | None = None, max_length: int = 5000) -> str:
    """Fetch a web page and extract its text content. Useful for reading article details.
    Automatically handles Chinese encoding (gb2312/gbk/utf-8). PDF URLs return metadata only.

    Args:
        url: The URL to fetch.
        keywords: Optional list of keywords to filter relevant text snippets.
        max_length: Maximum total text length to return (default 5000).
    """
    result = fetch_page(url, keywords, max_length)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def web_fetch_pdf(url: str, keywords: list[str] | None = None, max_length: int = 5000) -> str:
    """Fetch a PDF file and extract its text content. Useful for reading research report PDFs.

    Args:
        url: The PDF URL to fetch (e.g. from mcp_stock_analyst's pdf_url field).
        keywords: Optional list of keywords to filter relevant text snippets.
        max_length: Maximum total text length to return (default 5000).
    """
    from hermes.api.search import fetch_pdf
    result = fetch_pdf(url, keywords, max_length)
    return json.dumps(result, ensure_ascii=False)


# ── Stock data tools ──

@mcp.tool()
def mcp_stock_quote(code: str) -> str:
    """Get real-time stock quote with valuation metrics.

    Args:
        code: Stock code, e.g. '002352' for Shenzhen, '603636' for Shanghai.
    """
    return json.dumps(stock_quote(code), ensure_ascii=False)


@mcp.tool()
def mcp_stock_kline(code: str, days: int = 120) -> str:
    """Get daily K-line data (OHLCV + change%) for a stock.

    Args:
        code: Stock code, e.g. '002352'.
        days: Number of recent trading days (default 120, max 500).
    """
    return json.dumps(stock_kline(code, days), ensure_ascii=False)


@mcp.tool()
def mcp_stock_fund_flow(code: str, days: int = 30) -> str:
    """Get daily fund flow data (main force, small/medium/large/super large net inflow).

    Args:
        code: Stock code, e.g. '002352'.
        days: Number of recent days (default 30, max 120).
    """
    return json.dumps(stock_fund_flow(code, days), ensure_ascii=False)


@mcp.tool()
def mcp_stock_announcements(code: str, count: int = 20) -> str:
    """Get recent company announcements (type, date, title).

    Args:
        code: Stock code, e.g. '002352'.
        count: Number of recent announcements (default 20, max 50).
    """
    return json.dumps(stock_announcements(code, count), ensure_ascii=False)


@mcp.tool()
def mcp_stock_valuation_history(code: str) -> str:
    """Get historical PE/PB percentile for valuation context.

    Args:
        code: Stock code, e.g. '002352'.
    """
    return json.dumps(stock_valuation_history(code), ensure_ascii=False)


@mcp.tool()
def mcp_stock_financial(code: str, report_type: str = "income", count: int = 4) -> str:
    """Get multi-period financial statement data (income/balance/cashflow).

    Args:
        code: Stock code, e.g. '002352'.
        report_type: Statement type - 'income', 'balance', or 'cashflow' (default 'income').
        count: Number of recent periods (default 4, max 8).
    """
    return json.dumps(stock_financial(code, report_type, count), ensure_ascii=False)


@mcp.tool()
def mcp_stock_shareholders(code: str, top_n: int = 10) -> str:
    """Get top shareholders and top tradable shareholders.

    Args:
        code: Stock code, e.g. '002352' for Shenzhen, '603636' for Shanghai.
        top_n: Number of top shareholders per list (default 10, max 10).
    """
    return json.dumps(stock_shareholders(code, top_n), ensure_ascii=False)


@mcp.tool()
def mcp_stock_unlock_schedule(code: str) -> str:
    """Get upcoming restricted share unlock schedule.

    Args:
        code: Stock code, e.g. '002352'.
    """
    return json.dumps(stock_unlock_schedule(code), ensure_ascii=False)


@mcp.tool()
def mcp_market_index(days: int = 60) -> str:
    """Get recent market index data (Shanghai Composite + Shenzhen Component).

    Args:
        days: Number of recent trading days (default 60, max 500).
    """
    return json.dumps(market_index(days), ensure_ascii=False)


@mcp.tool()
def mcp_stock_dividend(code: str) -> str:
    """Get dividend history for a stock (dividend per share, yield, payout ratio, consistency).

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.dividend import stock_dividend
    return json.dumps(stock_dividend(code), ensure_ascii=False)


@mcp.tool()
def mcp_industry_chain(code: str) -> str:
    """Get industry chain analysis — supply chain positioning, peer companies, competitive landscape.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.industry_chain import industry_chain
    return json.dumps(industry_chain(code), ensure_ascii=False)


@mcp.tool()
def mcp_macro_indicators() -> str:
    """Get latest macro economic indicators (PMI, CPI, GDP, LPR, M2)."""
    from hermes.data.macro import macro_indicators
    return json.dumps(macro_indicators(), ensure_ascii=False)


@mcp.tool()
def mcp_stock_analyst(code: str) -> str:
    """Get analyst research data — research reports, profit forecasts, institutional participation.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.analyst import stock_analyst
    return json.dumps(stock_analyst(code), ensure_ascii=False)


@mcp.tool()
def mcp_dragon_tiger(date: str = "") -> str:
    """Get dragon-tiger list (龙虎榜) — hot money activity for a trading day.

    Args:
        date: Trading date in YYYYMMDD format (empty = most recent available day).
    """
    from hermes.data.dragon_tiger import dragon_tiger_list
    return json.dumps(dragon_tiger_list(date), ensure_ascii=False)


@mcp.tool()
def mcp_northbound_flow(days: int = 30) -> str:
    """Get daily northbound capital net flow (沪股通+深股通合计).

    Args:
        days: Number of recent days (default 30, max 120).
    """
    from hermes.data.northbound import northbound_flow
    return json.dumps(northbound_flow(days), ensure_ascii=False)


# ── Industry & factor tools ──

@mcp.tool()
def mcp_industry_benchmarks(industry: str = "") -> str:
    """Get industry median benchmarks (PE, PB, dividend_yield, profit YoY, revenue YoY).
    Used for industry-neutralized factor scoring.

    Args:
        industry: Optional industry name to filter (empty = all industries).
    """
    from hermes.data.industry import get_industry_benchmarks
    bench = get_industry_benchmarks()
    if industry:
        matched = {}
        for k in bench:
            if industry in k or k in industry:
                matched[k] = bench[k]
        if not matched:
            return json.dumps({"error": f"No match for '{industry}'", "available": list(bench.keys())[:20]}, ensure_ascii=False)
        return json.dumps(matched, ensure_ascii=False)
    return json.dumps(bench, ensure_ascii=False)


@mcp.tool()
def mcp_factor_score(code: str, factors: str = "") -> str:
    """Compute quantitative factor scores for a stock. Returns 0-10 scores per factor.

    Args:
        code: Stock code, e.g. '002352'.
        factors: Comma-separated factor names (empty = all). Options: value,growth,quality,dividend,momentum,capital_flow,volatility,liquidity.
    """
    from hermes.factors import factor_score, ALL_FACTORS
    names = [f.strip() for f in factors.split(",") if f.strip()] if factors else None
    result = factor_score(code, names)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def mcp_factor_composite(code: str, weights: str = "") -> str:
    """Compute composite multi-factor score with configurable weights. Returns total score and signal.

    Default weights come from user config (~/.hermes/config.json), or fall back to:
    value=0.20, growth=0.20, quality=0.20, dividend=0.15, momentum=0.06, capital_flow=0.06, volatility=0.06, liquidity=0.07
    Signal: score>=7→buy, >=5→hold, >=3→watch, <3→sell

    Args:
        code: Stock code, e.g. '002352'.
        weights: Optional JSON dict of factor weights, e.g. '{"value":0.3,"growth":0.2,"quality":0.3}'.
    """
    from hermes.factors.composite import composite_factor
    import json as _json
    if weights:
        try:
            w = _json.loads(weights)
        except Exception:
            w = None
    else:
        w = None
    result = composite_factor(code, w)
    return json.dumps(result, ensure_ascii=False)


# ── Report & trigger storage tools ──

@mcp.tool()
def save_evaluation_report(code: str, content: str, score: int = 0) -> str:
    """Save an evaluation report to the portfolio database. Called by the evaluate-stock skill after generating a full report.

    Args:
        code: Stock code, e.g. '002352'.
        content: Full markdown report content.
        score: Overall score (e.g. 22 out of 50).
    """
    from hermes.portfolio.db import save_report
    result = save_report(code, content, score)
    return json.dumps({"status": "saved", "code": result.code, "score": result.score}, ensure_ascii=False)


@mcp.tool()
def save_trigger_conditions(code: str, name: str, triggers_json: str) -> str:
    """Save trigger conditions to the portfolio database. Called by the evaluate-stock skill after analysis.

    Args:
        code: Stock code, e.g. '002352'.
        name: Stock name, e.g. '顺丰控股'.
        triggers_json: JSON array of trigger dicts, each with 'type', 'value', 'description'.
    """
    from hermes.portfolio.db import save_triggers
    from hermes.portfolio.models import TriggerCondition
    import json as _json
    try:
        triggers = _json.loads(triggers_json)
    except Exception:
        return json.dumps({"error": "Invalid triggers_json", "code": code}, ensure_ascii=False)

    models = [TriggerCondition(code=code, name=name, type=t.get("type", ""), value=t.get("value", 0), description=t.get("description", "")) for t in triggers]
    save_triggers(models)
    return json.dumps({"status": "saved", "code": code, "count": len(models)}, ensure_ascii=False)


# ── Portfolio CRUD tools ──

@mcp.tool()
def mcp_add_holding(code: str, name: str, cost_price: float, shares: int, buy_date: str = "") -> str:
    """Add a stock to portfolio holdings.

    Args:
        code: Stock code, e.g. '002352'.
        name: Stock name, e.g. '顺丰控股'.
        cost_price: Buy price per share.
        shares: Number of shares held.
        buy_date: Buy date in YYYY-MM-DD format (empty = today).
    """
    from datetime import date as _date
    from hermes.portfolio.db import add_holding
    if not buy_date:
        buy_date = str(_date.today())
    h = add_holding(code, name, cost_price, shares, buy_date)
    return json.dumps({"status": "added", "id": h.id, "code": h.code, "name": h.name, "cost": h.cost_price, "shares": h.shares}, ensure_ascii=False)


@mcp.tool()
def mcp_remove_holding(id: int) -> str:
    """Remove a holding by ID.

    Args:
        id: Holding ID (get from mcp_list_holdings).
    """
    from hermes.portfolio.db import remove_holding
    ok = remove_holding(id)
    return json.dumps({"status": "removed" if ok else "not_found", "id": id}, ensure_ascii=False)


@mcp.tool()
def mcp_list_holdings() -> str:
    """List all portfolio holdings with id, code, name, cost, shares, buy_date."""
    from hermes.portfolio.db import list_holdings
    holdings = list_holdings()
    items = [{"id": h.id, "code": h.code, "name": h.name, "cost_price": h.cost_price, "shares": h.shares, "buy_date": h.buy_date} for h in holdings]
    return json.dumps({"count": len(items), "holdings": items}, ensure_ascii=False)


@mcp.tool()
def mcp_add_watch(code: str, name: str) -> str:
    """Add a stock to watchlist.

    Args:
        code: Stock code, e.g. '002352'.
        name: Stock name, e.g. '顺丰控股'.
    """
    from hermes.portfolio.db import add_watch
    w = add_watch(code, name)
    return json.dumps({"status": "added", "code": w.code, "name": w.name}, ensure_ascii=False)


@mcp.tool()
def mcp_remove_watch(code: str) -> str:
    """Remove a stock from watchlist.

    Args:
        code: Stock code to remove.
    """
    from hermes.portfolio.db import remove_watch
    ok = remove_watch(code)
    return json.dumps({"status": "removed" if ok else "not_found", "code": code}, ensure_ascii=False)


@mcp.tool()
def mcp_list_watchlist() -> str:
    """List all watchlist entries."""
    from hermes.portfolio.db import list_watchlist
    items = list_watchlist()
    entries = [{"code": w.code, "name": w.name} for w in items]
    return json.dumps({"count": len(entries), "watchlist": entries}, ensure_ascii=False)


@mcp.tool()
def mcp_list_triggers(code: str = "") -> str:
    """List active trigger conditions. Optionally filter by stock code.

    Args:
        code: Stock code to filter (empty = all triggers).
    """
    from hermes.portfolio.db import list_triggers
    triggers = list_triggers(code)
    items = [{"id": t.id, "code": t.code, "name": t.name, "type": t.type, "value": t.value, "description": t.description, "source": t.source} for t in triggers]
    return json.dumps({"count": len(items), "triggers": items}, ensure_ascii=False)


@mcp.tool()
def mcp_get_report(code: str) -> str:
    """Get the latest evaluation report for a stock.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.portfolio.db import get_report
    r = get_report(code)
    if not r:
        return json.dumps({"error": f"No report found for {code}"}, ensure_ascii=False)
    return json.dumps({"code": r.code, "score": r.score, "created_at": r.created_at, "content": r.content}, ensure_ascii=False)


# ── Evaluation & screening tools ──

@mcp.tool()
def mcp_screen(industry: str = "", pe_max: float = 0, pe_min: float = 0,
               pb_max: float = 0, pb_min: float = 0,
               cap_min: float = 0, cap_max: float = 0,
               turnover_min: float = 0,
               profit_yoy_min: float = 0, revenue_yoy_min: float = 0,
               limit: int = 20, watch: bool = False) -> str:
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
        watch: Auto-add screened stocks to watchlist (default false).
    """
    from hermes.api.eastmoney import em_get
    from hermes.portfolio.db import add_watch

    stocks = []
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
                revenue_yoy_pct = item.get("f170", "-")
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
    stocks = stocks[:limit]

    if watch and stocks:
        for s in stocks:
            add_watch(s["code"], s["name"])

    return json.dumps({"count": len(stocks), "stocks": stocks}, ensure_ascii=False)


@mcp.tool()
def mcp_evaluate(code: str) -> str:
    """Run full evaluation on a stock. Returns signal, score, report, triggers.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.strategy.eval import analyze, get_triggers
    from hermes.portfolio.models import TriggerCondition
    from hermes.portfolio.db import save_report, save_triggers

    analysis = analyze(code)
    signal = analysis.get("signal", "hold")
    report_text = analysis.get("report", "")
    score = analysis.get("score", 0)

    # Save report
    save_report(code, report_text, score)

    # Save triggers
    triggers_raw = get_triggers(code, analysis)
    trigger_models = [TriggerCondition(**t) for t in triggers_raw]
    save_triggers(trigger_models)

    return json.dumps({
        "code": code,
        "signal": signal,
        "score": score,
        "report_length": len(report_text),
        "triggers_count": len(triggers_raw),
        "report": report_text,
    }, ensure_ascii=False)


@mcp.tool()
def mcp_export_report(code: str) -> str:
    """Export evaluation report as markdown file to .hermes/reports/.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.portfolio.db import get_report
    from hermes.config import get_reports_dir
    from hermes.data.quote import stock_quote
    from datetime import date

    r = get_report(code)
    if not r:
        return json.dumps({"error": f"No report found for {code}"}, ensure_ascii=False)

    q = stock_quote(code)
    name = q.get("name", code) if "error" not in q else code
    filename = f"{code}_{name}_{date.today().strftime('%Y%m%d')}.md"
    reports_dir = get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    filepath = reports_dir / filename
    filepath.write_text(r.content, encoding="utf-8")

    return json.dumps({"status": "exported", "path": str(filepath)}, ensure_ascii=False)


# ── Portfolio analysis tools ──

@mcp.tool()
def mcp_portfolio_concentration() -> str:
    """Show portfolio industry concentration analysis. Warns if any industry >30%."""
    from hermes.portfolio.db import list_holdings
    from hermes.data.quote import stock_quote

    holdings = list_holdings()
    if not holdings:
        return json.dumps({"error": "No holdings"}, ensure_ascii=False)

    ind_map = {}
    for h in holdings:
        q = stock_quote(h.code)
        ind = q.get("industry", "未知") if "error" not in q else "未知"
        mv = q.get("price", 0) * h.shares if "error" not in q else 0
        ind_map.setdefault(ind, []).append({"code": h.code, "name": h.name, "mv": mv})

    total_mv = sum(item["mv"] for items in ind_map.values() for item in items)
    result = []
    for ind, items in ind_map.items():
        ind_mv = sum(i["mv"] for i in items)
        pct = round(ind_mv / total_mv * 100, 1) if total_mv > 0 else 0
        result.append({"industry": ind, "count": len(items), "market_value_wan": round(ind_mv / 10000, 2), "pct": pct, "stocks": [i["name"] for i in items]})

    result.sort(key=lambda x: x["pct"], reverse=True)
    warnings = [r for r in result if r["pct"] > 30]
    return json.dumps({"total_mv_wan": round(total_mv / 10000, 2), "industries": result, "warnings": warnings}, ensure_ascii=False)


@mcp.tool()
def mcp_portfolio_dividend() -> str:
    """Show dividend income summary for all holdings."""
    from hermes.portfolio.db import list_holdings
    from hermes.data.dividend import stock_dividend

    holdings = list_holdings()
    if not holdings:
        return json.dumps({"error": "No holdings"}, ensure_ascii=False)

    items = []
    total_dividend = 0.0
    for h in holdings:
        div = stock_dividend(h.code)
        if "error" in div:
            items.append({"code": h.code, "name": h.name, "shares": h.shares, "dps": None, "dividend_income": None, "yield_pct": None, "consecutive_years": None})
            continue
        dps = div.get("latest_dps") or 0
        div_income = round(dps * h.shares, 2)
        total_dividend += div_income
        items.append({
            "code": h.code, "name": h.name, "shares": h.shares,
            "dps": dps, "dividend_income": div_income,
            "yield_pct": div.get("dividend_yield"), "consecutive_years": div.get("consecutive_years"),
        })

    return json.dumps({"total_dividend_income": round(total_dividend, 2), "total_wan": round(total_dividend / 10000, 2), "items": items}, ensure_ascii=False)


@mcp.tool()
def mcp_portfolio_performance() -> str:
    """Show portfolio performance vs CSI 300 benchmark."""
    from hermes.portfolio.db import list_holdings
    from hermes.data.quote import stock_quote
    from hermes.data.kline import stock_kline

    holdings = list_holdings()
    if not holdings:
        return json.dumps({"error": "No holdings"}, ensure_ascii=False)

    bench_kline = stock_kline("000300")
    items = []
    total_pnl_pct = 0.0
    total_bench_pct = 0.0
    total_weight = 0.0

    for h in holdings:
        q = stock_quote(h.code)
        if "error" in q:
            items.append({"code": h.code, "name": h.name, "buy_date": h.buy_date, "cost": h.cost_price, "price": None, "pnl_pct": None, "bench_pct": None, "excess": None})
            continue
        current_price = q.get("price", 0)
        holding_pnl = round((current_price - h.cost_price) / h.cost_price * 100, 2) if h.cost_price > 0 else 0

        bench_return = 0.0
        if bench_kline and "error" not in bench_kline:
            klines = bench_kline.get("klines", [])
            buy_idx = None
            for i, k in enumerate(klines):
                if k.get("date", "") <= h.buy_date:
                    buy_idx = i
            latest_bench = klines[-1].get("close", 0) if klines else 0
            if buy_idx is not None and latest_bench > 0:
                bench_at_buy = klines[buy_idx].get("close", 0)
                if bench_at_buy > 0:
                    bench_return = round((latest_bench - bench_at_buy) / bench_at_buy * 100, 2)

        excess = round(holding_pnl - bench_return, 2)
        weight = h.cost_price * h.shares
        total_pnl_pct += holding_pnl * weight
        total_bench_pct += bench_return * weight
        total_weight += weight

        items.append({"code": h.code, "name": h.name, "buy_date": h.buy_date, "cost": h.cost_price, "price": current_price, "pnl_pct": holding_pnl, "bench_pct": bench_return, "excess": excess})

    weighted_pnl = round(total_pnl_pct / total_weight, 2) if total_weight > 0 else 0
    weighted_bench = round(total_bench_pct / total_weight, 2) if total_weight > 0 else 0
    weighted_excess = round(weighted_pnl - weighted_bench, 2)

    return json.dumps({"items": items, "weighted_pnl_pct": weighted_pnl, "weighted_bench_pct": weighted_bench, "weighted_excess_pct": weighted_excess}, ensure_ascii=False)


@mcp.tool()
def mcp_portfolio_log(code: str = "", limit: int = 30) -> str:
    """Show transaction log (buy/sell history).

    Args:
        code: Stock code filter (empty = all).
        limit: Number of entries (default 30).
    """
    from hermes.portfolio.db import list_transactions

    txns = list_transactions(code, limit)
    items = [{"id": t.id, "code": t.code, "name": t.name, "action": t.action, "price": t.price, "shares": t.shares, "amount": t.amount, "note": t.note, "date": t.created_at[:10] if t.created_at else ""} for t in txns]

    return json.dumps({"count": len(items), "transactions": items}, ensure_ascii=False)


@mcp.tool()
def mcp_patrol() -> str:
    """Run automated patrol: check all holdings/watchlist against trigger conditions."""
    from hermes.portfolio.db import list_holdings, list_watchlist, list_triggers
    from hermes.data.quote import stock_quote

    holdings = list_holdings()
    watchlist = list_watchlist()
    all_codes = [(h.code, h.name) for h in holdings] + [(w.code, w.name) for w in watchlist]

    if not all_codes:
        return json.dumps({"error": "No holdings or watchlist"}, ensure_ascii=False)

    alerts = []
    for code, name in all_codes:
        q = stock_quote(code)
        if "error" in q:
            continue
        current_price = q.get("price", 0)
        triggers = list_triggers(code)

        for t in triggers:
            if t.type == "price_stop_loss" and current_price <= t.value:
                alerts.append({"code": code, "name": name, "type": "止损", "threshold": t.value, "current": current_price})
            elif t.type == "price_stop_profit" and current_price >= t.value:
                alerts.append({"code": code, "name": name, "type": "止盈", "threshold": t.value, "current": current_price})
            elif t.type == "price_stop_loss_adaptive" and current_price <= t.value:
                alerts.append({"code": code, "name": name, "type": "动态止损", "threshold": t.value, "current": current_price})
            elif t.type == "price_stop_profit_adaptive" and current_price >= t.value:
                alerts.append({"code": code, "name": name, "type": "动态止盈", "threshold": t.value, "current": current_price})
            elif t.type == "near_52w_low" and current_price <= t.value:
                alerts.append({"code": code, "name": name, "type": "接近52周低点", "threshold": t.value, "current": current_price})
            elif t.type == "pe_high":
                pe = q.get("pe_dynamic")
                if pe and pe >= t.value:
                    alerts.append({"code": code, "name": name, "type": "PE预警", "threshold": t.value, "current": pe})

    return json.dumps({"checked": len(all_codes), "alerts": alerts, "alert_count": len(alerts)}, ensure_ascii=False)


@mcp.tool()
def mcp_config_show() -> str:
    """Show current Hermes configuration (factor weights, reports dir, etc)."""
    from hermes.config import load_config

    cfg = load_config()
    return json.dumps(cfg, ensure_ascii=False)


@mcp.tool()
def mcp_config_set(key: str, value: str) -> str:
    """Set a configuration value. Use dot notation for nested keys.

    Args:
        key: Config key, e.g. 'factor_weights.value' or 'push2_cooldown'.
        value: Config value (auto-converted to number if possible).
    """
    from hermes.config import load_config, save_config

    cfg = load_config()
    keys = key.split(".")
    target = cfg
    for k in keys[:-1]:
        if k not in target or not isinstance(target[k], dict):
            return json.dumps({"error": f"Path {key} does not exist"}, ensure_ascii=False)
        target = target[k]

    try:
        parsed = float(value)
        if parsed == int(parsed):
            parsed = int(parsed)
    except ValueError:
        parsed = value

    target[keys[-1]] = parsed
    save_config(cfg)
    return json.dumps({"status": "set", "key": key, "value": parsed}, ensure_ascii=False)


@mcp.tool()
def mcp_corporate_events(code: str) -> str:
    """Get upcoming corporate events for a stock (earnings dates, dividend schedule).

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.events import corporate_events

    result = corporate_events(code)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()