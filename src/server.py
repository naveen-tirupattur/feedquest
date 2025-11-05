"""FastMCP server exposing minimal RSS‑feed discovery tools.

Available tools:
* ``register_feed(site_url: str) -> str`` – finds an RSS/Atom feed for the given site and
  stores it in the local registry.
* ``list_registered_feeds() -> str`` – returns a newline‑separated list of stored feed URLs.
"""

import os
from fastmcp import FastMCP

from rss_finder import find_rss_feed
from registry import add_feed, list_feeds

mcp = FastMCP()


@mcp.tool
async def register_feed(site_url: str) -> str:
    """Detect an RSS/Atom feed for *site_url* and add it to the registry.

    Returns a human‑readable status message.
    """
    feed_url = find_rss_feed(site_url)
    if not feed_url:
        return f"No RSS/Atom feed found for {site_url}."

    added = add_feed(feed_url)
    if added:
        return f"Feed registered: {feed_url}"
    else:
        return f"Feed already registered: {feed_url}"


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

