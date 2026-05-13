"""Portfolio analysis service — shared logic for CLI and MCP."""

from hermes.portfolio.db import (
    list_holdings, list_watchlist, list_triggers,
    save_report, save_triggers,
)
from hermes.data.quote import stock_quote
from hermes.data.dividend import stock_dividend
from hermes.data.kline import stock_kline
from hermes.strategy.eval import analyze, get_triggers
from hermes.portfolio.models import TriggerCondition


def portfolio_concentration_data() -> dict:
    """Compute portfolio industry concentration. Returns dict with industries, warnings."""
    holdings = list_holdings()
    if not holdings:
        return {"error": "No holdings"}

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
    return {"total_mv_wan": round(total_mv / 10000, 2), "industries": result, "warnings": warnings}


def portfolio_dividend_data() -> dict:
    """Compute dividend income summary for all holdings."""
    holdings = list_holdings()
    if not holdings:
        return {"error": "No holdings"}

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

    return {"total_dividend_income": round(total_dividend, 2), "total_wan": round(total_dividend / 10000, 2), "items": items}


def portfolio_performance_data() -> dict:
    """Compute portfolio performance vs CSI 300 benchmark."""
    holdings = list_holdings()
    if not holdings:
        return {"error": "No holdings"}

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

    return {"items": items, "weighted_pnl_pct": weighted_pnl, "weighted_bench_pct": weighted_bench, "weighted_excess_pct": weighted_excess}


def patrol_data() -> dict:
    """Check all holdings/watchlist against trigger conditions. Returns alerts."""
    holdings = list_holdings()
    watchlist = list_watchlist()
    all_codes = [(h.code, h.name) for h in holdings] + [(w.code, w.name) for w in watchlist]

    if not all_codes:
        return {"error": "No holdings or watchlist"}

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

    return {"checked": len(all_codes), "alerts": alerts, "alert_count": len(alerts)}


def evaluate_stock(code: str) -> dict:
    """Run full evaluation on a stock. Returns signal, score, report, triggers."""
    analysis = analyze(code)
    signal = analysis.get("signal", "hold")
    report_text = analysis.get("report", "")
    score = analysis.get("score", 0)

    save_report(code, report_text, score)

    triggers_raw = get_triggers(code, analysis)
    trigger_models = [TriggerCondition(**t) for t in triggers_raw]
    save_triggers(trigger_models)

    return {
        "code": code,
        "signal": signal,
        "score": score,
        "report_length": len(report_text),
        "triggers_count": len(triggers_raw),
        "report": report_text,
    }