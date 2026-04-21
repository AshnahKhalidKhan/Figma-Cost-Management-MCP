from pydantic import BaseModel

# Supported Figma webhook event types
WEBHOOK_EVENT_TYPES = frozenset({
    "FILE_UPDATE",
    "FILE_VERSION_UPDATE",
    "FILE_DELETE",
    "LIBRARY_PUBLISH",
    "FILE_COMMENT",
})

WEBHOOK_STATUS_ACTIVE = "ACTIVE"
WEBHOOK_STATUS_PAUSED = "PAUSED"


class Webhook(BaseModel):
    id: str
    team_id: str
    event_type: str
    client_id: str | None = None
    endpoint: str
    passcode: str | None = None
    status: str
    description: str | None = None


class WebhookRequest(BaseModel):
    id: str
    webhook_id: str
    client_id: str | None = None
    created_at: str
    sent_at: str | None = None
    error: str | None = None
    error_reason: str | None = None
    response_status: int | None = None


class TeamWebhooksResponse(BaseModel):
    webhooks: list[Webhook]


class WebhookRequestsResponse(BaseModel):
    requests: list[WebhookRequest]
