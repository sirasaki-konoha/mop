from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from orchestrator.server import configure_server_transport, mcp

DEFAULT_HOST = os.environ.get("MOP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("MOP_PORT", "8765"))
DEFAULT_PATH = os.environ.get("MOP_PATH", "/mcp")


def _port(value: str) -> int:
    port = int(value)
    if port < 1 or port > 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _path(value: str) -> str:
    if not value.startswith("/"):
        raise argparse.ArgumentTypeError("path must start with '/'")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run MOP as a shared Streamable HTTP MCP server.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=_port, default=DEFAULT_PORT)
    parser.add_argument("--path", type=_path, default=DEFAULT_PATH)
    parser.add_argument("--log-level", default="info")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logger = logging.getLogger(__name__)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        logger.warning("MOP has no HTTP authentication; bind only to a trusted network")

    configure_server_transport("streamable-http")
    logger.info(
        "Starting shared MOP server at http://%s:%d%s",
        args.host,
        args.port,
        args.path,
    )
    try:
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path,
            log_level=args.log_level,
            stateless_http=False,
        )
    except Exception:
        logger.exception("Shared MOP HTTP server stopped unexpectedly")
        raise


if __name__ == "__main__":
    main()
