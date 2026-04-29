# AGENTS.md

> One-page brief for AI coding agents (Claude Code, Cursor, etc.) working on
> this repo.

## What this repo is

`devcontext-mcp` is an **MCP server**. It does not host intelligence — it
forwards calls from MCP clients (Claude Desktop, Claude Code, Cursor) to two
upstream services (Auto Sentinel, DevDocs RAG) and returns structured Pydantic
results.

## Read these first

1. [`CLAUDE.md`](./CLAUDE.md) — full tool/resource contracts, conventions, and tech decisions.
2. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — protocol-level diagram of how an MCP call flows through the server.
3. [`README.md`](./README.md) — user-facing setup.

## Where to put things

- A new tool → its own file in `src/devcontext_mcp/tools/`, registered in `server.py`.
- A new backend → its own client class in `src/devcontext_mcp/clients/`.
- A new test → `tests/test_tools.py` (per-tool happy path) or a new file.
- A new config knob → `src/devcontext_mcp/config.py` + `.env.example`.

## What not to do

- Don't put business logic in `server.py`. It is wiring only.
- Don't add `print` statements — use `logging.getLogger(__name__)`.
- Don't bypass the Pydantic input/output models. Every tool has both.
- Don't break stdio. No `print` to stdout from anywhere reachable by the server runtime.

## Quality gates

Every PR must pass:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Mypy is in `--strict` mode. New code needs full type hints.
