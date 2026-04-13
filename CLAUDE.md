# Figma Cost Management MCP

## Project Purpose
MCP server for Figma subscription cost/billing management, analysis, and associated user management.
**No other Figma functionality is in scope.**

## Multi-Language Rule
**IMPORTANT: This project supports the MCP in C#, Java, Java Spring Boot, Rust, and Python simultaneously.**
- All implementations must expose identical tools with identical schemas.
- When adding, removing, or changing any tool, ALL language implementations must be updated.
- Currently implemented: Python (`implementations/python/`)
- Pending: C# (`implementations/csharp/`), Java (`implementations/java/`), Java Spring Boot (`implementations/java-springboot/`), Rust (`implementations/rust/`)

## Engineering Standards
- **TDD**: Tests are written before or alongside implementation. All tools require unit + integration tests.
- **SOLID**: Single responsibility per module. Depend on abstractions. Open for extension, closed for modification.
- **Lean**: No unused code. No speculative abstractions. Minimal dependencies.

## Figma APIs in Scope
- **Payments** (`GET /v1/payments`) — subscription/billing validation
- **SCIM** (`/scim/v2/Users`, `/scim/v2/Groups`) — user and group management for billing
- **Activity Logs** (`GET /v1/activity_logs`) — billing and user management events only

## Rate Limiting
Figma uses a leaky bucket algorithm. On 429 responses:
1. Read the `Retry-After` response header
2. Wait that many seconds
3. Retry with exponential backoff as fallback
4. Max 3 retries total, then raise

## Authentication
- **REST API (Payments, Activity Logs)**: OAuth 2.0 authorization code flow using `FIGMA_CLIENT_ID` + `FIGMA_CLIENT_SECRET`. Tokens stored at `~/.figma-cost-mcp/tokens.json`, auto-refreshed (90-day expiry).
- **SCIM API (Users, Groups)**: Separate `FIGMA_SCIM_TOKEN` from env — no OAuth scope exists for SCIM.
- **PAT override**: If `FIGMA_ACCESS_TOKEN` is set, it overrides OAuth for REST API calls (useful for testing).
- Figma only supports authorization code flow — no client credentials grant.

## Python Implementation
- Location: `implementations/python/`
- Python 3.10+, `uv` for package management
- FastMCP (`mcp[cli]>=1.2.0`) for the server
- **NEVER write to stdout in STDIO mode** — use `logging` (writes to stderr) only
- Run tests: `cd implementations/python && uv run pytest`
- Run server: `cd implementations/python && uv run python -m figma_cost_mcp`
- Install dev deps: `cd implementations/python && uv sync --extra dev`
