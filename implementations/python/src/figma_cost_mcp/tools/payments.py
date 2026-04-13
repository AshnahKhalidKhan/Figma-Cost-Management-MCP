import logging
from typing import Annotated

from .._mcp import mcp
from ..config import Config
from ..http_client import RateLimitedClient, make_rest_client
from ..models.payments import PaymentInformation
from ..oauth import get_oauth_manager

logger = logging.getLogger(__name__)

_RESOURCE_TYPE_TO_PARAM = {
    "PLUGIN": "plugin_id",
    "WIDGET": "widget_id",
    "COMMUNITY_FILE": "community_file_id",
}

_client: RateLimitedClient | None = None


def _get_client() -> RateLimitedClient:
    global _client
    if _client is None:
        config = Config.from_env()
        if config.figma_access_token:
            _client = make_rest_client(token=config.figma_access_token)
        else:
            _client = make_rest_client(token_provider=get_oauth_manager().get_valid_token)
    return _client


def _set_client(client: RateLimitedClient | None) -> None:
    global _client
    _client = client


@mcp.tool()
async def validate_payment_by_token(
    plugin_payment_token: Annotated[str, "Short-lived token from getPluginPaymentTokenAsync()"],
) -> dict:
    """Validate a Figma plugin/widget purchase using a plugin payment token.

    Returns payment status (PAID, UNPAID, TRIAL) and purchase date.
    Use this when validating payments from within a plugin or widget context.
    """
    data = await _get_client().get("/v1/payments", params={"plugin_payment_token": plugin_payment_token})
    return PaymentInformation.model_validate(data).model_dump()


@mcp.tool()
async def validate_payment_by_user(
    user_id: Annotated[int, "Figma user ID — use check_figma_auth_status to get the authenticated user's ID"],
    resource_type: Annotated[str, "One of: PLUGIN, WIDGET, COMMUNITY_FILE"],
    resource_id: Annotated[int, "ID of the plugin, widget, or community file"],
) -> dict:
    """Validate a Figma plugin/widget/community file purchase for a specific user.

    Returns payment status (PAID, UNPAID, TRIAL) and purchase details.
    You can only query resources you own. Authenticate first with start_figma_authorization.
    """
    param_name = _RESOURCE_TYPE_TO_PARAM.get(resource_type.upper())
    if not param_name:
        raise ValueError(
            f"Invalid resource_type '{resource_type}'. Must be one of: {', '.join(_RESOURCE_TYPE_TO_PARAM)}"
        )
    data = await _get_client().get(
        "/v1/payments",
        params={"user_id": user_id, param_name: resource_id},
    )
    return PaymentInformation.model_validate(data).model_dump()
