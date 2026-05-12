"""EvalStrategy — factor-enhanced evaluation producing a full structured report.

Signal logic uses composite_factor scores (8-factor weighted). When factor data
unavailable, falls back to simple profit_yoy logic but marks signal as "mechanical".

Report sections:
  1. Fundamentals (financial data, shareholders)
  2. Technical (price, valuation, fund flow)
  3. Factor scoring (8-factor composite)
  3.5. Industry chain (supply chain, peers, landscape)
  3.6. Analyst consensus (ratings, EPS forecast, institutional participation)
  4. Catalysts (industry, announcements)
  5. Risk assessment
  6. Peer comparison
  7. Unlock schedule
  8. Market environment
  9. Macro indicators
  10. Action recommendation
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
from hermes.data.dividend import stock_dividend
from hermes.data.industry_chain import industry_chain
from hermes.data.macro import macro_indicators
from hermes.data.analyst import stock_analyst
from hermes.data.northbound import northbound_flow
from hermes.strategy.base import BUY, SELL, HOLD, WATCH


def _num(v, suffix="", default="N/A", decimals=2):
    """Format a numeric value with controlled precision."""
    if v is None:
        return default
    try:
        return f"{float(v):.{decimals}f}{suffix}"
    except (ValueError, TypeError):
        return default


def _pct(v, default="N/A"):
    """Format a percentage value. Handles both float and string inputs."""
    if v is None:
        return default
    try:
        return f"{float(v):.2f}%"
    except (ValueError, TypeError):
        return default


def _yi(v, default="N/A"):
    """Format a value as 亿元. Input is assumed to be in 亿元 (from akshare financial API).
    For raw 元 values (e.g. market_cap from push2), divide by 1e8 first.
    """
    if v is None:
        return default
    try:
        v = float(v)
        if abs(v) > 1e6:  # Raw 元 — divide by 1e8
            return f"{v/1e8:.2f}亿"
        return f"{v:.2f}亿"
    except (ValueError, TypeError):
        return default


def _wan(v, default="N/A"):
    """Format a value as 万元. Divides raw 元 by 1e4."""
    if v is None:
        return default
    try:
        v = float(v)
        if abs(v) > 1e4:  # Raw 元 — divide by 1e4
            return f"{v/1e4:.2f}万"
        return f"{v:.2f}万"
    except (ValueError, TypeError):
        return default


def _rating_label(score: float | None) -> str:
    """Convert 0-10 score to Chinese rating label."""
    if score is None:
        return "数据缺失"
    if score >= 7:
        return "优秀"
    if score >= 5:
        return "良好"
    if score >= 3:
        return "一般"
    return "较差"


def _flow_dir(v: float | None) -> str:
    """Return direction label for fund flow: 流入/流出/持平."""
    if v is None:
        return "N/A"
    if v > 0:
        return "流入"
    if v < 0:
        return "流出"
    return "持平"


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
    dividend = stock_dividend(code, quote)
    chain = industry_chain(code)
    macro = macro_indicators()
    analyst_data = stock_analyst(code)
    northbound = northbound_flow(30)

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
        "dividend": dividend,
        "industry_chain": chain,
        "macro": macro,
        "analyst": analyst_data,
        "northbound": northbound,
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
            score = round(factor_score * 5, 0)
            signal = factor_signal
            signal_source = "factor-based"
            data["factor"] = factor_result
    except Exception:
        pass

    # Mechanical fallback
    if signal_source == "mechanical":
        profit_yoy = quote.get("profit_yoy")
        if profit_yoy is not None and profit_yoy > 15:
            signal = BUY
        elif profit_yoy is not None and profit_yoy < -20:
            signal = SELL

    # Build full structured report
    name = quote.get("name", code)
    price = quote.get("price", 0)
    pe = quote.get("pe_dynamic")
    profit_yoy = quote.get("profit_yoy")
    revenue_yoy = quote.get("revenue_yoy")
    industry = quote.get("industry", "")

    report = f"# {name}（{code}）综合评估报告\n\n"
    report += f"> 信息截至今日\n\n---\n\n"

    # ── 一、基本面 ──
    report += "### 一、基本面评分\n\n"
    inc_periods = income.get("periods", []) if "error" not in income else []
    bal_periods = balance.get("periods", []) if "error" not in balance else []
    cf_periods = cashflow.get("periods", []) if "error" not in cashflow else []
    latest_inc = inc_periods[0] if inc_periods else {}
    latest_bal = bal_periods[0] if bal_periods else {}
    latest_cf = cf_periods[0] if cf_periods else {}

    report += "| 项目 | 数据 | 评价 |\n|------|------|------|\n"
    rev = latest_inc.get("TOTAL_OPERATE_INCOME")
    np_val = latest_inc.get("PARENT_NETPROFIT")
    np_ratio = latest_inc.get("PARENT_NETPROFIT_RATIO")
    debt_ratio = latest_bal.get("DEBT_ASSET_RATIO")
    ocf = latest_cf.get("NETCASH_OPERATE")

    report += f"| 营收(最新) | {_yi(rev)} | {_pct(revenue_yoy)} |\n"
    report += f"| 净利润(最新) | {_yi(np_val)} | {_pct(profit_yoy)} |\n"
    report += f"| 净利率 | {_pct(np_ratio)} | {'良好' if np_ratio is not None and np_ratio > 10 else '偏低' if np_ratio is not None and np_ratio < 5 else 'N/A'} |\n"
    report += f"| 经营现金流 | {_yi(ocf)} | {'健康' if ocf is not None and np_val is not None and ocf > np_val else '偏弱' if ocf is not None and np_val is not None and ocf < np_val * 0.5 else 'N/A'} |\n"
    report += f"| 资产负债率 | {_pct(debt_ratio)} | {'低杠杆' if debt_ratio is not None and debt_ratio < 40 else '中等' if debt_ratio is not None and debt_ratio < 60 else '高杠杆'} |\n"

    # Financial trend table
    if len(inc_periods) >= 2:
        report += "\n**近4期财务指标趋势**\n\n"
        report += "| 报告期 | 营收(亿) | 净利润(亿) | 净利率% | 营收增速% | 净利增速% |\n|--------|---------|----------|--------|---------|---------|\n"
        for i, p in enumerate(inc_periods[:4]):
            r = p.get("TOTAL_OPERATE_INCOME")
            n = p.get("PARENT_NETPROFIT")
            mr = p.get("PARENT_NETPROFIT_RATIO")
            # Compute YoY from consecutive periods (current vs previous)
            r_prev = inc_periods[i+1].get("TOTAL_OPERATE_INCOME") if i+1 < len(inc_periods) else None
            n_prev = inc_periods[i+1].get("PARENT_NETPROFIT") if i+1 < len(inc_periods) else None
            ry = round((r - r_prev) / r_prev * 100, 2) if r is not None and r_prev is not None and r_prev != 0 else None
            py = round((n - n_prev) / n_prev * 100, 2) if n is not None and n_prev is not None and n_prev != 0 else None
            period = p.get("REPORT_DATE", p.get("REPORT_DATE_NAME", "N/A"))
            if isinstance(period, str):
                period = period[:10]
            report += f"| {period} | {_yi(r)} | {_yi(n)} | {_pct(mr)} | {_pct(ry)} | {_pct(py)} |\n"

    # Shareholders
    sh_data = shareholders if "error" not in shareholders else {}
    top10 = sh_data.get("shareholders", [])
    if top10:
        report += "\n**前十大股东**\n\n"
        report += "| 股东名 | 持股比例% | 增减变动 | 类型 |\n|--------|----------|---------|------|\n"
        for s in top10[:10]:
            report += f"| {s.get('name', 'N/A')} | {s.get('hold_ratio_pct', 'N/A')} | {s.get('change', 'N/A')} | {s.get('change_ratio_pct', 'N/A')} |\n"

    # ── 二、技术面 ──
    report += "\n### 二、技术面评分\n\n"
    report += "| 项目 | 数据 | 评价 |\n|------|------|------|\n"
    val = valuation if "error" not in valuation else {}
    report += f"| 当前价格 | {_num(price, '元')} | — |\n"
    report += f"| 52周最高 | {_num(val.get('price_52w_high'), '元')} | — |\n"
    report += f"| 52周最低 | {_num(val.get('price_52w_low'), '元')} | — |\n"
    price_pct = val.get('price_pct_in_range')
    report += f"| 价格百分位 | {_pct(price_pct)} | {'偏高' if price_pct is not None and price_pct > 80 else '偏低' if price_pct is not None and price_pct < 20 else '中性'} |\n"
    report += f"| MA5 | {_num(val.get('ma5'), '元')} | — |\n"
    report += f"| MA20 | {_num(val.get('ma20'), '元')} | — |\n"
    report += f"| 价格vs MA5 | {_pct(val.get('price_vs_ma5'))} | — |\n"
    report += f"| 价格vs MA20 | {_pct(val.get('price_vs_ma20'))} | — |\n"

    # Fund flow
    ff = fund_flow if "error" not in fund_flow else {}
    ff_list = ff.get("fund_flow", [])
    if ff_list:
        latest_ff = ff_list[0]
        # API uses main_net_inflow, not main_net
        main_net = latest_ff.get("main_net_inflow")
        main_pct = latest_ff.get("main_pct")
        report += f"| 资金流向 | 主力{_wan(main_net)}{_flow_dir(main_net)} | {'主力做多' if main_net is not None and main_net > 0 else '主力做空' if main_net is not None and main_net < 0 else 'N/A'} |\n"

    # ── 三、量化因子评分 ──
    report += "\n### 三、量化因子评分\n\n"
    f = data.get("factor")
    if f and "error" not in f:
        report += "| 因子 | 评分 | 覆盖率% | 评级 | 备注 |\n|------|------|---------|------|------|\n"
        for fname, sf in f.get("sub_factors", {}).items():
            s = sf.get("score")
            c = sf.get("coverage_pct", 0)
            unavail = sf.get("details", {}).get("unavailable", [])
            note = "; ".join(u.get("reason", "") for u in unavail) if unavail else ""
            report += f"| {fname} | {_num(s)} | {_pct(c)} | {_rating_label(s)} | {note} |\n"
        report += f"| **综合** | **{_num(f.get('score'))}** | — | **{signal.upper()}** | 评分来源: {signal_source} |\n"
        missing = f.get("missing_factors", [])
        if missing:
            report += "\n**缺失因子说明**：\n"
            for m in missing:
                report += f"- {m.get('factor')}: {m.get('reason', 'N/A')}\n"
    else:
        report += f"| 综合评分 | N/A | — | {signal.upper()} | 评分来源: {signal_source} |\n"

    # ── 三.五、产业链定位 ──
    report += "\n### 三.五、产业链定位与行业分析\n\n"
    ch = chain if "error" not in chain else {}
    report += "| 项目 | 详情 | 评价 |\n|------|------|------|\n"
    cp = ch.get("chain_position", {})
    upstream = cp.get("upstream", [])
    downstream = cp.get("downstream", [])
    complementary = cp.get("complementary", [])
    substitute = cp.get("substitute", [])
    report += f"| 上游行业 | {', '.join(upstream) if upstream else 'N/A'} | — |\n"
    report += f"| 下游行业 | {', '.join(downstream) if downstream else 'N/A'} | — |\n"
    report += f"| 互补行业 | {', '.join(complementary) if complementary else 'N/A'} | — |\n"
    report += f"| 替代威胁 | {', '.join(substitute) if substitute else 'N/A'} | — |\n"
    landscape = ch.get("landscape", {})
    concentration = landscape.get("top3_concentration")
    our_rank = landscape.get("our_market_cap_rank")
    total_peers = landscape.get("total_peers")
    report += f"| 行业集中度 | Top3占比{_pct(concentration)} | {'垄断格局' if concentration is not None and concentration > 60 else '竞争格局' if concentration is not None and concentration < 30 else '中等集中' if concentration is not None else 'N/A'} |\n"
    report += f"| 公司行业排名 | 第{our_rank}名/共{total_peers}家 | {'领导者' if our_rank is not None and our_rank <= 3 else '跟随者' if our_rank is not None and our_rank <= 10 else 'N/A'} |\n"
    report += f"| 行业 | {industry} | — |\n"

    # ── 三.六、分析师共识 ──
    report += "\n### 三.六、分析师共识与盈利预测\n\n"
    ad = analyst_data if "error" not in analyst_data else {}
    consensus = ad.get("consensus", {})
    eps_latest = ad.get("eps_forecast_latest", {})
    inst_part = ad.get("institutional_participation", {})
    reports_list = ad.get("research_reports", [])
    report += "| 项目 | 详情 | 评价 |\n|------|------|------|\n"
    if consensus:
        report += f"| 机构共识评级 | 买入{_pct(consensus.get('buy_pct'))} / 增持{_pct(consensus.get('hold_pct'))} / 减持{_pct(consensus.get('sell_pct'))} | {'整体看好' if consensus.get('rating') == 'buy' else '偏中性' if consensus.get('rating') == 'hold' else '看淡'} |\n"
    else:
        report += "| 机构共识评级 | N/A | 无研报数据 |\n"
    report += f"| EPS预测2026 | {_num(eps_latest.get('eps_2026'), '元')} | — |\n"
    report += f"| EPS预测2027 | {_num(eps_latest.get('eps_2027'), '元')} | — |\n"
    if reports_list:
        latest_r = reports_list[0]
        report += f"| 最新研报 | {latest_r.get('title', 'N/A')} ({latest_r.get('institution', 'N/A')}, {latest_r.get('date', 'N/A')}) | — |\n"
    else:
        report += "| 最新研报 | N/A | — |\n"
    inst_pct = inst_part.get("institutional_participation_pct")
    report += f"| 机构参与度 | {_pct(inst_pct)} | {'机构高度关注' if inst_pct is not None and inst_pct > 50 else '机构关注度低' if inst_pct is not None else 'N/A'} |\n"

    # ── 四、题材与催化剂 ──
    report += "\n### 四、题材与催化剂\n\n"
    report += "| 项目 | 详情 | 评价 |\n|------|------|------|\n"
    report += f"| 所属行业 | {industry} | — |\n"
    ann_items = announcements.get("announcements", []) if "error" not in announcements else []
    recent_ann = ann_items[:3] if ann_items else []
    if recent_ann:
        for a in recent_ann:
            report += f"| 近期公告 | {a.get('title', 'N/A')} ({a.get('date', 'N/A')}) | — |\n"
    else:
        report += "| 近期公告 | N/A | — |\n"

    # ── 五、风险评估 ──
    report += "\n### 五、风险评估\n\n"
    report += "| 风险项 | 详情 | 严重程度 |\n|--------|------|----------|\n"
    profit_risk = "高" if profit_yoy is not None and profit_yoy < -20 else "中" if profit_yoy is not None and profit_yoy < 0 else "低" if profit_yoy is not None else "N/A"
    report += f"| 盈利风险 | 净利润同比{_pct(profit_yoy)} | {profit_risk} |\n"
    val_risk = "高" if price_pct is not None and price_pct > 80 else "中" if price_pct is not None and price_pct > 60 else "低" if price_pct is not None else "N/A"
    report += f"| 估值风险 | PE {_num(pe)}, 价格百分位 {_pct(price_pct)} | {val_risk} |\n"
    ff_risk = "高" if ff_list and any(it.get("main_net_inflow") is not None and it["main_net_inflow"] < 0 for it in ff_list[:5]) else "低"
    report += f"| 主力资金风险 | 主力近期流向 | {ff_risk} |\n"
    unlock_items = unlock.get("unlocks", []) if "error" not in unlock else []
    unlock_risk = "高" if unlock_items and any(it.get("free_ratio_pct") is not None and it["free_ratio_pct"] > 5 for it in unlock_items[:3]) else "低"
    report += f"| 限售解禁压力 | 近期解禁 | {unlock_risk} |\n"
    debt_risk = "高" if debt_ratio is not None and debt_ratio > 70 else "中" if debt_ratio is not None and debt_ratio > 50 else "低" if debt_ratio is not None else "N/A"
    report += f"| 负债风险 | 资产负债率 {_pct(debt_ratio)} | {debt_risk} |\n"

    # ── 六、同行对比 ──
    report += "\n### 六、同行对比\n\n"
    peers = ch.get("peers", [])
    if peers:
        top_peers = peers[:3]
        peer_names = [p.get("name", "N/A") for p in top_peers]
        col_header = f"| 指标 | {name} | {peer_names[0]} | {peer_names[1] if len(peer_names) > 1 else 'N/A'} | {peer_names[2] if len(peer_names) > 2 else 'N/A'} |\n|------|---------|---------|---------|---------|\n"
        report += col_header
        our_cap = quote.get("market_cap")
        peer_caps = [_yi(p.get("market_cap")) for p in top_peers]
        report += f"| 市值 | {_yi(our_cap)} | {peer_caps[0]} | {peer_caps[1] if len(peer_caps) > 1 else 'N/A'} | {peer_caps[2] if len(peer_caps) > 2 else 'N/A'} |\n"
        report += f"| PE | {_num(pe)} | {_num(top_peers[0].get('pe'))} | {_num(top_peers[1].get('pe')) if len(top_peers) > 1 else 'N/A'} | {_num(top_peers[2].get('pe')) if len(top_peers) > 2 else 'N/A'} |\n"
    else:
        report += "同行业对比数据暂不可用。\n"

    # ── 七、限售解禁 ──
    report += "\n### 七、限售解禁与减持压力\n\n"
    if unlock_items:
        report += "| 解禁日期 | 解禁类型 | 解禁股数(万股) | 占总股本% |\n|----------|---------|-------------|---------|\n"
        for u in unlock_items[:5]:
            report += f"| {u.get('free_date', 'N/A')} | {u.get('free_shares_type', 'N/A')} | {_num(u.get('current_free_shares_wan'))} | {_pct(u.get('free_ratio_pct'))} |\n"
    else:
        report += "近期无限售解禁计划。\n"

    # ── 八、大盘环境 ──
    report += "\n### 八、大盘环境\n\n"
    idx = index if "error" not in index else {}
    report += "| 指标 | 近期走势 | 评价 |\n|------|---------|------|\n"
    for key, label in [("shanghai", "上证指数"), ("shenzhen", "深证成指")]:
        idx_data = idx.get(key)
        if idx_data:
            chg = idx_data.get("latest_change_pct")
            close = idx_data.get("latest_close")
            mood = "偏乐观" if chg is not None and chg > 2 else "偏悲观" if chg is not None and chg < -2 else "中性震荡"
            report += f"| {label} | {_num(close)} ({_pct(chg)}) | {mood} |\n"
        else:
            report += f"| {label} | N/A | — |\n"

    # ── 九、宏观环境 ──
    report += "\n### 九、宏观环境\n\n"
    m = macro if "error" not in macro else {}
    report += "| 指标 | 最新值 | 评价 |\n|------|--------|------|\n"
    pmi_data = m.get("pmi") or {}
    cpi_data = m.get("cpi") or {}
    gdp_data = m.get("gdp") or {}
    lpr_data = m.get("lpr") or {}
    m2_data = m.get("m2") or {}
    pmi_val = pmi_data.get("manufacturing_pmi")
    cpi_val = cpi_data.get("cpi_monthly_rate")
    gdp_val = gdp_data.get("gdp_yoy")
    lpr_1y = lpr_data.get("lpr_1y")
    m2_val = m2_data.get("m2_yoy")
    report += f"| PMI | {_num(pmi_val)} | {'扩张' if pmi_val is not None and pmi_val > 50 else '收缩' if pmi_val is not None else 'N/A'} |\n"
    report += f"| CPI | {_num(cpi_val)} | — |\n"
    report += f"| GDP增速 | {_pct(gdp_val)} | — |\n"
    report += f"| LPR(1年) | {_num(lpr_1y, '%')} | {'利率下行' if lpr_1y is not None and lpr_1y < 3.5 else '利率偏高' if lpr_1y is not None else 'N/A'} |\n"
    report += f"| M2增速 | {_pct(m2_val)} | — |\n"

    # ── 十、操作建议 ──
    report += "\n### 十、操作建议\n\n"
    report += f"- **综合评分**: {score}/50 ({signal.upper()}, 来源: {signal_source})\n"

    f_data = data.get("factor", {})
    momentum_score = f_data.get("sub_factors", {}).get("momentum", {}).get("score") if f_data and "sub_factors" in f_data else None

    short_term = "观望等待"
    if momentum_score is not None:
        if momentum_score >= 7:
            short_term = "顺势做多"
        elif momentum_score <= 3:
            short_term = "规避"
        else:
            short_term = "观望等待"

    mid_term = "关注建仓机会"
    if signal == BUY:
        mid_term = "逢低建仓"
    elif signal == SELL:
        mid_term = "考虑减仓"
    elif signal == WATCH:
        mid_term = "关注，等待信号明确"

    value_score = f_data.get("sub_factors", {}).get("value", {}).get("score") if f_data and "sub_factors" in f_data else None
    growth_score = f_data.get("sub_factors", {}).get("growth", {}).get("score") if f_data and "sub_factors" in f_data else None
    quality_score = f_data.get("sub_factors", {}).get("quality", {}).get("score") if f_data and "sub_factors" in f_data else None

    long_term = "长期逻辑不明确"
    core_scores = [s for s in [value_score, growth_score, quality_score] if s is not None]
    if core_scores:
        avg_core = sum(core_scores) / len(core_scores)
        if avg_core >= 7:
            long_term = "长期价值突出，值得持有"
        elif avg_core >= 5:
            long_term = "长期逻辑尚可，需跟踪基本面变化"
        elif avg_core < 3:
            long_term = "长期基本面偏弱，谨慎"

    report += f"- **短线建议(1-2周)**: {short_term}\n"
    report += f"- **中线建议(1-3月)**: {mid_term}\n"
    report += f"- **长线逻辑(1年+)**: {long_term}\n"
    report += f"- **关键观察指标**: PE {_num(pe)} | 净利润同比 {_pct(profit_yoy)} | 主力资金流向\n"
    report += f"- **风险提示**: 以上分析基于公开数据与量化因子模型，不构成投资建议。\n"

    # Dividend summary
    if "error" not in dividend:
        div_yield = dividend.get("dividend_yield")
        div_years = dividend.get("consecutive_years")
        div_dps = dividend.get("latest_dps")
        if div_dps is not None and div_dps > 0:
            report += f"\n**分红摘要**: 每股分红{_num(div_dps, '元')} | 股息率{_pct(div_yield)} | 连续分红{div_years}年\n"

    # Northbound flow
    if "error" not in northbound:
        nb_items = northbound.get("items", [])
        if nb_items:
            latest_nb = nb_items[0]
            nb_net = latest_nb.get("net_flow")
            nb_cum = northbound.get("cumulative_net")
            report += f"\n**北向资金**: 最新{_wan(nb_net)}{_flow_dir(nb_net)} | 30日累计{_yi(nb_cum)}\n"

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
        if vol_score <= 3:
            stop_pct = 0.85
        elif vol_score <= 6:
            stop_pct = 0.90
        else:
            stop_pct = 0.93
        trigger_type = "price_stop_loss_adaptive"
    else:
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
        from hermes.data.industry import get_industry_median_from_quote
        ind_bench = get_industry_median_from_quote(quote)
        pe_threshold = 50
        if ind_bench:
            ind_pe = ind_bench.get("pe_ttm_median") or ind_bench.get("pe_median")
            if ind_pe is not None and ind_pe > 0:
                pe_threshold = round(ind_pe * 2, 1)

        triggers.append({
            "code": code, "name": name, "source": "auto",
            "type": "pe_high",
            "value": pe_threshold,
            "description": f"PE超{pe_threshold}预警（当前PE {round(pe, 1)}，行业PE中位数 {ind_bench.get('pe_ttm_median') or ind_bench.get('pe_median') if ind_bench else 'N/A'}）",
        })

    # 52w low proximity
    low_52w = valuation.get("price_52w_low")
    if low_52w is not None and low_52w > 0 and price <= low_52w * 1.05:
        triggers.append({
            "code": code, "name": name, "source": "auto",
            "type": "near_52w_low",
            "value": round(low_52w * 1.05, 2),
            "description": f"接近52周最低价 {low_52w} 元",
        })

    return triggers