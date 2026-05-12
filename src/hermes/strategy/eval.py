"""EvalStrategy — fundamental + technical + catalyst evaluation producing a report and triggers."""

from hermes.data.quote import stock_quote
from hermes.data.kline import stock_kline
from hermes.data.fund_flow import stock_fund_flow
from hermes.data.announcements import stock_announcements
from hermes.data.valuation import stock_valuation_history
from hermes.data.financial import stock_financial
from hermes.data.shareholders import stock_shareholders
from hermes.data.unlock import stock_unlock_schedule
from hermes.data.market import market_index
from hermes.strategy.base import BUY, SELL, HOLD, WATCH


def analyze(code: str) -> dict:
    """Run full evaluation on a stock. Returns dict with signal, report (markdown), score, data."""
    quote = stock_quote(code)
    if "error" in quote:
        return {"signal": WATCH, "report": f"无法获取 {code} 行情数据", "score": 0, "data": {}}

    kline = stock_kline(code, 120)
    valuation = stock_valuation_history(code)
    fund_flow = stock_fund_flow(code, 30)
    announcements = stock_announcements(code, 20)
    income = stock_financial(code, "income", 4)
    balance = stock_financial(code, "balance", 2)
    cashflow = stock_financial(code, "cashflow", 2)
    shareholders = stock_shareholders(code)
    unlock = stock_unlock_schedule(code)
    index = market_index(60)

    data = {
        "quote": quote,
        "kline": kline,
        "valuation": valuation,
        "fund_flow": fund_flow,
        "announcements": announcements,
        "income": income,
        "balance": balance,
        "cashflow": cashflow,
        "shareholders": shareholders,
        "unlock": unlock,
        "market_index": index,
    }

    # Compute basic metrics for scoring
    price = quote.get("price", 0)
    pe = quote.get("pe_dynamic")
    profit_yoy = quote.get("profit_yoy")
    revenue_yoy = quote.get("revenue_yoy")

    # Basic signal logic (placeholder — full analysis is done by the evaluate-stock skill via Claude)
    signal = HOLD
    if profit_yoy is not None and profit_yoy > 15:
        signal = BUY
    elif profit_yoy is not None and profit_yoy < -20:
        signal = SELL

    # Build summary report (detailed report generation is delegated to the skill/AI)
    name = quote.get("name", "")
    report = f"# {name}（{code}）数据摘要\n\n"
    report += f"当前价格: {price} | PE: {pe} | 净利润同比: {profit_yoy}% | 营收同比: {revenue_yoy}%\n"
    report += f"\n建议信号: {signal}\n"
    report += "\n> 详细评估请使用 /evaluate-stock skill 或让AI基于以下数据生成完整报告。\n"

    return {"signal": signal, "report": report, "score": 0, "data": data}


def get_triggers(code: str, analysis: dict) -> list[dict]:
    """Generate trigger conditions from analysis data."""
    triggers = []
    quote = analysis.get("data", {}).get("quote", {})
    valuation = analysis.get("data", {}).get("valuation", {})
    price = quote.get("price", 0)
    name = quote.get("name", "")

    if not price:
        return triggers

    # Stop loss: -10% from current price
    triggers.append({
        "code": code, "name": name,
        "type": "price_stop_loss",
        "value": round(price * 0.90, 2),
        "description": f"止损价 {round(price * 0.90, 2)} 元（当前价 -10%）",
    })

    # Stop profit: +20% from current price
    triggers.append({
        "code": code, "name": name,
        "type": "price_stop_profit",
        "value": round(price * 1.20, 2),
        "description": f"止盈价 {round(price * 1.20, 2)} 元（当前价 +20%）",
    })

    # PE high alert: if PE > 50
    pe = quote.get("pe_dynamic")
    if pe and pe > 0:
        triggers.append({
            "code": code, "name": name,
            "type": "pe_high",
            "value": 50,
            "description": f"PE超50预警（当前PE {pe}）",
        })

    # 52w low proximity: price within 5% of 52-week low
    low_52w = valuation.get("price_52w_low")
    if low_52w and low_52w > 0 and price <= low_52w * 1.05:
        triggers.append({
            "code": code, "name": name,
            "type": "near_52w_low",
            "value": round(low_52w * 1.05, 2),
            "description": f"接近52周最低价 {low_52w} 元",
        })

    return triggers