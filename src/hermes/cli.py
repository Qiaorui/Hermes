"""Hermes CLI — stock analysis, screening, and portfolio tracking."""

import typer
import json
from datetime import date
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from hermes.strategy.eval import analyze, get_triggers
from hermes.factors import factor_score, ALL_FACTORS
from hermes.factors.composite import composite_factor
from hermes.portfolio.db import (
    add_holding, remove_holding, list_holdings, update_holding, get_holding,
    add_watch, remove_watch, list_watchlist,
    add_trigger, remove_trigger, list_triggers, save_triggers,
    save_report, get_report,
    add_transaction, list_transactions,
)
from hermes.portfolio.models import TriggerCondition
from hermes.data.quote import stock_quote
from hermes.data.market import market_index
from hermes.notify.cli_notifier import notify, notify_trigger

console = Console(force_terminal=True)

app = typer.Typer(help="Hermes — A-stock analysis and portfolio tracking")
portfolio_app = typer.Typer(help="Portfolio management")
trigger_app = typer.Typer(help="Trigger conditions management")


@app.command()
def dashboard():
    """Show portfolio dashboard with visual P&L, market index, and holdings overview."""
    holdings = list_holdings()
    watchlist = list_watchlist()

    total_cost = 0.0
    total_value = 0.0

    # ─── Header: Summary ───
    for h in holdings:
        q = stock_quote(h.code)
        if "error" not in q:
            total_cost += h.cost_price * h.shares
            total_value += q.get("price", 0) * h.shares

    total_pnl = round(total_value - total_cost, 2)
    total_pnl_pct = round(total_pnl / total_cost * 100, 2) if total_cost > 0 else 0
    pnl_color = "green" if total_pnl >= 0 else "red"
    sign = "+" if total_pnl >= 0 else ""

    header = Text()
    header.append(" Hermes Portfolio ", style="bold white on blue")
    header.append(f"  总市值 {round(total_value/10000, 2)}万  总成本 {round(total_cost/10000, 2)}万  ", style="bold")
    header.append(f"总盈亏 {sign}{total_pnl_pct}% ({sign}{round(total_pnl/10000, 2)}万)", style=f"bold {pnl_color}")
    console.print(Panel(header, border_style="blue"))

    # ─── Holdings Table ───
    h_table = Table(title="持仓", show_lines=True, title_style="bold cyan", expand=True)
    h_table.add_column("ID", style="dim", min_width=3)
    h_table.add_column("代码", style="cyan", min_width=8)
    h_table.add_column("名称", min_width=10)
    h_table.add_column("现价", justify="right", min_width=8)
    h_table.add_column("成本", justify="right", min_width=8)
    h_table.add_column("数量", justify="right", min_width=7)
    h_table.add_column("盈亏%", justify="right", min_width=9)
    h_table.add_column("信号", justify="center", min_width=6)
    h_table.add_column("市值(万)", justify="right", min_width=10)
    h_table.add_column("行业", min_width=10)

    # Cache factor results to avoid repeated API calls per stock
    factor_cache: dict[str, dict] = {}
    for h in holdings:
        if h.code not in factor_cache:
            try:
                factor_cache[h.code] = composite_factor(h.code)
            except Exception:
                factor_cache[h.code] = {}

    for h in holdings:
        q = stock_quote(h.code)
        if "error" in q:
            h_table.add_row(str(h.id), h.code, h.name, "-", str(h.cost_price), str(h.shares), "-", "-", "-", "")
            continue
        price = q.get("price", 0)
        pnl_pct = round((price - h.cost_price) / h.cost_price * 100, 2) if h.cost_price > 0 else 0
        mv = round(price * h.shares / 10000, 2)
        c = "green" if pnl_pct >= 0 else "red"
        s = "+" if pnl_pct >= 0 else ""
        arrow = "▲" if pnl_pct >= 0 else "▼"

        # Factor signal
        fc = factor_cache.get(h.code, {})
        if fc and "error" not in fc:
            sig = fc.get("signal", "hold")
            sc = fc.get("score", 0)
            sig_icon = {"buy": "▲", "hold": "●", "watch": "◆", "sell": "▼"}.get(sig, "?")
            sig_color = {"buy": "green", "hold": "cyan", "watch": "yellow", "sell": "red"}.get(sig, "white")
            signal_text = Text(f"{sig_icon}{sc}", style=sig_color)
        else:
            signal_text = Text("-", style="dim")

        h_table.add_row(
            str(h.id), h.code, h.name, str(price), str(h.cost_price), str(h.shares),
            Text(f"{arrow}{s}{pnl_pct}%", style=c), signal_text, str(mv),
            q.get("industry", ""),
        )

    console.print(h_table)

    # ─── Market Index ───
    from hermes.data.market import INDICES
    idx = market_index(30)
    m_table = Table(title="大盘", title_style="bold yellow", show_lines=False)
    m_table.add_column("指数", min_width=10)
    m_table.add_column("收盘", justify="right", min_width=10)
    m_table.add_column("涨跌%", justify="right", min_width=8)

    for key, (symbol, label) in INDICES.items():
        data = idx.get(key)
        if data:
            chg = data.get("latest_change_pct")
            c = "green" if chg and chg >= 0 else "red"
            m_table.add_row(label, str(data["latest_close"]), Text(f"{chg:+}" if chg else "-", style=c))

    console.print(Panel(m_table, border_style="yellow"))

    # ─── Watchlist ───
    w_table = Table(title="关注", title_style="bold magenta", show_lines=False)
    w_table.add_column("代码", style="cyan", min_width=8)
    w_table.add_column("名称", min_width=10)
    w_table.add_column("现价", justify="right", min_width=8)
    w_table.add_column("PE", justify="right", min_width=8)
    w_table.add_column("净利同比%", justify="right", min_width=10)

    for w in watchlist:
        q = stock_quote(w.code)
        if "error" not in q:
            w_table.add_row(w.code, w.name, str(q.get("price", "-")), str(q.get("pe_dynamic", "-")), str(q.get("profit_yoy", "-")))
        else:
            w_table.add_row(w.code, w.name, "-", "-", "-")

    console.print(Panel(w_table, border_style="magenta"))

    # ─── Triggers ───
    all_triggers = list_triggers()
    t_text = Text()
    if all_triggers:
        t_text.append(f"活跃触发条件: {len(all_triggers)} 条\n", style="bold")
        for t in all_triggers:
            icon = {"price_stop_loss": "▼", "price_stop_profit": "▲", "pe_high": "⚠", "near_52w_low": "◆"}.get(t.type, "?")
            t_text.append(f"  {icon} [{t.code} {t.name}] {t.description}\n")
    else:
        t_text.append("  无触发条件", style="dim")
    console.print(Panel(t_text, title="触发条件", border_style="red"))
app.add_typer(portfolio_app, name="portfolio")
app.add_typer(trigger_app, name="trigger")


@app.command()
def patrol():
    """Automated patrol: check all holdings/watchlist against triggers. Designed for cron use."""
    portfolio_check()


@app.command()
def evaluate(code: str):
    """Evaluate a single stock. Runs full analysis, saves report and triggers."""
    typer.echo(f"正在评估 {code}...")
    analysis = analyze(code)
    signal = analysis.get("signal", "hold")
    report = analysis.get("report", "")
    data = analysis.get("data", {})

    # Get stock name
    quote = data.get("quote", {})
    name = quote.get("name", code)

    # Save report
    save_report(code, report, analysis.get("score", 0))

    # Generate and save triggers
    triggers_raw = get_triggers(code, analysis)
    trigger_models = [TriggerCondition(**t) for t in triggers_raw]
    save_triggers(trigger_models)

    # Print full report with Rich
    console.print(Panel(report, title=f"{name}（{code}）评估报告", border_style="cyan"))

    # Signal summary
    signal_icon = {"buy": "▲", "hold": "●", "watch": "◆", "sell": "▼"}.get(signal, "?")
    signal_color = {"buy": "green", "hold": "cyan", "watch": "yellow", "sell": "red"}.get(signal, "white")
    console.print(Panel(
        Text(f"{signal_icon} 信号: {signal.upper()} | 评分: {analysis.get('score', 0)}/50", style=f"bold {signal_color}"),
        title="综合信号", border_style=signal_color,
    ))

    # Triggers
    if triggers_raw:
        t_table = Table(title="触发条件", show_lines=False, title_style="bold red")
        t_table.add_column("类型", min_width=15)
        t_table.add_column("阈值", justify="right", min_width=10)
        t_table.add_column("描述", min_width=30)
        for t in triggers_raw:
            t_table.add_row(t["type"], str(t["value"]), t["description"])
        console.print(t_table)


@app.command()
def screen(
    industry: str = typer.Option("", "--industry", "-i", help="行业筛选"),
    pe_max: float = typer.Option(0, "--pe-max", help="PE上限（0=不限）"),
    pe_min: float = typer.Option(0, "--pe-min", help="PE下限（0=不限）"),
    pb_max: float = typer.Option(0, "--pb-max", help="PB上限（0=不限）"),
    pb_min: float = typer.Option(0, "--pb-min", help="PB下限（0=不限）"),
    market_cap_min: float = typer.Option(0, "--cap-min", help="市值下限(亿元, 0=不限)"),
    market_cap_max: float = typer.Option(0, "--cap-max", help="市值上限(亿元, 0=不限)"),
    turnover_min: float = typer.Option(0, "--turnover-min", help="换手率下限%(0=不限)"),
    profit_yoy_min: float = typer.Option(0, "--profit-yoy-min", help="净利润同比增长下限%"),
    revenue_yoy_min: float = typer.Option(0, "--revenue-yoy-min", help="营收同比增长下限%"),
    limit: int = typer.Option(20, "--limit", "-l", help="返回数量上限"),
    watch: bool = typer.Option(False, "--watch", "-w", help="自动添加筛选结果到关注列表"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON格式输出"),
):
    """Screen stocks by criteria. Returns filtered ranked list."""
    from hermes.api.eastmoney import em_get, parse_secid

    # Fetch A-share stock list (add f55 for turnover_rate)
    stocks = []
    for fs in ["m:1+t:2,m:0+t:6,m:0+t:80,m:1+t:23"]:
        url = f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit*3}&po=1&np=1&fltt=2&invt=2&fs={fs}&fields=f2,f3,f12,f14,f9,f20,f23,f55,f115,f169,f170,f100"
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

                # PB filter
                if pb_max > 0 or pb_min > 0:
                    try:
                        pb_val = float(pb)
                        if pb_max > 0 and pb_val > pb_max:
                            continue
                        if pb_min > 0 and pb_val < pb_min:
                            continue
                    except (ValueError, TypeError):
                        continue

                # Market cap filter (in 亿元)
                if market_cap_min > 0 or market_cap_max > 0:
                    try:
                        cap_yi = float(market_cap) / 1e8
                        if market_cap_min > 0 and cap_yi < market_cap_min:
                            continue
                        if market_cap_max > 0 and cap_yi > market_cap_max:
                            continue
                    except (ValueError, TypeError):
                        continue

                # Turnover rate filter
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

    if not stocks:
        typer.echo("未找到符合条件的股票")
        return

    # JSON output
    if json_output:
        typer.echo(json.dumps({"count": len(stocks), "stocks": stocks}, ensure_ascii=False))
        if watch:
            for s in stocks:
                add_watch(s["code"], s["name"])
        return

    # Rich Table output
    s_table = Table(title=f"筛选结果（共 {len(stocks)} 只）", show_lines=False, title_style="bold cyan", expand=True)
    s_table.add_column("代码", style="cyan", min_width=8)
    s_table.add_column("名称", min_width=10)
    s_table.add_column("价格", justify="right", min_width=8)
    s_table.add_column("涨跌%", justify="right", min_width=7)
    s_table.add_column("PE", justify="right", min_width=8)
    s_table.add_column("PB", justify="right", min_width=6)
    s_table.add_column("市值(亿)", justify="right", min_width=9)
    s_table.add_column("换手%", justify="right", min_width=6)
    s_table.add_column("净利同比%", justify="right", min_width=10)
    s_table.add_column("行业", min_width=10)

    for s in stocks:
        chg = s["change_pct"]
        try:
            chg_color = "green" if float(chg) >= 0 else "red"
        except (ValueError, TypeError):
            chg_color = "white"
        s_table.add_row(
            s["code"], s["name"], str(s["price"]),
            Text(str(chg), style=chg_color), str(s["pe"]),
            str(s["pb"]), str(s["market_cap_yi"]),
            str(s["turnover_rate"]),
            str(s["profit_yoy_pct"]), s["industry"],
        )

    console.print(s_table)

    # Auto-add to watchlist
    if watch:
        added = 0
        for s in stocks:
            w = add_watch(s["code"], s["name"])
            added += 1
        typer.echo(f"已添加 {added} 只股票到关注列表")


@app.command()
def factor(
    code: str,
    names: str = typer.Option("", "--factors", "-f", help="因子列表(逗号分隔,空=全部): value,growth,quality,dividend,momentum,capital_flow,volatility,liquidity"),
    composite: bool = typer.Option(False, "--composite", "-c", help="同时输出综合因子评分"),
):
    """Compute quantitative factor scores for a stock."""
    factor_names = [f.strip() for f in names.split(",") if f.strip()] if names else None
    result = factor_score(code, factor_names)

    if not result.get("factors"):
        typer.echo(f"无法计算 {code} 的因子得分")
        return

    q = stock_quote(code)
    stock_name = q.get("name", code) if "error" not in q else code

    f_table = Table(title=f"因子评分 — {stock_name}({code})", show_lines=False, title_style="bold cyan")
    f_table.add_column("因子", min_width=12)
    f_table.add_column("得分", justify="right", min_width=6)
    f_table.add_column("评级", justify="center", min_width=6)

    for fname, fdata in result["factors"].items():
        score = fdata.get("score")
        coverage = fdata.get("coverage_pct", 100)
        if score is None:
            f_table.add_row(fname, Text("N/A", style="dim"), Text("数据缺失", style="dim"))
            continue
        rating = "优秀" if score >= 7 else ("良好" if score >= 5 else ("一般" if score >= 3 else "较差"))
        color = "green" if score >= 7 else ("cyan" if score >= 5 else ("yellow" if score >= 3 else "red"))
        cov_color = "green" if coverage == 100 else ("yellow" if coverage >= 67 else "red")
        f_table.add_row(fname, Text(str(score), style=color), Text(f"{rating} ({coverage:.0f}%)", style=f"{color} {cov_color}"))

    console.print(f_table)

    # Print key sub-factor details + unavailable warnings
    for fname, fdata in result["factors"].items():
        details = fdata.get("details", {})
        unavail = details.get("unavailable", [])
        key_items = [f"{k}={v}" for k, v in details.items() if v is not None and not k.endswith("_score") and k != "unavailable"]
        if key_items:
            typer.echo(f"  {fname}: {', '.join(key_items)}")
        if unavail:
            for u in unavail:
                typer.echo(f"    ⚠ {u['sub_factor']}: {u['reason']}")

    if composite:
        comp = composite_factor(code)
        if "error" not in comp:
            score = comp["score"]
            signal = comp["signal"]
            signal_icon = {"buy": "▲", "hold": "●", "watch": "◆", "sell": "▼"}.get(signal, "?")
            signal_color = {"buy": "green", "hold": "cyan", "watch": "yellow", "sell": "red"}.get(signal, "white")
            text = f"综合评分: {score}/10  信号: {signal_icon} {signal.upper()}"
            partial = comp.get("partial_factors", [])
            if partial:
                text += "\n⚠ 数据覆盖不完整:"
                for pf in partial:
                    text += f"\n  {pf['factor']}: 仅{pf['coverage_pct']}%因子可用"
            console.print(Panel(
                Text(text, style=f"bold {signal_color}"),
                title="综合因子", border_style=signal_color,
            ))


@app.command()
def report(
    code: str,
    output: str = typer.Option("", "--output", "-o", help="导出格式: md"),
):
    """View the latest evaluation report for a stock. Use --output md to export."""
    r = get_report(code)
    if not r:
        typer.echo(f"未找到 {code} 的评估报告。请先运行: hermes evaluate {code}")
        return

    if output == "md":
        from hermes.config import get_reports_dir
        from hermes.data.quote import stock_quote as _sq
        q = _sq(code)
        name = q.get("name", code) if "error" not in q else code
        filename = f"{code}_{name}_{date.today().strftime('%Y%m%d')}.md"
        reports_dir = get_reports_dir()
        reports_dir.mkdir(parents=True, exist_ok=True)
        filepath = reports_dir / filename
        filepath.write_text(r.content, encoding="utf-8")
        typer.echo(f"报告已导出: {filepath}")
    else:
        typer.echo(r.content)


# ─── Portfolio commands ───

@portfolio_app.command("add")
def portfolio_add(
    code: str,
    cost: float = typer.Option(0.0, "--cost", "-c", help="买入均价"),
    shares: int = typer.Option(100, "--shares", "-s", help="持股数量"),
    buy_date: str = typer.Option("", "--date", "-d", help="买入日期（YYYY-MM-DD）"),
):
    """Add a stock to portfolio holdings."""
    if not buy_date:
        buy_date = str(date.today())

    # Get stock name from quote
    q = stock_quote(code)
    name = q.get("name", code) if "error" not in q else code

    h = add_holding(code, name, cost, shares, buy_date)
    add_transaction(code, name, "buy", cost, shares, f"买入 成本{cost}元 {shares}股")
    typer.echo(f"已添加持仓: {h.code} {h.name} 成本{h.cost_price}元 {h.shares}股 日期{h.buy_date}")


@portfolio_app.command("watch")
def portfolio_watch(code: str):
    """Add a stock to watchlist."""
    q = stock_quote(code)
    name = q.get("name", code) if "error" not in q else code

    w = add_watch(code, name)
    typer.echo(f"已添加关注: {w.code} {w.name}")


@portfolio_app.command("log")
def portfolio_log(
    code: str = typer.Option("", "--code", "-c", help="股票代码（空=全部）"),
    limit: int = typer.Option(30, "--limit", "-l", help="显示条数"),
):
    """Show transaction log (buy/sell history)."""
    txns = list_transactions(code, limit)
    if not txns:
        typer.echo("暂无交易记录")
        return

    t_table = Table(title="交易记录", show_lines=False, title_style="bold green", expand=True)
    t_table.add_column("ID", style="dim", min_width=3)
    t_table.add_column("日期", min_width=12)
    t_table.add_column("代码", style="cyan", min_width=8)
    t_table.add_column("名称", min_width=10)
    t_table.add_column("操作", justify="center", min_width=6)
    t_table.add_column("价格", justify="right", min_width=8)
    t_table.add_column("数量", justify="right", min_width=6)
    t_table.add_column("金额", justify="right", min_width=10)
    t_table.add_column("备注", min_width=20)

    for t in txns:
        action_color = "green" if t.action in ("buy", "add") else "red" if t.action in ("sell", "reduce") else "yellow"
        t_table.add_row(
            str(t.id), t.created_at[:10] if t.created_at else "", t.code, t.name,
            Text(t.action, style=action_color), str(t.price), str(t.shares),
            str(round(t.amount, 2)), t.note,
        )

    console.print(t_table)


@portfolio_app.command("performance")
def portfolio_performance():
    """Show portfolio performance vs benchmark (CSI 300)."""
    holdings = list_holdings()
    if not holdings:
        typer.echo("暂无持仓")
        return

    from hermes.data.kline import stock_kline

    p_table = Table(title="持仓收益 vs 基准", show_lines=False, title_style="bold cyan", expand=True)
    p_table.add_column("代码", style="cyan", min_width=8)
    p_table.add_column("名称", min_width=10)
    p_table.add_column("买入日", min_width=12)
    p_table.add_column("买入价", justify="right", min_width=8)
    p_table.add_column("现价", justify="right", min_width=8)
    p_table.add_column("持仓收益%", justify="right", min_width=10)
    p_table.add_column("同期基准%", justify="right", min_width=10)
    p_table.add_column("超额%", justify="right", min_width=10)

    # CSI 300 kline for benchmark
    bench_kline = stock_kline("000300")

    total_pnl_pct = 0.0
    total_bench_pct = 0.0
    total_weight = 0.0

    for h in holdings:
        q = stock_quote(h.code)
        if "error" in q:
            p_table.add_row(h.code, h.name, h.buy_date, str(h.cost_price), "-", "-", "-", "-")
            continue
        current_price = q.get("price", 0)
        holding_pnl = round((current_price - h.cost_price) / h.cost_price * 100, 2) if h.cost_price > 0 else 0

        # Find benchmark price at buy_date
        bench_return = 0.0
        if bench_kline and "error" not in bench_kline:
            klines = bench_kline.get("klines", [])
            buy_date_str = h.buy_date
            # Find closest kline date before buy_date
            buy_idx = None
            for i, k in enumerate(klines):
                if k.get("date", "") <= buy_date_str:
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

        c_h = "green" if holding_pnl >= 0 else "red"
        c_b = "green" if bench_return >= 0 else "red"
        c_e = "green" if excess >= 0 else "red"
        p_table.add_row(
            h.code, h.name, h.buy_date, str(h.cost_price), str(current_price),
            Text(f"{holding_pnl:+}%", style=c_h), Text(f"{bench_return:+}%", style=c_b), Text(f"{excess:+}%", style=c_e),
        )

    console.print(p_table)

    if total_weight > 0:
        weighted_pnl = round(total_pnl_pct / total_weight, 2)
        weighted_bench = round(total_bench_pct / total_weight, 2)
        weighted_excess = round(weighted_pnl - weighted_bench, 2)
        typer.echo(f"组合加权收益: {weighted_pnl:+}% | 基准收益: {weighted_bench:+}% | 超额收益: {weighted_excess:+}%")


@portfolio_app.command("dividend")
def portfolio_dividend():
    """Show dividend income summary for all holdings."""
    holdings = list_holdings()
    if not holdings:
        typer.echo("暂无持仓")
        return

    d_table = Table(title="分红收益汇总", show_lines=False, title_style="bold green", expand=True)
    d_table.add_column("代码", style="cyan", min_width=8)
    d_table.add_column("名称", min_width=10)
    d_table.add_column("持股", justify="right", min_width=6)
    d_table.add_column("最新DPS(元)", justify="right", min_width=10)
    d_table.add_column("分红收益(元)", justify="right", min_width=12)
    d_table.add_column("股息率%", justify="right", min_width=8)
    d_table.add_column("连续年份", justify="right", min_width=8)

    total_dividend = 0.0
    for h in holdings:
        from hermes.data.dividend import stock_dividend
        div = stock_dividend(h.code)
        if "error" in div:
            d_table.add_row(h.code, h.name, str(h.shares), "-", "-", "-", "-")
            continue
        dps = div.get("latest_dps") or 0
        div_income = round(dps * h.shares, 2)
        total_dividend += div_income
        yield_pct = div.get("dividend_yield") or 0
        consecutive = div.get("consecutive_years") or 0
        d_table.add_row(h.code, h.name, str(h.shares), str(dps), str(div_income), str(yield_pct), str(consecutive))

    console.print(d_table)
    typer.echo(f"预计年度分红收益合计: {round(total_dividend, 2)}元 ({round(total_dividend/10000, 2)}万)")


@portfolio_app.command("concentration")
def portfolio_concentration():
    """Show portfolio industry concentration analysis."""
    holdings = list_holdings()
    if not holdings:
        typer.echo("暂无持仓")
        return

    # Group by industry
    ind_map: dict[str, list] = {}
    for h in holdings:
        q = stock_quote(h.code)
        ind = q.get("industry", "未知") if "error" not in q else "未知"
        mv = q.get("price", 0) * h.shares if "error" not in q else 0
        ind_map.setdefault(ind, []).append({"code": h.code, "name": h.name, "mv": mv})

    total_mv = sum(item["mv"] for items in ind_map.values() for item in items)

    c_table = Table(title="行业集中度", show_lines=False, title_style="bold cyan", expand=True)
    c_table.add_column("行业", min_width=10)
    c_table.add_column("持仓数", justify="right", min_width=6)
    c_table.add_column("市值(万)", justify="right", min_width=10)
    c_table.add_column("占比%", justify="right", min_width=8)
    c_table.add_column("股票", min_width=20)

    # Sort by market value descending
    sorted_inds = sorted(ind_map.items(), key=lambda x: sum(i["mv"] for i in x[1]), reverse=True)

    for ind, items in sorted_inds:
        ind_mv = sum(i["mv"] for i in items)
        pct = round(ind_mv / total_mv * 100, 1) if total_mv > 0 else 0
        stocks_str = ", ".join(f"{i['name']}" for i in items)
        c_table.add_row(ind, str(len(items)), str(round(ind_mv / 10000, 2)), Text(f"{pct}%", style="bold" if pct > 30 else ""), stocks_str)

    console.print(c_table)

    # Warning if any industry > 30%
    for ind, items in sorted_inds:
        ind_mv = sum(i["mv"] for i in items)
        pct = round(ind_mv / total_mv * 100, 1) if total_mv > 0 else 0
        if pct > 30:
            typer.echo(f"⚠ 行业 '{ind}' 占比 {pct}%，超过30%阈值，建议分散配置")


@portfolio_app.command("unwatch")
def portfolio_unwatch(code: str):
    """Remove a stock from watchlist."""
    if remove_watch(code):
        typer.echo(f"已移除关注: {code}")
    else:
        typer.echo(f"关注列表中未找到 {code}")


@portfolio_app.command("list")
def portfolio_list():
    """List all holdings (with current price and P&L) and watchlist."""
    holdings = list_holdings()
    watchlist = list_watchlist()

    if holdings:
        h_table = Table(title="持仓", show_lines=False, title_style="bold cyan", expand=True)
        h_table.add_column("ID", style="dim", min_width=3)
        h_table.add_column("代码", style="cyan", min_width=8)
        h_table.add_column("名称", min_width=10)
        h_table.add_column("现价", justify="right", min_width=8)
        h_table.add_column("成本", justify="right", min_width=8)
        h_table.add_column("数量", justify="right", min_width=7)
        h_table.add_column("盈亏%", justify="right", min_width=9)
        h_table.add_column("市值(万)", justify="right", min_width=10)
        h_table.add_column("买入日期", min_width=12)

        for h in holdings:
            q = stock_quote(h.code)
            if "error" in q:
                h_table.add_row(str(h.id), h.code, h.name, "-", str(h.cost_price), str(h.shares), "-", "-", h.buy_date)
                continue
            price = q.get("price", 0)
            pnl_pct = round((price - h.cost_price) / h.cost_price * 100, 2) if h.cost_price > 0 else 0
            mv = round(price * h.shares / 10000, 2)
            c = "green" if pnl_pct >= 0 else "red"
            sign = "+" if pnl_pct >= 0 else ""
            arrow = "▲" if pnl_pct >= 0 else "▼"
            h_table.add_row(
                str(h.id), h.code, h.name, str(price), str(h.cost_price), str(h.shares),
                Text(f"{arrow}{sign}{pnl_pct}%", style=c), str(mv), h.buy_date,
            )

        console.print(h_table)

    if watchlist:
        w_table = Table(title="关注", show_lines=False, title_style="bold magenta")
        w_table.add_column("代码", style="cyan", min_width=8)
        w_table.add_column("名称", min_width=10)
        w_table.add_column("现价", justify="right", min_width=8)

        for w in watchlist:
            q = stock_quote(w.code)
            if "error" not in q:
                w_table.add_row(w.code, w.name, str(q.get("price", "-")))
            else:
                w_table.add_row(w.code, w.name, "-")

        console.print(w_table)

    if not holdings and not watchlist:
        typer.echo("暂无持仓和关注。使用 hermes portfolio add/watch 添加。")


@portfolio_app.command("update")
def portfolio_update(
    id: int,
    cost: float = typer.Option(None, "--cost", "-c", help="更新买入均价"),
    shares: int = typer.Option(None, "--shares", "-s", help="更新持股数量"),
    buy_date: str = typer.Option(None, "--date", "-d", help="更新买入日期（YYYY-MM-DD）"),
):
    """Update holding info by ID. Only updates specified fields."""
    h = update_holding(id, cost_price=cost, shares=shares, buy_date=buy_date)
    if not h:
        typer.echo(f"持仓 #{id} 不存在")
        return
    typer.echo(f"已更新持仓 #{id}: {h.code} {h.name} 成本{h.cost_price}元 {h.shares}股 日期{h.buy_date}")


@portfolio_app.command("remove")
def portfolio_remove(id: int):
    """Remove a holding by ID, or a watchlist entry by code."""
    h = get_holding(id)
    if h:
        remove_holding(id)
        add_transaction(h.code, h.name, "sell", 0, h.shares, f"清仓 #{id} 成本{h.cost_price}元")
        typer.echo(f"已删除持仓 #{id}: {h.code} {h.name}")
    else:
        typer.echo(f"持仓 #{id} 不存在")


@portfolio_app.command("check")
def portfolio_check():
    """Check all holdings and watchlist against trigger conditions."""
    holdings = list_holdings()
    watchlist = list_watchlist()
    all_codes = [(h.code, h.name) for h in holdings] + [(w.code, w.name) for w in watchlist]

    if not all_codes:
        typer.echo("暂无持仓和关注")
        return

    typer.echo(f"正在巡检 {len(all_codes)} 只股票...")

    signals = []
    for code, name in all_codes:
        # Get current quote
        q = stock_quote(code)
        if "error" in q:
            typer.echo(f"  {code}: 无法获取行情")
            continue

        current_price = q.get("price", 0)
        triggers = list_triggers(code)

        triggered = False
        for t in triggers:
            if t.type == "price_stop_loss" and current_price <= t.value:
                notify_trigger(code, name, "止损", t.value, f"当前价 {current_price} <= 止损价 {t.value}")
                triggered = True
            elif t.type == "price_stop_profit" and current_price >= t.value:
                notify_trigger(code, name, "止盈", t.value, f"当前价 {current_price} >= 止盈价 {t.value}")
                triggered = True
            elif t.type == "price_stop_loss_adaptive" and current_price <= t.value:
                notify_trigger(code, name, "动态止损", t.value, f"当前价 {current_price} <= 动态止损线 {t.value}")
                triggered = True
            elif t.type == "price_stop_profit_adaptive" and current_price >= t.value:
                notify_trigger(code, name, "动态止盈", t.value, f"当前价 {current_price} >= 动态止盈线 {t.value}")
                triggered = True
            elif t.type == "pe_high":
                pe = q.get("pe_dynamic")
                if pe and pe >= t.value:
                    notify_trigger(code, name, "PE预警", t.value, f"当前PE {pe} >= 预警值 {t.value}")
                    triggered = True
            elif t.type == "near_52w_low" and current_price <= t.value:
                notify_trigger(code, name, "接近52周低点", t.value, f"当前价 {current_price} <= 52周低点线 {t.value}")
                triggered = True
            elif t.type == "fund_flow_negative":
                from hermes.data.fund_flow import stock_fund_flow
                ff = stock_fund_flow(code)
                if "error" not in ff:
                    items = ff.get("fund_flow", [])
                    if items:
                        latest_main_net = items[0].get("main_net_inflow", 0)
                        if latest_main_net is not None and latest_main_net < t.value:
                            notify_trigger(code, name, "资金流出", t.value, f"主力净流入 {latest_main_net}万 < 阈值 {t.value}万")
                            triggered = True

        if not triggered:
            signal = "hold"
            profit_yoy = q.get("profit_yoy")
            if profit_yoy is not None and profit_yoy > 15:
                signal = "buy"
            elif profit_yoy is not None and profit_yoy < -20:
                signal = "sell"
            notify(code, name, signal, f"价格 {current_price} | PE {q.get('pe_dynamic')} | 净利同比 {q.get('profit_yoy')}%")

        signals.append({"code": code, "name": name, "price": current_price, "triggered": triggered})

    typer.echo("\n巡检完成")


# ─── Config commands ───

config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show():
    """Show current configuration."""
    from hermes.config import load_config
    cfg = load_config()
    console.print(Panel(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        title="Hermes 配置", border_style="cyan",
    ))


@config_app.command("set")
def config_set(
    key: str = typer.Option(..., "--key", "-k", help="配置键，如 factor_weights.value"),
    value: str = typer.Option(..., "--value", "-v", help="配置值"),
):
    """Set a configuration value. Use dot notation for nested keys (e.g. factor_weights.value)."""
    from hermes.config import load_config, save_config

    cfg = load_config()
    keys = key.split(".")
    target = cfg
    for k in keys[:-1]:
        if k not in target or not isinstance(target[k], dict):
            typer.echo(f"配置路径 {key} 不存在")
            return
        target = target[k]

    # Try numeric conversion
    try:
        parsed = float(value)
        if parsed == int(parsed):
            parsed = int(parsed)
    except ValueError:
        parsed = value

    target[keys[-1]] = parsed
    save_config(cfg)
    typer.echo(f"已设置 {key} = {parsed}")


# ─── Trigger commands ───

@trigger_app.command("list")
def trigger_list(code: str = typer.Option("", "--code", "-c", help="股票代码（空=全部）")):
    """List trigger conditions."""
    triggers = list_triggers(code)
    if not triggers:
        typer.echo("暂无触发条件")
        return
    for t in triggers:
        typer.echo(f"  #{t.id} [{t.code} {t.name}] {t.type} 阈值={t.value} {t.description}")


@trigger_app.command("add")
def trigger_add(
    code: str,
    type: str = typer.Option(..., "--type", "-t", help="类型: price_stop_loss/price_stop_profit/pe_high/fund_flow_negative"),
    value: float = typer.Option(..., "--value", "-v", help="触发阈值"),
    description: str = typer.Option("", "--desc", "-d", help="描述"),
):
    """Add a trigger condition manually."""
    q = stock_quote(code)
    name = q.get("name", code) if "error" not in q else code
    t = add_trigger(code, name, type, value, description)
    typer.echo(f"已添加触发条件: #{t.id} [{code} {name}] {type} 阈值={value}")


@trigger_app.command("remove")
def trigger_remove(id: int):
    """Remove a trigger condition by ID."""
    if remove_trigger(id):
        typer.echo(f"已删除触发条件 #{id}")
    else:
        typer.echo(f"触发条件 #{id} 不存在")


if __name__ == "__main__":
    app()