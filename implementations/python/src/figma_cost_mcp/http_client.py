import asyncio
import logging
from typing import Any, Awaitable, Callable

import httpx

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
FIGMA_API_BASE = "https://api.figma.com"
FIGMA_SCIM_BASE = "https://www.figma.com/scim/v2"

TokenProvider = Callable[[], Awaitable[str]]


class RateLimitedClient:
    """Async HTTP client with automatic rate-limit retry using Retry-After header.

    Accepts either a static token string or an async token_provider callable.
    token_provider is called on every request so OAuth tokens are always fresh.
    """

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        token_provider: TokenProvider | None = None,
    ) -> None:
        if token is None and token_provider is None:
            raise ValueError("Either token or token_provider must be provided")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._token_provider = token_provider

    async def _auth_header(self) -> str:
        if self._token_provider:
            return f"Bearer {await self._token_provider()}"
        return f"Bearer {self._token}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any] | None:
        url = f"{self._base_url}/{path.lstrip('/')}"
        for attempt in range(_MAX_RETRIES):
            headers = {
                "Authorization": await self._auth_header(),
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method, url, headers=headers, timeout=30.0, **kwargs
                )
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 2 ** attempt))
                logger.warning("Rate limited; retrying in %ds (attempt %d/%d)", wait, attempt + 1, _MAX_RETRIES)
                await asyncio.sleep(wait)
                continue
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        raise RuntimeError(f"Max retries exceeded due to rate limiting on {method} {path}")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", path, json=json)

    async def patch(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> None:
        await self._request("DELETE", path)


def make_rest_client(
    token: str | None = None,
    token_provider: TokenProvider | None = None,
) -> RateLimitedClient:
    return RateLimitedClient(FIGMA_API_BASE, token=token, token_provider=token_provider)


def make_scim_client(token: str) -> RateLimitedClient:
    return RateLimitedClient(FIGMA_SCIM_BASE, token=token)
