# Project: Hermes

## 网络搜索规则

**必须使用 MCP 工具进行网络搜索，禁止使用 Claude Code 内置的 WebSearch/WebFetch。**

- 网页搜索：用 MCP `web_search`（backend="google"，失败切 "lite")
- 新闻搜索：用 MCP `web_search_news`
- 网页内容抓取：用 MCP `web_fetch_page`（指定 keywords 过滤）

原因：MCP 搜索工具是本项目专门搭建的，覆盖范围和稳定性优于内置工具。

## 评估流程

单股评估时，按 `.claude/commands/evaluate-stock.md` 模板执行，8步全流程不可省略。

**触发方式：**
- 用户输入 `/evaluate-stock 002352` → 自动加载模板，$ARGUMENTS 替换为股票代码
- 用户说"帮我分析XXX" / "评估顺丰控股"等 → 你应主动读取 evaluate-stock.md 模板并按8步执行

**量化数据**：用 MCP `mcp_*` 工具获取，不要用 Bash 调用 Python 脚本绕过。

**因子评分**：用 MCP `mcp_factor_composite(code)` 获取，报告第三部分应包含8因子评分表。

**报告存储**：第8步必须调用 MCP `save_evaluation_report` 和 `save_trigger_conditions` 将结果持久化。