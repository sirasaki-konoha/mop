from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from orchestrator.server import mcp


def main() -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting Multi-Agent MCP Orchestrator server")
    mcp.run()


if __name__ == "__main__":
    main()
