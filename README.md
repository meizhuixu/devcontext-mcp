# DevContext MCP

> A Model Context Protocol server that gives Claude Code, Claude Desktop, and
> Cursor first-class access to your **incident triage** and **codebase
> retrieval** backends.

[![CI](https://github.com/meizhuixu/devcontext-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/meizhuixu/devcontext-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Status

✅ Phase 1 complete — integrated and verified in Claude Code (Opus) with 6 tools + 1 resource live.

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

Phase 1 ships canned mock responses inside the server so Claude Code (or any
other MCP client) can talk to it without any backend running. See
[ARCHITECTURE.md](./ARCHITECTURE.md) for the protocol-level diagram.

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

## How to use with Claude Code

This is the verified, recommended path. Phase 1 ships in mock mode so the
6 tools + 1 resource respond without any backend running.

1. Make sure `uv` and this repo are installed locally.
2. Register the server with Claude Code (user scope, mock backend):

   ```bash
   claude mcp add devcontext \
     -s user \
     -e DEVCONTEXT_BACKEND_MODE=mock \
     -- /opt/homebrew/bin/uv \
     --directory <ABSOLUTE_PATH_TO_REPO> \
     run devcontext-mcp
   ```

   Replace `<ABSOLUTE_PATH_TO_REPO>` with the absolute path on your machine
   (e.g. `/Users/yourname/Repo/devcontext-mcp`). On Linux or non-Homebrew
   setups, swap `/opt/homebrew/bin/uv` for the output of `which uv`.

3. Verify inside Claude Code:

   ```
   /mcp
   ```

   You should see something like:

   ```
   devcontext  ✔ connected   Capabilities: tools · resources   Tools: 6 tools
   ```

4. Try it with a natural-language prompt:

   > Use the `analyze_error_log` tool from devcontext to diagnose this:
   > `NullPointerException at User.java:42 ...`

   Claude Code will pick the tool, call it over MCP, and turn the structured
   mock response into a natural-language diagnosis and fix plan.

If you don't see the server, run `claude mcp list` to confirm it was
registered, and check that `<ABSOLUTE_PATH_TO_REPO>` points at the repo root
(the directory containing `pyproject.toml`).

## How to use with Claude Desktop (alternative)

Claude Desktop is supported as a secondary path; the integration is the same
but configured via JSON instead of `claude mcp add`.

1. Open (or create) the Claude Desktop config:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
2. Merge the contents of [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json)
   into your existing config (under the top-level `mcpServers` key), replacing
   the `--directory` value with the absolute path to this repo.
3. Quit Claude Desktop completely (`Cmd+Q`) and re-open it.
4. In any chat, click the tools icon — you should see the 6 tools + 1 resource.

If a tool doesn't show up, check the Claude Desktop log:

```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

---

## Live Demo

Verified end-to-end in Claude Code (Opus) — `/mcp` shows the server
connected, tools are discovered, and a natural-language prompt resolves to a
real MCP tool call against the mock backend.

<!-- TODO: replace the three placeholder filenames below with the actual
     files committed under docs/screenshots/. Captions can stay as-is. -->

![/mcp connected — 6 tools + 1 resource](docs/screenshots/TODO-1.png)

![Tool discovery — devcontext tools listed in Claude Code](docs/screenshots/TODO-2.png)

![Natural-language prompt → analyze_error_log → diagnosis](docs/screenshots/TODO-3.png)

---

## Status & Roadmap

- ✅ **Phase 1 (current)** — server scaffolded, 6 tools + 1 resource, mock
  responses, CI green, integration verified live in Claude Code (Opus);
  Claude Desktop also supported.
- 🚧 **Phase 2** — replace mock clients with real `httpx` calls to Auto
  Sentinel and DevDocs RAG. Add retry/backoff and structured logging.
- 🔮 **Phase 3** — HTTP/SSE transport, OAuth, multi-tenant session resource.
- 🔮 **Phase 4** — Cursor-specific packaging, telemetry, rate limiting.

---

## License

MIT
