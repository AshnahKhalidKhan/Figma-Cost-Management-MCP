import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    figma_client_id: str
    figma_client_secret: str
    figma_redirect_uri: str
    figma_scim_token: str
    figma_org_id: str
    # Optional: if set, bypasses OAuth for REST API calls (useful for testing or PAT-only setups)
    figma_access_token: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            figma_client_id=os.environ["FIGMA_CLIENT_ID"],
            figma_client_secret=os.environ["FIGMA_CLIENT_SECRET"],
            figma_redirect_uri=os.environ["FIGMA_REDIRECT_URI"],
            figma_scim_token=os.environ["FIGMA_SCIM_TOKEN"],
            figma_org_id=os.environ["FIGMA_ORG_ID"],
            figma_access_token=os.environ.get("FIGMA_ACCESS_TOKEN"),
        )
