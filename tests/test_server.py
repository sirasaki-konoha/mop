from __future__ import annotations

import asyncio

from orchestrator.server import configure_server_transport, get_server_info


def test_get_server_info_reports_identity_and_registered_tools():
    info = asyncio.run(get_server_info())

    assert info["name"] == "mop"
    assert info["version"] == "0.1.0"
    assert info["transport"] == "stdio"
    assert info["live_messaging"] is False
    assert info["state_scope"] == "server_process"
    assert info["tool_count"] == len(info["tools"])
    assert {
        "decompose_task",
        "get_agent_inbox",
        "get_server_info",
        "list_registered_agents",
        "register_agent",
        "wait_for_agent_message",
    }.issubset(info["tools"])


def test_get_server_info_reports_streamable_http_mode():
    configure_server_transport("streamable-http")
    try:
        info = asyncio.run(get_server_info())
    finally:
        configure_server_transport("stdio")

    assert info["transport"] == "streamable-http"
    assert info["live_messaging"] is True
