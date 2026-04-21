import logging
import sys

from ._mcp import mcp
from .tools import (  # noqa: F401 — side-effect: registers tools
    activity_logs,
    analytics,
    auth,
    comments,
    components,
    dev_resources,
    files,
    me,
    payments,
    projects,
    scim,
    teams,
    variables,
    webhooks,
)

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
