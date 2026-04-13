# Figma Cost Management MCP

An MCP (Model Context Protocol) server for Figma subscription **cost and billing management** and associated **user management**. No other Figma functionality is in scope.

## Capabilities

| Domain | Tools |
|--------|-------|
| **Payments** | `validate_payment_by_token`, `validate_payment_by_user` |
| **User Management** | `list_figma_users`, `get_figma_user`, `create_figma_user`, `update_figma_user`, `deactivate_figma_user`, `change_figma_user_seat`, `delete_figma_user` |
| **Group Management** | `list_figma_groups`, `get_figma_group`, `create_figma_group`, `add_group_members`, `remove_group_members`, `delete_figma_group` |
| **Activity Logs** | `get_billing_activity_logs`, `get_user_management_activity_logs`, `get_activity_logs` |

## Implementations

| Language | Status | Location |
|----------|--------|----------|
| Python | Ready | `implementations/python/` |
| C# | Pending | `implementations/csharp/` |
| Java | Pending | `implementations/java/` |
| Java Spring Boot | Pending | `implementations/java-springboot/` |
| Rust | Pending | `implementations/rust/` |

## Python Setup

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

### Install
```bash
cd implementations/python
uv sync --extra dev
```

### Configure
```bash
cp .env.example .env
# Edit .env with your Figma credentials
```

Required environment variables:
- `FIGMA_ACCESS_TOKEN` — Personal access token (for Payments + Activity Logs)
- `FIGMA_SCIM_TOKEN` — SCIM API token (for User/Group management)
- `FIGMA_ORG_ID` — Figma organization ID

### Run Tests
```bash
cd implementations/python
uv run pytest
```

### Run Server
```bash
cd implementations/python
uv run python -m figma_cost_mcp
```

## MCP Configuration

Add to your Claude Desktop / MCP client config (`.mcp.json` is provided at the project root):

```json
{
  "mcpServers": {
    "figma-cost-mcp-python": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "figma_cost_mcp"],
      "cwd": "implementations/python",
      "env": {
        "FIGMA_ACCESS_TOKEN": "your_token",
        "FIGMA_SCIM_TOKEN": "your_scim_token",
        "FIGMA_ORG_ID": "your_org_id"
      }
    }
  }
}
```

## Architecture

```
implementations/python/
├── src/figma_cost_mcp/
│   ├── _mcp.py            # FastMCP instance
│   ├── server.py          # Entry point
│   ├── config.py          # Config from env vars
│   ├── http_client.py     # Rate-limited httpx wrapper (handles 429 + Retry-After)
│   ├── models/            # Pydantic models (payments, scim, activity_logs)
│   └── tools/             # MCP tools (payments, scim, activity_logs)
└── tests/                 # pytest test suite
```

## Rate Limiting

Figma uses a leaky bucket algorithm. The HTTP client automatically retries on 429 responses using the `Retry-After` header, with exponential backoff fallback and a maximum of 3 retries.
