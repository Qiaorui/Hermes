"""EvalStrategy — factor-enhanced evaluation producing a report and triggers.

Signal logic now uses composite_factor scores (6-factor weighted) instead of
a single profit_yoy threshold. When factor data unavailable, falls back to
simple profit_yoy logic but marks signal as "mechanical" not "factor-based".
"""

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
    """Run full evaluation on a stock. Returns dict with signal, report, score, data."""
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

    # Factor-based signal (primary)
    signal = HOLD
    score = 0
    signal_source = "mechanical"

    try:
        from hermes.factors.composite import composite_factor
        factor_result = composite_factor(code)
        if "error" not in factor_result:
            factor_score = factor_result.get("score", 0)
            factor_signal = factor_result.get("signal", "hold")
            # Scale factor score (0-10) to 0-50 range for report scoring
            score = round(factor_score * 5, 0)
            signal = factor_signal
            signal_source = "factor-based"
            # Add factor data to analysis
            data["factor"] = factor_result
    except Exception:
        pass

    # Mechanical fallback when factor data unavailable
    if signal_source == "mechanical":
        profit_yoy = quote.get("profit_yoy")
        if profit_yoy is not None and profit_yoy > 15:
            signal = BUY
        elif profit_yoy is not None and profit_yoy < -20:
            signal = SELL

    # Build summary report
    name = quote.get("name", "")
    price = quote.get("price", 0)
    pe = quote.get("pe_dynamic")

    report = f"# {name}（{code}）数据摘要\n\n"
    report += f"当前价格: {price} | PE: {pe} | 净利润同比: {quote.get('profit_yoy')}% | 营收同比: {quote.get('revenue_yoy')}%\n"
    report += f"\n建议信号: {signal} (来源: {signal_source}) | 评分: {score}/50\n"

    if data.get("factor"):
        f = data["factor"]
        report += f"\n因子评分: {f.get('score', 'N/A')}/10\n"
        for name_key, sf in f.get("sub_factors", {}).items():
            s = sf.get("score", "N/A")
            c = sf.get("coverage_pct", 0)
            report += f"  {name_key}: {s} (覆盖率{c}%)\n"

    report += "\n> 详细评估请使用 /evaluate-stock skill 或让AI基于以下数据生成完整报告。\n"

    return {"signal": signal, "report": report, "score": score, "data": data}


def get_triggers(code: str, analysis: dict) -> list[dict]:
    """Generate trigger conditions from analysis data.
    When factor data available, uses volatility/valuation for adaptive thresholds.
    When factor unavailable, uses fixed mechanical thresholds.
    """
    triggers = []
    quote = analysis.get("data", {}).get("quote", {})
    valuation = analysis.get("data", {}).get("valuation", {})
    factor = analysis.get("data", {}).get("factor", {})
    price = quote.get("price", 0)
    name = quote.get("name", "")

    if not price:
        return triggers

    # Adaptive stop-loss based on volatility factor
    vol_score = None
    if factor and "sub_factors" in factor:
        vol = factor["sub_factors"].get("volatility", {})
        vol_score = vol.get("score")

    if vol_score is not None:
        # Higher volatility → wider stop-loss (score 1-3: -15%, 4-6: -10%, 7-10: -7%)
        if vol_score <= 3:
            stop_pct = 0.85
        elif vol_score <= 6:
            stop_pct = 0.90
        else:
            stop_pct = 0.93
        trigger_type = "price_stop_loss_adaptive"
    else:
        # Mechanical fallback: fixed -10%
        stop_pct = 0.90
        trigger_type = "price_stop_loss"

    triggers.append({
        "code": code, "name": name, "source": "auto",
        "type": trigger_type,
        "value": round(price * stop_pct, 2),
        "description": f"止损价 {round(price * stop_pct, 2)} 元（当前价 {price} 元，-{round((1-stop_pct)*100)}%）",
    })

    # Adaptive stop-profit based on valuation percentile
    price_pct = valuation.get("price_pct_in_range")
    if price_pct is not None:
        # Near 52w high (>80%) → tighter profit target (+10%)
        # Near 52w low (<20%) → wider profit target (+25%)
        if price_pct > 80:
            profit_pct = 1.10
        elif price_pct < 20:
            profit_pct = 1.25
        else:
            profit_pct = 1.20
        trigger_type = "price_stop_profit_adaptive"
    else:
        profit_pct = 1.20
        trigger_type = "price_stop_profit"

    triggers.append({
        "code": code, "name": name, "source": "auto",
        "type": trigger_type,
        "value": round(price * profit_pct, 2),
        "description": f"止盈价 {round(price * profit_pct, 2)} 元（当前价 {price} 元，+{round((profit_pct-1)*100)}%）",
    })

    # PE high alert — industry-relative threshold (2x industry median)
    pe = quote.get("pe_dynamic")
    if pe is not None and pe > 0:
        # Try industry-relative threshold first
        from hermes.data.industry import get_industry_median_from_quote
        ind_bench = get_industry_median_from_quote(quote)
        pe_threshold = 50  # fallback absolute threshold
        if ind_bench:
            ind_pe = ind_bench.get("pe_ttm_median") or ind_bench.get("pe_median")
            if ind_pe and ind_pe > 0:
                pe_threshold = round(ind_pe * 2, 1)

        triggers.append({
            "code": code, "name": name, "source": "auto",
            "type": "pe_high",
            "value": pe_threshold,
            "description": f"PE超{pe_threshold}预警（当前PE {round(pe, 1)}，行业PE中位数 {ind_bench.get('pe_ttm_median') or ind_bench.get('pe_median') if ind_bench else 'N/A'}）",
        })

    # 52w low proximity
    low_52w = valuation.get("price_52w_low")
    if low_52w and low_52w > 0 and price <= low_52w * 1.05:
        triggers.append({
            "code": code, "name": name, "source": "auto",
            "type": "near_52w_low",
            "value": round(low_52w * 1.05, 2),
            "description": f"接近52周最低价 {low_52w} 元",
        })

    return triggers