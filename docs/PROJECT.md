# DevContext MCP — Project Context & Status

> 项目上下文 + 进度快照。**维护规则：每次代码 PR 落地，顺手更新「当前状态」段和涉及的决策段。**
> 权威进度以 `git log` / `DEBT.md` 为准，本文件是快照 + 上下文入口。
> 矩阵全局上下文见 `~/Repo/PORTFOLIO.md`（本地文件，不入库）。

---

## 当前状态（快照 2026-07-03，M4 代码完成）

- ✅ **Phase 1 完成**（2026-04-28）。6 tool + 1 resource 全部注册，Claude Code 实地集成验证通过。
- ✅ **Phase 2（M4）代码完成 + 程序化实测通过**（2026-07-03，本地 commit 未 push）：
  - 5/6 tool 在 `DEVCONTEXT_BACKEND_MODE=http` 下真调用后端（`summarize_pr` 无后端端点，
    降级保留 mock 并显式标注，见 DEBT.md）。接口先行设计兑现：只改 clients 层 +
    `analyze_error_log` 输出增量扩展（`incident_id`/`status`）。
  - **trace_id 透传定案：自定义 `X-Trace-Id`**（弃 W3C Traceparent，理由见 DEBT.md）。
    实测：MCP 生成的 id 成为 Langfuse parent trace（`fdd45304…`，4 个 generation 嵌套）。
  - 依赖两个后端的 `feat/m4-mcp-enabler` 分支（**均未合并、未 push**）：auto-sentinel
    新增 GET alerts/{id} + incidents 搜索 + X-Trace-Id 入口（470 tests 绿）；devdocs-rag
    新增 retrieval_only + line/chunk_type 字段（145 tests 绿）。
- ⏳ **M4 剩余**：Claude Code 会话内实测（MCP 配置已切 http，待 reconnect）+ Cursor 双端验证；
  两个 enabler 分支的 merge/push 需 owner 确认。

---

## 项目是什么

MCP (Model Context Protocol) server，把 Auto Sentinel（项目 1）和 DevDocs RAG（项目 2）的能力
以 tool/resource 形式暴露给 Claude Code / Claude Desktop / Cursor。本项目是集成面，不拥有智能——
只做转发 + 结构化返回。

## 暴露的 6 tool + 1 resource

| # | Name | 来自 | 状态 |
|---|---|---|---|
| 1 | `analyze_error_log(log)` | Auto Sentinel | ✅ http（X-Trace-Id 注入 + 轮询） |
| 2 | `search_past_incidents(query, limit)` | Auto Sentinel | ✅ http |
| 3 | `propose_fix(error_id)` | Auto Sentinel | ✅ http |
| 4 | `search_codebase(query, repo)` | DevDocs RAG | ✅ http（SSE retrieval_only） |
| 5 | `find_examples(api_name)` | DevDocs RAG | ✅ http（code chunk 过滤） |
| 6 | `summarize_pr(pr_url)` | DevDocs RAG | mock（无后端端点，降级，见 DEBT） |
| R | `devcontext://session` | 内置 | mock |

**关键事实**：默认 `DEVCONTEXT_BACKEND_MODE=mock`（零外部依赖）；`http` 模式走真后端。
接口先行设计兑现——Phase 2 只改了 `clients/` 层，tool schema 与 MCP 注册零修改
（除 `analyze_error_log` 输出的增量扩展）。

## 关键技术

MCP over **stdio** / Anthropic 官方 Python `mcp` SDK / Pydantic v2（每个 tool 的 Input/Output
schema）/ mypy --strict / 9 smoke + 单元测试，CI gating

## 技术栈

Python 3.11+ / `mcp` SDK / Pydantic v2 / mypy --strict + ruff / pytest / GitHub Actions / uv

## Phase 2 范围（M4）

1. ✅ tool mock → 真实 HTTP 调用（5/6；`summarize_pr` 降级见 DEBT.md）
2. ✅ trace_id 跨服务透传定案：**自定义 `X-Trace-Id`**（32-hex 直传，弃 Traceparent；
   MCP 生成 id、sentinel 入口采纳并自己 `open_parent_trace`，parent 归属留在 sentinel，
   避开 orphan generation 坑）。实测 trace `fdd45304…` 单父 4 generation 进 Langfuse。
3. ⏳ Claude Code 会话内实测（配置已切 http，待 reconnect）+ Cursor 集成测试

## 后续可加（非必须）

- 90 秒 demo 视频
- `run_tests(repo, pattern)` tool 扩展示范
- MCP prompt template（`/devcontext:debug-incident` 斜杠命令）
