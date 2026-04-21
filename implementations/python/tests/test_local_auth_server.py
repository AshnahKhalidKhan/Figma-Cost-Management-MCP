import asyncio

import httpx
import pytest

from figma_cost_mcp.local_auth_server import capture_oauth_callback, find_free_port


def test_find_free_port_returns_integer() -> None:
    port = find_free_port()
    assert isinstance(port, int)
    assert 1024 < port < 65536


def test_find_free_port_is_actually_free() -> None:
    import socket
    port = find_free_port()
    # Should be able to bind immediately after finding it
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))


@pytest.mark.asyncio
async def test_capture_callback_returns_code_and_state() -> None:
    port = find_free_port()

    async def send_redirect() -> None:
        await asyncio.sleep(0.05)
        async with httpx.AsyncClient() as client:
            await client.get(f"http://127.0.0.1:{port}/?code=test-code&state=test-state")

    asyncio.create_task(send_redirect())
    code, state = await capture_oauth_callback(port, timeout=5)
    assert code == "test-code"
    assert state == "test-state"


@pytest.mark.asyncio
async def test_capture_callback_times_out() -> None:
    port = find_free_port()
    with pytest.raises(TimeoutError, match="No authorization callback"):
        await capture_oauth_callback(port, timeout=1)


@pytest.mark.asyncio
async def test_capture_callback_raises_on_missing_params() -> None:
    port = find_free_port()

    async def send_bad_redirect() -> None:
        await asyncio.sleep(0.05)
        async with httpx.AsyncClient() as client:
            await client.get(f"http://127.0.0.1:{port}/")  # no code or state

    asyncio.create_task(send_bad_redirect())
    with pytest.raises(ValueError, match="missing 'code' or 'state'"):
        await capture_oauth_callback(port, timeout=5)
