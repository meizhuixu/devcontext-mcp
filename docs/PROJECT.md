# DevContext MCP — Project Context & Status

> 项目上下文 + 进度快照。**维护规则：每次代码 PR 落地，顺手更新「当前状态」段和涉及的决策段。**
> 权威进度以 `git log` / `DEBT.md` 为准，本文件是快照 + 上下文入口。
> 矩阵全局上下文见 `~/Repo/PORTFOLIO.md`（本地文件，不入库）。

---

## 当前状态（快照 2026-07-03）

- ✅ **Phase 1 完成**（2026-04-28），main 干净且与远端同步。6 tool + 1 resource 全部注册，
  Claude Code 实地集成验证通过（`/mcp` 列出 devcontext、Opus 主动调 tool、结构化返回进对话）。
- ⏳ **Phase 2 待启动**：mock → 真实 HTTP 后端。前置条件：项目 1 Sprint 5 ✅（已完成）+
  项目 2 Phase 6（未启动）。矩阵串行顺序里本项目排最后，**不要提前动**。
- Phase 2 待办细项见 `DEBT.md`（本次新建）。

---

## 项目是什么

MCP (Model Context Protocol) server，把 Auto Sentinel（项目 1）和 DevDocs RAG（项目 2）的能力
以 tool/resource 形式暴露给 Claude Code / Claude Desktop / Cursor。本项目是集成面，不拥有智能——
只做转发 + 结构化返回。

## 暴露的 6 tool + 1 resource

| # | Name | 来自 | 状态 |
|---|---|---|---|
| 1 | `analyze_error_log(log)` | Auto Sentinel | mock |
| 2 | `search_past_incidents(query, limit)` | Auto Sentinel | mock |
| 3 | `propose_fix(error_id)` | Auto Sentinel | mock |
| 4 | `search_codebase(query, repo)` | DevDocs RAG | mock |
| 5 | `find_examples(api_name)` | DevDocs RAG | mock |
| 6 | `summarize_pr(pr_url)` | DevDocs RAG | mock |
| R | `devcontext://session` | 内置 | mock |

**Phase 1 关键事实**：6 tool 全部 mock（返回写死的字典结构）。接口先行设计——换真实 backend
只改 `tools/<name>.py` 函数体，MCP client 端零修改。

## 关键技术

MCP over **stdio** / Anthropic 官方 Python `mcp` SDK / Pydantic v2（每个 tool 的 Input/Output
schema）/ mypy --strict / 9 smoke + 单元测试，CI gating

## 技术栈

Python 3.11+ / `mcp` SDK / Pydantic v2 / mypy --strict + ruff / pytest / GitHub Actions / uv

## Phase 2 范围（待启动）

1. 6 tool 函数体 mock → 真实 HTTP 调用 auto-sentinel 和 devdocs-rag
2. trace_id 跨服务透传（MCP → Auto Sentinel）——W3C `Traceparent` header 还是自定义
   `X-Trace-Id`，Phase 2 实测决定。注意上游约定：trace_id 是 32-char lowercase hex
   （auto-sentinel 入口生成，OTel 兼容）
3. Cursor 集成测试（目前只在 Claude Code 验证过）

## 后续可加（非必须）

- 90 秒 demo 视频
- `run_tests(repo, pattern)` tool 扩展示范
- MCP prompt template（`/devcontext:debug-incident` 斜杠命令）
