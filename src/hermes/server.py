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

    Default weights: value=0.20, growth=0.20, quality=0.20, dividend=0.15, momentum=0.06, capital_flow=0.06, volatility=0.06, liquidity=0.07
    Signal: score>=7→buy, >=5→hold, >=3→watch, <3→sell

    Args:
        code: Stock code, e.g. '002352'.
        weights: Optional JSON dict of factor weights, e.g. '{"value":0.3,"growth":0.2,"quality":0.3}'.
    """
    from hermes.factors.composite import composite_factor, DEFAULT_WEIGHTS
    import json as _json
    if weights:
        try:
            w = _json.loads(weights)
        except Exception:
            w = DEFAULT_WEIGHTS
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


if __name__ == "__main__":
    mcp.run()