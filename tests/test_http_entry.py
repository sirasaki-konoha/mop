from __future__ import annotations

import pytest

from http_entry import build_parser


def test_http_entry_defaults_to_local_shared_endpoint():
    args = build_parser().parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.path == "/mcp"


@pytest.mark.parametrize("port", ["0", "65536"])
def test_http_entry_rejects_invalid_ports(port):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--port", port])


def test_http_entry_requires_absolute_path():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--path", "mcp"])
