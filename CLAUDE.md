# Project: Hermes

A股量化分析与持仓管理工具，支持 CLI 和 MCP Server 双模式运行。

## 架构概览

```
数据源 (akshare, eastmoney, sina, duckduckgo)
    → API 层 (api/)
    → 数据层 (data/)        — 17 个数据模块
    → 因子评分 (factors/)    — 8 因子 + 综合评分
    → 策略/分析 (strategy/)  — 评估策略生成结构化报告
    → 服务层 (service/)      — 持仓/分红/绩效/巡逻共享逻辑
    → 持仓存储 (portfolio/)  — SQLite CRUD
    → 展示层 (cli.py / server.py)
```

**技术栈**: Python 3.14 + uv + Typer (CLI) + FastMCP (Server) + SQLite + Rich

**项目数据目录**: `.hermes/` — 包含 `hermes.db`、`config.json`、缓存文件

## 目录结构

| 路径 | 用途 |
|------|------|
| `src/hermes/api/` | 数据源适配: eastmoney.py, sina.py, search.py |
| `src/hermes/data/` | 17 模块: quote, kline, fund_flow, announcements, valuation, financial, shareholders, unlock, market, dividend, industry, industry_chain, macro, analyst, northbound, dragon_tiger, events, screen, cache |
| `src/hermes/factors/` | 8 因子评分 (Barra CNE5S): value, growth, quality, dividend, momentum, capital_flow, volatility, liquidity + composite + utils |
| `src/hermes/strategy/` | base.py (策略协议) + eval.py (评估策略) |
| `src/hermes/service/` | portfolio.py — 持仓集中度/分红/绩效/巡逻/评估共享逻辑 |
| `src/hermes/portfolio/` | models.py (5 数据类) + db.py (CRUD) |
| `src/hermes/notify/` | 通知系统: CLI notifier + webhook notifier |
| `src/hermes/cli.py` | Typer CLI (~710 行) |
| `src/hermes/server.py` | FastMCP Server (~628 行, 38 tools) |
| `src/hermes/config.py` | 项目级配置管理 |

## 网络搜索规则

**必须使用 MCP 工具进行网络搜索，禁止使用 Claude Code 内置的 WebSearch/WebFetch。**

- 网页搜索：`web_search`（backend="google"，失败切 "lite")
- 新闻搜索：`web_search_news`
- 网页抓取：`web_fetch_page`（指定 keywords 过滤）
- PDF 抓取：`web_fetch_pdf`（研报等）

## MCP 工具清单

### 数据查询 (18)
`mcp_stock_quote` · `mcp_stock_kline` · `mcp_stock_fund_flow` · `mcp_stock_announcements` · `mcp_stock_valuation_history` · `mcp_stock_financial` · `mcp_stock_shareholders` · `mcp_stock_unlock_schedule` · `mcp_market_index` · `mcp_stock_dividend` · `mcp_industry_chain` · `mcp_macro_indicators` · `mcp_stock_analyst` · `mcp_dragon_tiger` · `mcp_northbound_flow` · `mcp_industry_benchmarks` · `mcp_corporate_events` · `mcp_screen`

### 因子评分 (2)
`mcp_factor_score` — 单因子评分 (0-10) · `mcp_factor_composite` — 8 因子加权综合评分 + 信号

### 报告与触发 (4)
`save_evaluation_report` · `save_trigger_conditions` · `mcp_get_report` · `mcp_export_report`

### 持仓管理 (7)
`mcp_add_holding` · `mcp_remove_holding` · `mcp_list_holdings` · `mcp_add_watch` · `mcp_remove_watch` · `mcp_list_watchlist` · `mcp_list_triggers`

### 持仓分析 (4)
`mcp_portfolio_concentration` · `mcp_portfolio_dividend` · `mcp_portfolio_performance` · `mcp_portfolio_log`

### 其他 (3)
`mcp_evaluate` · `mcp_patrol` · `mcp_config_show` / `mcp_config_set`

## 因子评分体系

8 因子 (Barra CNE5S adapted)，权重可配置 (`mcp_config_set factor_weights.xxx`)：

| 因子 | 默认权重 | 数据源 |
|------|----------|--------|
| value | 0.20 | PE/PB 历史分位 |
| growth | 0.20 | 收入/利润增速 |
| quality | 0.20 | ROE/毛利率/资产负债率 |
| dividend | 0.15 | 股息率/分红稳定性 |
| momentum | 0.06 | 动量因子 |
| capital_flow | 0.06 | 主力资金流向 |
| volatility | 0.06 | 波动率因子 |
| liquidity | 0.07 | 流动性因子 |

**信号阈值**: score ≥ 7 → buy · ≥ 5 → hold · ≥ 3 → watch · < 3 → sell

## 评估流程

单股评估时，按 `.claude/commands/evaluate-stock.md` 模板执行，8 步全流程不可省略。

**触发方式：**
- `/evaluate-stock 002352` → 自动加载模板，$ARGUMENTS 替换为股票代码
- "帮我分析XXX" / "评估顺丰控股" → 主动读取模板并按 8 步执行

**量化数据**：用 MCP `mcp_*` 工具获取，不要用 Bash 调用 Python 脚本绕过。

**因子评分**：用 MCP `mcp_factor_composite(code)` 获取，报告第三部分应包含 8 因子评分表。

**报告存储**：第 8 步必须调用 `save_evaluation_report` 和 `save_trigger_conditions` 持久化结果。

## 数据策略

- 量化数据优先用 MCP 工具获取
- 数据不可用时显式标注 `unavailable` + `coverage_pct`，不做静默回退
- 因子评分支持多源回退（eastmoney → sina → akshare）