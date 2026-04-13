import logging
import sys

from ._mcp import mcp
from .tools import activity_logs, auth, payments, scim  # noqa: F401 — side-effect: registers tools

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
