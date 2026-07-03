# READ THIS FIRST

This file is the source of truth for AI agents (Claude Code, Cursor, etc.) working
on **devcontext-mcp**. Read it end-to-end before touching code.

---

## What is this project?

`devcontext-mcp` is a **Model Context Protocol (MCP) server** that exposes the
capabilities of two upstream services as tools/resources to MCP clients
(Claude Code, Claude Desktop, Cursor):

1. **Auto Sentinel** (project 1) — incident triage / fix proposal agent.
2. **DevDocs RAG** (project 2) — code + docs semantic retrieval.

This is project **#3** in the AI Native Portfolio matrix. The MCP server is
the *integration surface*: it does not own intelligence — it forwards calls
to backend HTTP services and returns structured results.

---

## Phase 1 scope (this phase)

- MCP server runs over **stdio** transport (so Claude Code / Claude Desktop
  can spawn it).
- Registers **6 tools + 1 resource** (all mocked — no real backend calls).
- `mcp dev src/devcontext_mcp/server.py` lists all tools.
- `pytest` green, `ruff` + `mypy` clean.
- Out of scope: real backend integration, auth, streaming, sampling, prompts.

---

## Tech decisions (do not deviate without asking)

| Concern        | Decision                                                  |
|----------------|-----------------------------------------------------------|
| MCP SDK        | Anthropic official **`mcp`** Python SDK (`FastMCP`)       |
| Transport      | **stdio** (Phase 1). HTTP/SSE deferred.                   |
| Python         | **3.11+** required                                        |
| Type system    | Type hints **mandatory**; checked with mypy --strict      |
| Schemas        | **Pydantic v2** for all tool input/output models          |
| HTTP client    | **httpx** (async). Phase 1 clients return mocks.          |
| Lint           | **ruff** (format + check)                                 |
| Tests          | **pytest** + `pytest-asyncio` for async tools             |
| Package layout | `src/devcontext_mcp/` (PEP 621 / src layout)              |
| Config         | `pydantic-settings` + `.env` for backend URLs             |

---

## Tool & resource contracts

Each tool lives in its own file under `src/devcontext_mcp/tools/`. Input and
output models are Pydantic v2 `BaseModel`. The tool function is async, takes
the input model, and returns the output model. The server module wires each
into FastMCP via `@mcp.tool()`.

### From Auto Sentinel

#### 1. `analyze_error_log`
- **Purpose**: Diagnose a stack trace / log block.
- **Input**:
  - `log: str` — raw error log (required, non-empty)
- **Output**:
  - `category: Literal["runtime", "build", "infra", "config", "unknown"]`
  - `severity: Literal["low", "medium", "high", "critical"]`
  - `summary: str` — one-paragraph human-readable diagnosis
- **Errors**: empty `log` → `ValueError` (MCP returns tool error).
- **Mock**: returns `category="runtime"`, `severity="medium"`,
  `summary="Mock diagnosis: NullPointerException in user-service."`

#### 2. `search_past_incidents`
- **Purpose**: Retrieve historical incidents matching a free-text query.
- **Input**:
  - `query: str` (required)
  - `limit: int = 5` (1..50)
- **Output**: `incidents: list[Incident]` where `Incident` =
  `{ id: str, title: str, resolution: str }`
- **Errors**: `limit` out of range → validation error.
- **Mock**: returns 2 fixed incidents.

#### 3. `propose_fix`
- **Purpose**: Given an incident id, propose a fix plan.
- **Input**: `error_id: str`
- **Output**:
  - `fix_plan: str`
  - `risk_level: Literal["low", "medium", "high"]`
  - `code_diff: str` — unified diff (may be empty if no code change)
- **Mock**: returns canned plan + a 5-line diff.

### From DevDocs RAG

#### 4. `search_codebase`
- **Purpose**: Semantic search over indexed repos.
- **Input**:
  - `query: str` (required)
  - `repo: str | None = None` — optional repo filter (`owner/name`)
- **Output**: `results: list[CodeHit]` where `CodeHit` =
  `{ file: str, line: int, snippet: str, score: float }` (score in `[0,1]`)
- **Mock**: returns 3 hits with scores `0.91 / 0.84 / 0.72`.

#### 5. `find_examples`
- **Purpose**: Locate concrete usage examples of a specific API symbol.
- **Input**: `api_name: str` (e.g., `"requests.post"`, `"asyncio.gather"`)
- **Output**: `examples: list[Example]` where `Example` =
  `{ repo: str, file: str, code: str }`
- **Mock**: returns 2 examples.

#### 6. `summarize_pr`
- **Purpose**: Summarize a GitHub PR by URL.
- **Input**: `pr_url: str` — must match `https://github.com/.../pull/<n>`
- **Output**:
  - `summary: str`
  - `changed_files: list[str]`
  - `key_changes: list[str]`
- **Errors**: malformed URL → validation error.
- **Mock**: returns canned summary.

### MCP resource

#### 7. `get_session_context` (resource, URI `devcontext://session`)
- **Purpose**: Expose current-session metadata as an MCP **resource** (not
  a tool). Clients read it via `resources/read`.
- **Output**:
  - `recent_queries: list[str]`
  - `active_repo: str | None`
  - `user_preferences: dict[str, str]`
- **Mock**: returns 2 recent queries, `active_repo="meizhuixu/devcontext-mcp"`,
  `user_preferences={"language": "python", "verbosity": "concise"}`.

---

## Repository layout

```
devcontext-mcp/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── .github/workflows/ci.yml
├── src/devcontext_mcp/
│   ├── __init__.py
│   ├── config.py                # pydantic-settings; reads .env
│   ├── server.py                # FastMCP server entry — registers tools
│   ├── tools/                   # one file per tool, pure functions
│   │   ├── __init__.py
│   │   ├── analyze_error.py
│   │   ├── search_incidents.py
│   │   ├── propose_fix.py
│   │   ├── search_codebase.py
│   │   ├── find_examples.py
│   │   ├── summarize_pr.py
│   │   └── get_session_context.py
│   └── clients/                 # HTTP clients to backend services
│       ├── __init__.py
│       ├── auto_sentinel.py     # Phase 1: in-memory mock
│       └── devdocs.py           # Phase 1: in-memory mock
├── tests/
│   ├── test_smoke.py            # server constructs + lists 6 tools + 1 resource
│   └── test_tools.py            # one test per tool (happy path)
├── examples/
│   └── claude_desktop_config.json
├── CLAUDE.md
├── AGENTS.md
├── README.md
└── ARCHITECTURE.md
```

---

## Coding conventions

- **One tool per file**. Each file exports `INPUT`, `OUTPUT` Pydantic models
  and an `async def run(input: INPUT) -> OUTPUT` function. The server module
  imports and registers them — registration logic stays out of tool files
  so they remain unit-testable.
- **No business logic in `server.py`.** It is wiring only.
- **Clients are interfaces**: `AutoSentinelClient` and `DevDocsClient` are
  thin classes with async methods. Phase 1 implementations return canned
  data; Phase 2 will swap to real `httpx.AsyncClient` calls without changing
  the tool signatures.
- **Type hints are mandatory**. `mypy --strict` must pass.
- **Errors**: raise `ValueError` for invalid input; raise
  `RuntimeError` for upstream failures. Pydantic validation errors propagate
  naturally.
- **Logging**: `logging.getLogger(__name__)`. No `print` in source code.

---

## How to run / test

```bash
# install
uv sync --all-extras

# run server in dev mode (lists tools, opens MCP inspector)
uv run mcp dev src/devcontext_mcp/server.py

# tests
uv run pytest -q

# lint + types
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

---

## Roadmap (informational)

- **Phase 2**: replace mock clients with real `httpx` calls to Auto Sentinel
  and DevDocs RAG. Add retry/backoff.
- **Phase 3**: HTTP/SSE transport, OAuth, multi-tenant session resource.
- **Phase 4**: Cursor-specific tool packaging, telemetry, rate limiting.

---

## Docs maintenance (PROJECT.md / DEBT.md)

- `docs/PROJECT.md` is the project-context doc + status snapshot. Whenever a
  code change lands as a PR, update its "当前状态（快照）" section in the same
  PR (current phase, key outcomes).
- `DEBT.md` is the technical debt register: add an entry inline when new debt
  surfaces while coding; flip `[ ]` → `[X]` in the same commit that lands the
  fix (keep the entry, do not delete it).
- Authoritative progress stays in `git log` + `DEBT.md` — PROJECT.md is a
  snapshot / entry point, not the source of truth.
