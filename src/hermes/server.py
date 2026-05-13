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


def _to_json(obj) -> str:
    """Serialize to JSON, non-ASCII preserved."""
    return json.dumps(obj)


def _safe_call(func, *args, **kwargs):
    """Call a data function, catching exceptions and returning structured error dict."""
    try:
        result = func(*args, **kwargs)
        return result
    except Exception as e:
        code = args[0] if args else kwargs.get("code", "")
        return {"error": str(e), "code": code}

mcp = FastMCP("hermes")


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
        original = backend
        backend = "google"
    else:
        original = None
    max_results = min(max_results, 20)
    results = search_text(query, max_results, backend)
    if not results:
        return _to_json({"error": "No results found", "query": query})
    resp = {"query": query, "count": len(results), "results": results}
    if original:
        resp["backend_used"] = backend
        resp["note"] = f"Requested backend '{original}' is not available, using '{backend}'"
    return _to_json(resp)


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
        return _to_json({"error": "No news results found", "query": query})
    return _to_json({"query": query, "count": len(results), "results": results})


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
    return _to_json(result)


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
    return _to_json(result)


# ── Stock data tools ──

@mcp.tool()
def mcp_stock_quote(code: str) -> str:
    """Get real-time stock quote with valuation metrics.

    Args:
        code: Stock code, e.g. '002352' for Shenzhen, '603636' for Shanghai.
    """
    return _to_json(_safe_call(stock_quote, code))


@mcp.tool()
def mcp_stock_kline(code: str, days: int = 120) -> str:
    """Get daily K-line data (OHLCV + change%) for a stock.

    Args:
        code: Stock code, e.g. '002352'.
        days: Number of recent trading days (default 120, max 500).
    """
    days = min(days, 500)
    return _to_json(_safe_call(stock_kline, code, days))


@mcp.tool()
def mcp_stock_fund_flow(code: str, days: int = 30) -> str:
    """Get daily fund flow data (main force, small/medium/large/super large net inflow).

    Args:
        code: Stock code, e.g. '002352'.
        days: Number of recent days (default 30, max 120).
    """
    days = min(days, 120)
    return _to_json(_safe_call(stock_fund_flow, code, days))


@mcp.tool()
def mcp_stock_announcements(code: str, count: int = 20) -> str:
    """Get recent company announcements (type, date, title).

    Args:
        code: Stock code, e.g. '002352'.
        count: Number of recent announcements (default 20, max 50).
    """
    count = min(count, 50)
    return _to_json(_safe_call(stock_announcements, code, count))


@mcp.tool()
def mcp_stock_valuation_history(code: str) -> str:
    """Get historical PE/PB percentile for valuation context.

    Args:
        code: Stock code, e.g. '002352'.
    """
    return _to_json(_safe_call(stock_valuation_history, code))


@mcp.tool()
def mcp_stock_financial(code: str, report_type: str = "income", count: int = 4) -> str:
    """Get multi-period financial statement data (income/balance/cashflow).

    Args:
        code: Stock code, e.g. '002352'.
        report_type: Statement type - 'income', 'balance', or 'cashflow' (default 'income').
        count: Number of recent periods (default 4, max 8).
    """
    count = min(count, 8)
    return _to_json(_safe_call(stock_financial, code, report_type, count))


@mcp.tool()
def mcp_stock_shareholders(code: str, top_n: int = 10) -> str:
    """Get top shareholders and top tradable shareholders.

    Args:
        code: Stock code, e.g. '002352' for Shenzhen, '603636' for Shanghai.
        top_n: Number of top shareholders per list (default 10, max 10).
    """
    return _to_json(_safe_call(stock_shareholders, code, top_n))


@mcp.tool()
def mcp_stock_unlock_schedule(code: str) -> str:
    """Get upcoming restricted share unlock schedule.

    Args:
        code: Stock code, e.g. '002352'.
    """
    return _to_json(_safe_call(stock_unlock_schedule, code))


@mcp.tool()
def mcp_market_index(days: int = 60) -> str:
    """Get recent market index data (Shanghai Composite + Shenzhen Component).

    Args:
        days: Number of recent trading days (default 60, max 500).
    """
    days = min(days, 500)
    return _to_json(_safe_call(market_index, days))


@mcp.tool()
def mcp_stock_dividend(code: str) -> str:
    """Get dividend history for a stock (dividend per share, yield, payout ratio, consistency).

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.dividend import stock_dividend
    return _to_json(_safe_call(stock_dividend, code))


@mcp.tool()
def mcp_industry_chain(code: str) -> str:
    """Get industry chain analysis — supply chain positioning, peer companies, competitive landscape.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.industry_chain import industry_chain
    return _to_json(_safe_call(industry_chain, code))


@mcp.tool()
def mcp_macro_indicators() -> str:
    """Get latest macro economic indicators (PMI, CPI, GDP, LPR, M2)."""
    from hermes.data.macro import macro_indicators
    return _to_json(_safe_call(macro_indicators))


@mcp.tool()
def mcp_stock_analyst(code: str) -> str:
    """Get analyst research data — research reports, profit forecasts, institutional participation.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.analyst import stock_analyst
    return _to_json(_safe_call(stock_analyst, code))


@mcp.tool()
def mcp_dragon_tiger(date: str = "") -> str:
    """Get dragon-tiger list (龙虎榜) — hot money activity for a trading day.

    Args:
        date: Trading date in YYYYMMDD format (empty = most recent available day).
    """
    from hermes.data.dragon_tiger import dragon_tiger_list
    return _to_json(_safe_call(dragon_tiger_list, date))


@mcp.tool()
def mcp_northbound_flow(days: int = 30) -> str:
    """Get daily northbound capital net flow (沪股通+深股通合计).

    Args:
        days: Number of recent days (default 30, max 120).
    """
    days = min(days, 120)
    from hermes.data.northbound import northbound_flow
    return _to_json(_safe_call(northbound_flow, days))


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
            return _to_json({"error": f"No match for '{industry}'", "available": list(bench.keys())[:20]})
        return _to_json(matched)
    return _to_json(bench)


@mcp.tool()
def mcp_factor_score(code: str, factors: str = "") -> str:
    """Compute quantitative factor scores for a stock. Returns 0-10 scores per factor.

    Args:
        code: Stock code, e.g. '002352'.
        factors: Comma-separated factor names (empty = all). Options: value,growth,quality,dividend,momentum,capital_flow,volatility,liquidity.
    """
    from hermes.factors import factor_score
    names = [f.strip() for f in factors.split(",") if f.strip()] if factors else None
    result = factor_score(code, names)
    return _to_json(result)


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
    if weights:
        try:
            w = json.loads(weights)
        except Exception:
            w = None
    else:
        w = None
    result = composite_factor(code, w)
    return _to_json(result)


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
    return _to_json({"status": "saved", "code": result.code, "score": result.score})


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
    try:
        triggers = json.loads(triggers_json)
    except Exception:
        return _to_json({"error": "Invalid triggers_json", "code": code})

    models = [TriggerCondition(code=code, name=name, type=t.get("type", ""), value=t.get("value", 0), description=t.get("description", "")) for t in triggers]
    save_triggers(models)
    return _to_json({"status": "saved", "code": code, "count": len(models)})


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
    return _to_json({"status": "added", "id": h.id, "code": h.code, "name": h.name, "cost": h.cost_price, "shares": h.shares})


@mcp.tool()
def mcp_remove_holding(id: int) -> str:
    """Remove a holding by ID.

    Args:
        id: Holding ID (get from mcp_list_holdings).
    """
    from hermes.portfolio.db import remove_holding
    ok = remove_holding(id)
    return _to_json({"status": "removed" if ok else "not_found", "id": id})


@mcp.tool()
def mcp_list_holdings() -> str:
    """List all portfolio holdings with id, code, name, cost, shares, buy_date."""
    from hermes.portfolio.db import list_holdings
    holdings = list_holdings()
    items = [{"id": h.id, "code": h.code, "name": h.name, "cost_price": h.cost_price, "shares": h.shares, "buy_date": h.buy_date} for h in holdings]
    return _to_json({"count": len(items), "holdings": items})


@mcp.tool()
def mcp_add_watch(code: str, name: str) -> str:
    """Add a stock to watchlist.

    Args:
        code: Stock code, e.g. '002352'.
        name: Stock name, e.g. '顺丰控股'.
    """
    from hermes.portfolio.db import add_watch
    w = add_watch(code, name)
    return _to_json({"status": "added", "code": w.code, "name": w.name})


@mcp.tool()
def mcp_remove_watch(code: str) -> str:
    """Remove a stock from watchlist.

    Args:
        code: Stock code to remove.
    """
    from hermes.portfolio.db import remove_watch
    ok = remove_watch(code)
    return _to_json({"status": "removed" if ok else "not_found", "code": code})


@mcp.tool()
def mcp_list_watchlist() -> str:
    """List all watchlist entries."""
    from hermes.portfolio.db import list_watchlist
    items = list_watchlist()
    entries = [{"code": w.code, "name": w.name} for w in items]
    return _to_json({"count": len(entries), "watchlist": entries})


@mcp.tool()
def mcp_list_triggers(code: str = "") -> str:
    """List active trigger conditions. Optionally filter by stock code.

    Args:
        code: Stock code to filter (empty = all triggers).
    """
    from hermes.portfolio.db import list_triggers
    triggers = list_triggers(code)
    items = [{"id": t.id, "code": t.code, "name": t.name, "type": t.type, "value": t.value, "description": t.description, "source": t.source} for t in triggers]
    return _to_json({"count": len(items), "triggers": items})


@mcp.tool()
def mcp_get_report(code: str) -> str:
    """Get the latest evaluation report for a stock.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.portfolio.db import get_report
    r = get_report(code)
    if not r:
        return _to_json({"error": f"No report found for {code}"})
    return _to_json({"code": r.code, "score": r.score, "created_at": r.created_at, "content": r.content})


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
    from hermes.data.screen import screen_stocks
    from hermes.portfolio.db import add_watch

    stocks = screen_stocks(
        industry=industry, pe_max=pe_max, pe_min=pe_min,
        pb_max=pb_max, pb_min=pb_min, cap_min=cap_min, cap_max=cap_max,
        turnover_min=turnover_min, profit_yoy_min=profit_yoy_min,
        revenue_yoy_min=revenue_yoy_min, limit=limit,
    )

    if watch and stocks:
        for s in stocks:
            add_watch(s["code"], s["name"])

    return _to_json({"count": len(stocks), "stocks": stocks})


@mcp.tool()
def mcp_evaluate(code: str) -> str:
    """Run full evaluation on a stock. Returns signal, score, report, triggers.

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.service.portfolio import evaluate_stock
    result = evaluate_stock(code)
    return _to_json(result)


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
        return _to_json({"error": f"No report found for {code}"})

    q = stock_quote(code)
    name = q.get("name", code) if "error" not in q else code
    filename = f"{code}_{name}_{date.today().strftime('%Y%m%d')}.md"
    reports_dir = get_reports_dir()
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        filepath = reports_dir / filename
        filepath.write_text(r.content, encoding="utf-8")
    except OSError as e:
        return _to_json({"error": f"Failed to write report file: {e}", "code": code})

    return _to_json({"status": "exported", "path": str(filepath)})


# ── Portfolio analysis tools ──

@mcp.tool()
def mcp_portfolio_concentration() -> str:
    """Show portfolio industry concentration analysis. Warns if any industry >30%."""
    from hermes.service.portfolio import portfolio_concentration_data
    result = portfolio_concentration_data()
    return _to_json(result)


@mcp.tool()
def mcp_portfolio_dividend() -> str:
    """Show dividend income summary for all holdings."""
    from hermes.service.portfolio import portfolio_dividend_data
    result = portfolio_dividend_data()
    return _to_json(result)


@mcp.tool()
def mcp_portfolio_performance() -> str:
    """Show portfolio performance vs CSI 300 benchmark."""
    from hermes.service.portfolio import portfolio_performance_data
    result = portfolio_performance_data()
    return _to_json(result)


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

    return _to_json({"count": len(items), "transactions": items})


@mcp.tool()
def mcp_patrol() -> str:
    """Run automated patrol: check all holdings/watchlist against trigger conditions."""
    from hermes.service.portfolio import patrol_data
    result = patrol_data()
    return _to_json(result)


@mcp.tool()
def mcp_config_show() -> str:
    """Show current Hermes configuration (factor weights, reports dir, etc)."""
    from hermes.config import load_config

    cfg = load_config()
    return _to_json(cfg)


@mcp.tool()
def mcp_config_set(key: str, value: str) -> str:
    """Set a configuration value. Use dot notation for nested keys.

    Args:
        key: Config key, e.g. 'factor_weights.value' or 'push2_cooldown'.
        value: Config value (auto-converted to number if possible).
    """
    from hermes.config import load_config, save_config, set_nested_config

    cfg = load_config()
    try:
        cfg, parsed = set_nested_config(cfg, key, value)
    except ValueError as e:
        return _to_json({"error": str(e)})
    save_config(cfg)
    return _to_json({"status": "set", "key": key, "value": parsed})


@mcp.tool()
def mcp_corporate_events(code: str) -> str:
    """Get upcoming corporate events for a stock (earnings dates, dividend schedule).

    Args:
        code: Stock code, e.g. '002352'.
    """
    from hermes.data.events import corporate_events

    result = corporate_events(code)
    return _to_json(result)


if __name__ == "__main__":
    mcp.run()