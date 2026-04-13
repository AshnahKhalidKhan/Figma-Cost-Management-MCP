import pytest
import httpx
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, RateLimitedClient


@pytest.mark.asyncio
async def test_raises_without_token_or_provider() -> None:
    with pytest.raises(ValueError, match="Either token or token_provider"):
        RateLimitedClient(FIGMA_API_BASE)


@pytest.mark.asyncio
async def test_get_success(rest_client: RateLimitedClient) -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        result = await rest_client.get("/v1/payments")
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_retries_on_429_then_succeeds(rest_client: RateLimitedClient) -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        result = await rest_client.get("/v1/payments")
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_raises_after_max_retries(rest_client: RateLimitedClient) -> None:
    with respx.mock:
        respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "0"})
        )
        with pytest.raises(RuntimeError, match="Max retries exceeded"):
            await rest_client.get("/v1/payments")


@pytest.mark.asyncio
async def test_delete_returns_none_on_204(rest_client: RateLimitedClient) -> None:
    with respx.mock:
        respx.delete(f"{FIGMA_API_BASE}/v1/users/123").mock(
            return_value=httpx.Response(204)
        )
        result = await rest_client.delete("/v1/users/123")
    assert result is None


@pytest.mark.asyncio
async def test_post_sends_json(rest_client: RateLimitedClient) -> None:
    with respx.mock:
        route = respx.post(f"{FIGMA_API_BASE}/v1/resource").mock(
            return_value=httpx.Response(201, json={"id": "new-id"})
        )
        result = await rest_client.post("/v1/resource", json={"name": "test"})
    assert result == {"id": "new-id"}
    assert b'"name"' in route.calls[0].request.content
    assert b'"test"' in route.calls[0].request.content


@pytest.mark.asyncio
async def test_patch_sends_json(rest_client: RateLimitedClient) -> None:
    with respx.mock:
        respx.patch(f"{FIGMA_API_BASE}/v1/resource/1").mock(
            return_value=httpx.Response(200, json={"updated": True})
        )
        result = await rest_client.patch("/v1/resource/1", json={"active": False})
    assert result == {"updated": True}


@pytest.mark.asyncio
async def test_authorization_header_sent(rest_client: RateLimitedClient) -> None:
    with respx.mock:
        route = respx.get(f"{FIGMA_API_BASE}/v1/payments").mock(
            return_value=httpx.Response(200, json={})
        )
        await rest_client.get("/v1/payments")
    assert route.calls[0].request.headers["Authorization"] == "Bearer test-access-token"
