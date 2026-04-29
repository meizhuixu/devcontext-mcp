# Architecture

This document describes how a single MCP call flows from an editor client to
a backend service through `devcontext-mcp`.

## High-level

```mermaid
flowchart LR
    subgraph Client["Editor / Assistant"]
        C1[Claude Desktop]
        C2[Claude Code]
        C3[Cursor]
    end

    subgraph Server["devcontext-mcp (FastMCP, Python)"]
        S1[server.py<br/>tool + resource registration]
        S2[tools/*.py<br/>pure async functions]
        S3[clients/*.py<br/>backend HTTP clients]
    end

    subgraph Backends["Backends (Phase 2)"]
        B1[Auto Sentinel<br/>HTTP service]
        B2[DevDocs RAG<br/>HTTP service]
    end

    C1 -- "MCP / stdio" --> S1
    C2 -- "MCP / stdio" --> S1
    C3 -- "MCP / stdio" --> S1
    S1 --> S2
    S2 --> S3
    S3 -- "httpx async" --> B1
    S3 -- "httpx async" --> B2
```

## Sequence: a `search_codebase` call

```mermaid
sequenceDiagram
    autonumber
    participant Cl as Claude Desktop
    participant Sv as devcontext-mcp
    participant T as tools/search_codebase.py
    participant Cli as clients/devdocs.py
    participant BE as DevDocs RAG (Phase 2)

    Cl->>Sv: tools/call { name: "search_codebase", args: {query, repo} }
    Sv->>T: run(SearchCodebaseInput(...))
    T->>Cli: search_codebase(query, repo)
    alt Phase 1 (mock)
        Cli-->>T: canned [CodeHit, ...]
    else Phase 2 (http)
        Cli->>BE: POST /search { query, repo }
        BE-->>Cli: 200 { results: [...] }
        Cli-->>T: parsed [CodeHit, ...]
    end
    T-->>Sv: SearchCodebaseOutput
    Sv-->>Cl: tools/call result (JSON)
```

## Layering rules

| Layer       | Knows about                              | Does not know about               |
|-------------|------------------------------------------|-----------------------------------|
| `server.py` | tools, clients, MCP SDK                  | HTTP wire format                  |
| `tools/*`   | clients, Pydantic models                 | MCP SDK, transport                |
| `clients/*` | httpx, backend wire format               | tools, MCP SDK                    |

This separation lets us:

- Unit-test tools with a fake client (no MCP runtime needed).
- Swap mock clients for real HTTP without touching tool signatures.
- Swap stdio for HTTP/SSE transport in Phase 3 without touching tools or clients.

## Why FastMCP

`FastMCP` (the high-level wrapper in the `mcp` SDK) auto-derives JSON Schema
from typed Python signatures. We pair it with explicit Pydantic models inside
each tool because:

1. We want the **input/output contract** to be testable independently of the
   server, and reusable for OpenAPI generation in Phase 2.
2. We want **strict validation** (`min_length`, regex, enum) at the boundary,
   not relying on the LLM to send well-formed JSON.

## Configuration flow

```
.env  ──▶  pydantic-settings (config.py)  ──▶  build_server(settings)
                                                  │
                                                  ▼
                                          AutoSentinelClient(url, mock=...)
                                          DevDocsClient(url, mock=...)
```

`backend_mode=mock` (Phase 1) makes the client classes return canned data.
`backend_mode=http` (Phase 2) will route through real `httpx.AsyncClient` calls.
