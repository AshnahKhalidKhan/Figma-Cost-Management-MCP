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
- **Teams** (`GET /v1/teams/{team_id}/members`) — member roles and billed seat analysis; available on Pro and above
- **Payments** (`GET /v1/payments`) — plugin/widget payment validation
- **SCIM** (`/scim/v2/Users`, `/scim/v2/Groups`) — user and group management for billing; **Enterprise plan required**
- **Activity Logs** (`GET /v1/activity_logs`) — billing and user management events only; **Organization/Enterprise plan required**

## Plan Compatibility
- **Pro plan**: Teams API only. SCIM and Activity Logs will return 403.
- **Organization/Enterprise plan**: All APIs available.

## Rate Limiting
Figma uses a leaky bucket algorithm. On 429 responses:
1. Read the `Retry-After` response header
2. Wait that many seconds
3. Retry with exponential backoff as fallback
4. Max 3 retries total, then raise

## Authentication
- **REST API (Teams, Payments, Activity Logs)**: Personal Access Token via `FIGMA_ACCESS_TOKEN` env var. Create at Figma Settings → Personal access tokens.
- **SCIM API (Users, Groups)**: Separate `FIGMA_SCIM_TOKEN` from env — Enterprise plans only.
- **`FIGMA_TEAM_ID`**: Required for Teams API. Find in the Figma URL: `figma.com/files/team/{TEAM_ID}`.
- **`FIGMA_ORG_ID`**: Required for Activity Logs API. Find in Figma Admin → Settings.
- No OAuth browser flow — all credentials are static env vars loaded via `python-dotenv`.

## Python Implementation
- Location: `implementations/python/`
- Python 3.10+, `uv` for package management
- FastMCP (`mcp[cli]>=1.2.0`) for the server
- **NEVER write to stdout in STDIO mode** — use `logging` (writes to stderr) only
- Run tests: `cd implementations/python && uv run pytest`
- Run server: `cd implementations/python && uv run python -m figma_cost_mcp`
- Install dev deps: `cd implementations/python && uv sync --extra dev`
