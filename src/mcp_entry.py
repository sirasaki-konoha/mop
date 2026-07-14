from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from orchestrator.server import configure_server_transport, mcp


def main() -> None:
    logger = logging.getLogger(__name__)
    configure_server_transport("stdio")
    logger.info("Starting MOP stdio server")
    mcp.run()


if __name__ == "__main__":
    main()
