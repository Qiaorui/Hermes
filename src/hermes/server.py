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

    Args:
        url: The URL to fetch.
        keywords: Optional list of keywords to filter relevant text snippets.
        max_length: Maximum total text length to return (default 5000).
    """
    result = fetch_page(url, keywords, max_length)
    return json.dumps(result, ensure_ascii=False)


# Stock data tools — wrap dict-returning functions with json.dumps

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


@mcp.tool()
def mcp_industry_benchmarks(industry: str = "") -> str:
    """Get industry median benchmarks (PE, PB, profit YoY, revenue YoY).
    Used for industry-neutralized factor scoring.

    Args:
        industry: Optional industry name to filter (empty = all industries).
    """
    from hermes.data.industry import get_industry_benchmarks
    bench = get_industry_benchmarks()
    if industry:
        # Direct + partial match
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
        factors: Comma-separated factor names (empty = all). Options: value,growth,quality,momentum,volatility,liquidity.
    """
    from hermes.factors import factor_score, ALL_FACTORS
    names = [f.strip() for f in factors.split(",") if f.strip()] if factors else None
    result = factor_score(code, names)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def mcp_factor_composite(code: str, weights: str = "") -> str:
    """Compute composite multi-factor score with configurable weights. Returns total score and signal.

    Default weights: value=0.20, growth=0.20, quality=0.25, momentum=0.15, volatility=0.10, liquidity=0.10
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


if __name__ == "__main__":
    mcp.run()