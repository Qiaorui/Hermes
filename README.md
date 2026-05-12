# Hermes

A股分析、选股筛选与持仓追踪 CLI 工具。

## 功能

- **单股评估** — 8步全面评估（基本面、技术面、题材、风险、同行、解禁、大盘、综合评分）
- **大盘指数** — 7大指数实时监控（上证、深证、创业板、科创50、沪深300、中证500、中证1000）
- **选股筛选** — 按行业、PE、增速等条件筛选
- **持仓管理** — 添加/更新/删除持仓与关注，实时盈亏计算
- **触发条件** — 止损/止盈/PE预警，自动巡检命中
- **看板视图** — rich dashboard 展示持仓盈亏、大盘行情、触发条件

## 安装

```bash
uv pip install -e .
```

## 使用

### CLI

```bash
hermes dashboard                    # 查看持仓看板
hermes evaluate 002352              # 评估股票
hermes portfolio add 002352 -c 40.5 -s 1000  # 添加持仓
hermes portfolio watch 603636       # 添加关注
hermes portfolio check              # 巡检触发条件
hermes screen --pe-max 30 --profit-yoy-min 20  # 选股筛选
hermes report 002352                # 查看评估报告
hermes trigger list                 # 查看触发条件
```

### 自然语言（通过 Claude Code）

搭配 MCP server 使用，用自然语言交互：

> "帮我看看顺丰控股最近资金流向"
> "把002352加到持仓成本40块1000股"
> "巡检一下我的持仓"

MCP server 配置：

```json
{
  "mcpServers": {
    "web-search": {
      "command": "uv",
      "args": ["run", "python", "-m", "hermes.server"]
    }
  }
}
```

评估 skill：`.claude/commands/evaluate-stock.md`

## 项目结构

```
src/hermes/
  api/          — 东方财富、新浪、DuckDuckGo 数据源
  data/         — 行情、K线、资金流、公告、估值、财报、股东、解禁、大盘
  strategy/     — 分析策略（Strategy Protocol）
  portfolio/    — 持仓/关注/触发条件 SQLite 存储
  notify/       — 通知（Notifier Protocol）
  resources/    — skill 模板等打包资源
  server.py     — MCP server
  cli.py        — CLI 入口
```

## License

MIT