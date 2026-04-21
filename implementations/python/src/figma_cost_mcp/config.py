import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    figma_access_token: str | None  # PAT — overrides OAuth if set
    figma_scim_token: str
    figma_org_id: str
    figma_team_id: str | None = None
    figma_client_id: str | None = None      # OAuth app Client ID
    figma_client_secret: str | None = None  # OAuth app Client Secret
    figma_redirect_uri: str | None = None   # OAuth redirect URI registered in your app
    figma_callback_port: int = 8080         # Local port for automated OAuth callback server

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            figma_access_token=os.environ.get("FIGMA_ACCESS_TOKEN") or None,
            figma_scim_token=os.environ.get("FIGMA_SCIM_TOKEN", ""),
            figma_org_id=os.environ.get("FIGMA_ORG_ID", ""),
            figma_team_id=os.environ.get("FIGMA_TEAM_ID"),
            figma_client_id=os.environ.get("FIGMA_CLIENT_ID"),
            figma_client_secret=os.environ.get("FIGMA_CLIENT_SECRET"),
            figma_redirect_uri=os.environ.get("FIGMA_REDIRECT_URI"),
            figma_callback_port=int(os.environ.get("FIGMA_CALLBACK_PORT", "8080")),
        )
