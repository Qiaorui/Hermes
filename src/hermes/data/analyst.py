"""Analyst research reports and consensus — professional investment opinions.

Provides:
  - Research report list (rating, institution, date, title, EPS forecasts)
  - Profit forecasts (EPS consensus by year)
  - Institutional participation level (机构参与度)

Uses akshare stock_research_report_em + stock_profit_forecast_ths APIs.

Strict data policy: returns what's available. Missing data → None + unavailable label.
"""

import logging
from hermes.api.eastmoney import em_get

log = logging.getLogger(__name__)


def _fetch_research_reports(code: str) -> list[dict] | None:
    """Fetch research report list for a stock from akshare."""
    try:
        import akshare as ak
        df = ak.stock_research_report_em(symbol=code)
        if df is None or len(df) == 0:
            return None

        reports = []
        for _, row in df.iterrows():
            try:
                entry = {
                    "title": str(row.get("报告名称", "")),
                    "rating": str(row.get("东财评级", "")),
                    "institution": str(row.get("机构", "")),
                    "date": str(row.get("日期", "")),
                    "industry": str(row.get("行业", "")),
                    "pdf_url": str(row.get("报告PDF链接", "")),
                    "eps_2026": float(row.get("2026-盈利预测-收益", 0)) if row.get("2026-盈利预测-收益") and str(row.get("2026-盈利预测-收益")) != "nan" else None,
                    "pe_2026": float(row.get("2026-盈利预测-市盈率", 0)) if row.get("2026-盈利预测-市盈率") and str(row.get("2026-盈利预测-市盈率")) != "nan" else None,
                    "eps_2027": float(row.get("2027-盈利预测-收益", 0)) if row.get("2027-盈利预测-收益") and str(row.get("2027-盈利预测-收益")) != "nan" else None,
                    "pe_2027": float(row.get("2027-盈利预测-市盈率", 0)) if row.get("2027-盈利预测-市盈率") and str(row.get("2027-盈利预测-市盈率")) != "nan" else None,
                    "eps_2028": float(row.get("2028-盈利预测-收益", 0)) if row.get("2028-盈利预测-收益") and str(row.get("2028-盈利预测-收益")) != "nan" else None,
                    "pe_2028": float(row.get("2028-盈利预测-市盈率", 0)) if row.get("2028-盈利预测-市盈率") and str(row.get("2028-盈利预测-市盈率")) != "nan" else None,
                }
                reports.append(entry)
            except (ValueError, TypeError):
                continue

        return reports if reports else None
    except Exception as e:
        log.warning(f"akshare research_reports failed for {code}: {e}")
        return None


def _fetch_profit_forecast(code: str) -> dict | None:
    """Fetch EPS profit forecast consensus from akshare (同花顺)."""
    try:
        import akshare as ak

        indicators = ["预测年报每股收益", "预测年报净利润", "预测年报营业收入"]
        forecasts = {}
        for indicator in indicators:
            try:
                df = ak.stock_profit_forecast_ths(symbol=code, indicator=indicator)
                if df is not None and len(df) > 0:
                    entries = []
                    for _, row in df.iterrows():
                        try:
                            entries.append({
                                "year": str(row.get("年度", "")),
                                "analyst_count": int(row.get("预测机构数", 0)) if row.get("预测机构数") else None,
                                "min": float(row.get("最小值", 0)) if row.get("最小值") else None,
                                "mean": float(row.get("均值", 0)) if row.get("均值") else None,
                                "max": float(row.get("最大值", 0)) if row.get("最大值") else None,
                                "industry_avg": float(row.get("行业平均数", 0)) if row.get("行业平均数") else None,
                            })
                        except (ValueError, TypeError):
                            continue
                    forecasts[indicator] = entries
            except Exception:
                continue

        if not forecasts:
            return None
        return forecasts
    except Exception as e:
        log.warning(f"akshare profit_forecast failed for {code}: {e}")
        return None


def _fetch_institutional_participation(code: str) -> dict | None:
    """Fetch institutional participation level from akshare."""
    try:
        import akshare as ak
        df = ak.stock_comment_detail_zlkp_jgcyd_em(symbol=code)
        if df is None or len(df) == 0:
            return None

        latest = df.iloc[0]
        return {
            "date": str(latest.get("交易日", "")),
            "institutional_participation_pct": float(latest.get("机构参与度", 0)) if latest.get("机构参与度") else None,
        }
    except Exception as e:
        log.warning(f"akshare institutional_participation failed for {code}: {e}")
        return None


def stock_analyst(code: str) -> dict:
    """Get analyst research data for a stock.

    Returns research reports, profit forecasts, and institutional participation.
    Tries akshare as primary source. Returns explicit unavailable when data not found.
    """
    result = {
        "code": code,
        "research_reports": None,
        "profit_forecast": None,
        "institutional_participation": None,
    }

    # Research reports
    reports = _fetch_research_reports(code)
    if reports:
        result["research_reports"] = reports
        # Extract consensus summary
        ratings = [r["rating"] for r in reports if r["rating"]]
        eps_forecasts = [r for r in reports if r.get("eps_2026") is not None]
        if ratings:
            # Count rating distribution
            buy_count = sum(1 for r in ratings if r in ["买入", "强烈推荐", "推荐"])
            hold_count = sum(1 for r in ratings if r in ["增持", "中性", "持有"])
            sell_count = sum(1 for r in ratings if r in ["减持", "卖出"])
            total = len(ratings)
            consensus_rating = "buy" if buy_count > hold_count + sell_count else ("hold" if hold_count >= buy_count else "sell")
            result["consensus"] = {
                "rating": consensus_rating,
                "buy_pct": round(buy_count / total * 100, 1) if total > 0 else None,
                "hold_pct": round(hold_count / total * 100, 1) if total > 0 else None,
                "sell_pct": round(sell_count / total * 100, 1) if total > 0 else None,
                "total_reports": total,
            }
        if eps_forecasts:
            latest_report = eps_forecasts[0]
            result["eps_forecast_latest"] = {
                "eps_2026": latest_report.get("eps_2026"),
                "pe_2026": latest_report.get("pe_2026"),
                "eps_2027": latest_report.get("eps_2027"),
                "institution": latest_report.get("institution"),
                "date": latest_report.get("date"),
            }

    # Profit forecast consensus
    forecast = _fetch_profit_forecast(code)
    if forecast:
        result["profit_forecast"] = forecast
        # Extract EPS consensus if available
        eps_data = forecast.get("预测年报每股收益", [])
        if eps_data:
            result["eps_consensus"] = eps_data

    # Institutional participation
    inst = _fetch_institutional_participation(code)
    if inst:
        result["institutional_participation"] = inst

    # If all three failed
    if not reports and not forecast and not inst:
        result["error"] = "All analyst data sources unavailable"

    return result