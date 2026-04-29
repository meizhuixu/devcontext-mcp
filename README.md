# DevContext MCP

> A Model Context Protocol server that gives Claude Code, Claude Desktop, and
> Cursor first-class access to your **incident triage** and **codebase
> retrieval** backends.

[![CI](https://github.com/meizhuixu/devcontext-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/meizhuixu/devcontext-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Why

AI coding assistants are only as smart as the context they can pull in. Two
systems already do the heavy lifting for me:

- **Auto Sentinel** — diagnoses errors, retrieves past incidents, proposes fixes.
- **DevDocs RAG** — semantic search over indexed code, examples, and PRs.

Both are HTTP services. Claude Desktop / Claude Code / Cursor can't call them
directly — but they all speak **MCP**. `devcontext-mcp` is the bridge: it
exposes those backends as a small set of tools and one session resource that
any MCP-compatible editor can consume.

This is **project #3** in my AI Native Portfolio matrix — the integration
surface that ties the rest together.

---

## Architecture

```
┌────────────────────┐    stdio       ┌──────────────────────┐    HTTP    ┌──────────────────┐
│ Claude Desktop /   │ ─────────────▶ │  devcontext-mcp      │ ─────────▶ │ Auto Sentinel    │
│ Claude Code /      │   MCP JSON-RPC │  (FastMCP, Python)   │            │ (Phase 2)        │
│ Cursor             │ ◀───────────── │                      │ ─────────▶ │ DevDocs RAG      │
└────────────────────┘                └──────────────────────┘            │ (Phase 2)        │
                                                                          └──────────────────┘
```

Phase 1 ships canned mock responses inside the server so Claude Desktop can
talk to it without any backend running. See [ARCHITECTURE.md](./ARCHITECTURE.md)
for the protocol-level diagram.

---

## Tech Stack

| Layer       | Choice                                                  |
|-------------|---------------------------------------------------------|
| Protocol    | Model Context Protocol (Anthropic spec)                 |
| Server SDK  | `mcp` (official Python SDK), `FastMCP`                  |
| Transport   | stdio (Phase 1)                                         |
| Schemas     | Pydantic v2 (input + output models per tool)            |
| HTTP client | httpx (async)                                           |
| Lint / Type | ruff, mypy --strict                                     |
| Tests       | pytest + pytest-asyncio                                 |
| Packaging   | hatchling, PEP 621 / src layout                         |

---

## Tools & Resources

| #  | Kind     | Name                  | Source         |
|----|----------|-----------------------|----------------|
| 1  | tool     | `analyze_error_log`   | Auto Sentinel  |
| 2  | tool     | `search_past_incidents` | Auto Sentinel |
| 3  | tool     | `propose_fix`         | Auto Sentinel  |
| 4  | tool     | `search_codebase`     | DevDocs RAG    |
| 5  | tool     | `find_examples`       | DevDocs RAG    |
| 6  | tool     | `summarize_pr`        | DevDocs RAG    |
| 7  | resource | `devcontext://session` | Local        |

Full schemas (input/output, error semantics) live in [CLAUDE.md](./CLAUDE.md).

---

## Quick start

```bash
# 1. install
uv sync --all-extras

# 2. tests + lint
uv run pytest -q
uv run ruff check .
uv run mypy src

# 3. dev mode (opens MCP Inspector — needs Node.js)
uv run mcp dev src/devcontext_mcp/server.py

# 4. run as a regular stdio server
uv run devcontext-mcp
```

---

## How to use with Claude Desktop

1. Make sure `uv` and this repo are installed locally.
2. Open (or create) the Claude Desktop config:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
3. Merge the contents of [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your existing config (under the top-level `mcpServers` key). The
   important entry is:

   ```json
   {
     "mcpServers": {
       "devcontext": {
         "command": "uv",
         "args": [
           "--directory",
           "/absolute/path/to/devcontext-mcp",
           "run",
           "devcontext-mcp"
         ]
       }
     }
   }
   ```

   Replace `/absolute/path/to/devcontext-mcp` with the absolute path on your
   machine (e.g. `/Users/yourname/Repo/devcontext-mcp`).
4. Quit Claude Desktop completely (`Cmd+Q`) and re-open it.
5. In any chat, click the tools icon — you should see the 6 `devcontext-*`
   tools and the `devcontext://session` resource.

If a tool doesn't show up, check the Claude Desktop log:

```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

## How to use with Claude Code

Claude Code reads MCP servers from `~/.claude/mcp_servers.json` (or the
project-local `.mcp.json`). Add the same block as above. Restart with
`claude mcp list` to verify.

---

## Status & Roadmap

- ✅ **Phase 1 (current)** — server scaffolded, 6 tools + 1 resource, mock
  responses, CI green, Claude Desktop integration verified.
- 🚧 **Phase 2** — replace mock clients with real `httpx` calls to Auto
  Sentinel and DevDocs RAG. Add retry/backoff and structured logging.
- 🔮 **Phase 3** — HTTP/SSE transport, OAuth, multi-tenant session resource.
- 🔮 **Phase 4** — Cursor-specific packaging, telemetry, rate limiting.

---

## License

MIT
