# Project: Hermes

## 网络搜索规则

**必须使用 MCP 工具进行网络搜索，禁止使用 Claude Code 内置的 WebSearch/WebFetch。**

- 网页搜索：用 MCP `web_search`（backend="google"，失败切 "lite")
- 新闻搜索：用 MCP `web_search_news`
- 网页内容抓取：用 MCP `web_fetch_page`（指定 keywords 过滤）

原因：MCP 搜索工具是本项目专门搭建的，覆盖范围和稳定性优于内置工具。

## 评估流程

单股评估时，按 `.claude/commands/evaluate-stock.md` 的 skill 执行，8步全流程不可省略。
量化数据用 MCP stock_* 工具获取，不要用 Bash 调用 Python 脚本绕过。