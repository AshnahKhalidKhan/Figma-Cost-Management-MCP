import pytest
import httpx
import respx

from figma_cost_mcp.http_client import FIGMA_API_BASE, FIGMA_SCIM_BASE, RateLimitedClient


@pytest.fixture
def rest_client() -> RateLimitedClient:
    return RateLimitedClient(FIGMA_API_BASE, token="test-access-token")


@pytest.fixture
def scim_client() -> RateLimitedClient:
    return RateLimitedClient(FIGMA_SCIM_BASE, token="test-scim-token")
