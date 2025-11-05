"""FastMCP server exposing minimal RSS‑feed discovery tools.

Available tools:
* ``register_feed(site_url: str) -> str`` – finds an RSS/Atom feed for the given site and
  stores it in the local registry.
* ``list_registered_feeds() -> str`` – returns a newline‑separated list of stored feed URLs.
"""

import os
from fastmcp import FastMCP

from src.feed_utils import register_feed as register
from src.main.tools.registry import list_feeds

mcp = FastMCP()


@mcp.tool
async def register_feed(site_url: str) -> str:
    """Detect an RSS/Atom feed for *site_url* and add it to the registry.

    Delegates to the shared ``register_feed`` implementation and returns the
    resulting message string.
    """
    result = register(site_url)
    return result["message"]


@mcp.tool
async def list_registered_feeds() -> str:
    """Return all registered feed URLs as a newline‑separated string."""
    feeds = list_feeds()
    if not feeds:
        return "No feeds registered."
    return "\n".join(feeds)


def main() -> None:
    """Entry point – start the FastMCP server on stdio transport."""
    port = int(os.getenv("MCP_PORT", "8000"))
    print(f"RSS‑Finder FastMCP server listening on port {port} (stdio transport)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
