# Technical Debt Register

Technical debt items for devcontext-mcp (Project 3). `[ ]` = open, `[X]` = resolved.

When code changes surface a new debt item, Claude Code adds an entry inline. When an item is
resolved, mark it `[X]` in the same commit that lands the fix — keep the entry (with its commit
ref), do not delete it. Format is kept consistent with `auto-sentinel/DEBT.md`.

Debt here is anchored to the phase roadmap (Phase 1 mock server complete → Phase 2 real backends).

---

## Phase 2 Anchors (real backend integration)

- [ ] **All 6 tools are mocks**: every `tools/<name>.py` returns a hard-coded dict. Phase 2
  replaces function bodies with real HTTP calls to auto-sentinel (tools 1-3) and devdocs-rag
  (tools 4-6). Interface-first design means the Pydantic schemas and MCP registration stay
  untouched. Gated on: devdocs-rag Phase 6 completing (auto-sentinel Sprint 5 is already done).
  Do NOT wire real backends before Phase 2 formally starts.

- [ ] **trace_id propagation header undecided**: MCP → auto-sentinel calls must carry the
  trace_id (32-char lowercase hex, generated at auto-sentinel's incident entrypoint, OTel
  compatible). W3C `Traceparent` vs custom `X-Trace-Id` — decide empirically during Phase 2 and
  record the decision here + in `docs/PROJECT.md`.

- [ ] **Cursor integration untested**: live verification so far is Claude Code only. Phase 2
  should repeat the `/mcp` + tool-invocation verification in Cursor.
