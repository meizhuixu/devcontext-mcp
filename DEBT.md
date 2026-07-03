# Technical Debt Register

Technical debt items for devcontext-mcp (Project 3). `[ ]` = open, `[X]` = resolved.

When code changes surface a new debt item, Claude Code adds an entry inline. When an item is
resolved, mark it `[X]` in the same commit that lands the fix — keep the entry (with its commit
ref), do not delete it. Format is kept consistent with `auto-sentinel/DEBT.md`.

Debt here is anchored to the phase roadmap (Phase 1 mock server complete → Phase 2 real backends).

---

## Phase 2 Anchors (real backend integration)

- [X] **All 6 tools are mocks**: every `tools/<name>.py` returns a hard-coded dict. Phase 2
  replaces function bodies with real HTTP calls to auto-sentinel (tools 1-3) and devdocs-rag
  (tools 4-6). Interface-first design means the Pydantic schemas and MCP registration stay
  untouched. Gated on: devdocs-rag Phase 6 completing (auto-sentinel Sprint 5 is already done).
  Do NOT wire real backends before Phase 2 formally starts.
  **Resolved 2026-07-03 (0500e13, live-verified same day)**: 5 of 6 tools drive real backends
  in `DEVCONTEXT_BACKEND_MODE=http` (interface-first held — only client bodies changed, plus an
  additive `incident_id`/`status` extension on `analyze_error_log`). Requires both backends'
  `feat/m4-mcp-enabler` branches. `summarize_pr` remains mock — tracked in its own entry below.

- [X] **trace_id propagation header undecided**: MCP → auto-sentinel calls must carry the
  trace_id (32-char lowercase hex, generated at auto-sentinel's incident entrypoint, OTel
  compatible). W3C `Traceparent` vs custom `X-Trace-Id` — decide empirically during Phase 2 and
  record the decision here + in `docs/PROJECT.md`.
  **Decision (2026-07-03): custom `X-Trace-Id`.** Rationale: the upstream contract is a bare
  32-hex OTel-compatible trace id with no span-context semantics (`Traceparent` carries
  span-id/flags we have no use for, and Langfuse v2 ingestion does not consume W3C context).
  MCP generates the id per `analyze_error_log` call; auto-sentinel adopts it as
  job_id == trace_id == incident_id and opens the parent Langfuse trace itself (parent-trace
  ownership stays at the sentinel entrypoint, avoiding the orphan-generation gotcha from
  llmops-dashboard docs/onboarding.md "Trace Ownership"). Client side landed in 0500e13.
  **Live-verified 2026-07-03**: MCP-generated id `fdd45304fa19a3f05d43c4159ad3fc97` became the
  Langfuse parent trace with 4 nested generations (diagnosis/supervisor/code_fixer/
  security_reviewer), tokens + CNY cost recorded.

- [ ] **Cursor integration untested**: live verification so far is Claude Code only. Phase 2
  should repeat the `/mcp` + tool-invocation verification in Cursor.

- [ ] **`summarize_pr` has no real backend (descoped from M4, 2026-07-03)**: devdocs-rag has no
  PR endpoint and no PR-fetching code at all; building one (GitHub API + LLM summarize) was cut
  from M4 scope. In http mode the tool returns the canned payload with the summary prefixed
  `[mock — no real backend yet]` so agents cannot mistake it for real analysis. Revisit if the
  M5 demo needs it (likely park permanently).

- [ ] **devdocs-rag trace injection deferred**: MCP → devdocs calls carry no trace id, so each
  search shows up in Langfuse as a devdocs-owned standalone trace (M3-verified behavior) rather
  than nesting under an MCP-session trace. Doing it properly requires MCP to own a parent trace
  (llmops-dashboard dependency + Langfuse creds in the MCP process) plus the devdocs LLMClient
  Protocol change its ark_client.py docstring anchors. Not needed for the M4 completion
  criterion. Note: with `retrieval_only=true` devdocs makes no LLM call, so MCP searches
  currently generate no devdocs trace at all.
