"""Local HTTP callback server for the Figma OAuth automated flow.

Starts a temporary server on localhost, waits for the browser redirect from
Figma, parses the code and state from the query string, and shuts down cleanly.
"""
import asyncio
import socket
from urllib.parse import parse_qs, urlparse

_SUCCESS_HTML = (
    b"<!DOCTYPE html><html><head><meta charset='utf-8'>"
    b"<title>Figma Authorization</title></head>"
    b"<body style='font-family:sans-serif;text-align:center;padding:4rem'>"
    b"<h2>&#10003; Authorization Successful</h2>"
    b"<p>You can close this tab and return to Claude.</p>"
    b"</body></html>"
)

_ERROR_HTML = (
    b"<!DOCTYPE html><html><head><meta charset='utf-8'>"
    b"<title>Figma Authorization</title></head>"
    b"<body style='font-family:sans-serif;text-align:center;padding:4rem'>"
    b"<h2>&#10007; Missing Parameters</h2>"
    b"<p>The redirect did not include a code or state. Please try again.</p>"
    b"</body></html>"
)


def find_free_port() -> int:
    """Return an available TCP port on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def capture_oauth_callback(port: int, timeout: int = 120) -> tuple[str, str]:
    """Start a local HTTP server and block until Figma redirects the browser to it.

    Returns (code, state) extracted from the redirect URL query string.
    Raises TimeoutError if no redirect arrives within *timeout* seconds.
    Raises ValueError if the redirect is missing the expected parameters.
    """
    code: str | None = None
    state: str | None = None
    done = asyncio.Event()

    async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal code, state
        try:
            raw = await reader.read(4096)
            request_line = raw.decode("utf-8", errors="replace").split("\r\n")[0]
            if " " in request_line:
                path = request_line.split(" ", 2)[1]
                qs = parse_qs(urlparse(f"http://x{path}").query)
                code = (qs.get("code") or [None])[0]
                state = (qs.get("state") or [None])[0]
            body = _SUCCESS_HTML if (code and state) else _ERROR_HTML
            header = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode()
            writer.write(header + body)
            await writer.drain()
        finally:
            writer.close()
            done.set()

    server = await asyncio.start_server(_handle, "127.0.0.1", port)
    async with server:
        try:
            await asyncio.wait_for(done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"No authorization callback received within {timeout} seconds. "
                "Make sure you opened the browser URL and approved the request."
            )

    if not code or not state:
        raise ValueError(
            "Authorization callback was missing 'code' or 'state' query parameters."
        )

    return code, state
