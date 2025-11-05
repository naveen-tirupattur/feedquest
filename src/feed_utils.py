"""Shared utilities for FeedQuest.

Both the FastAPI HTTP server (`src/app_server.py`) and the FastMCP tool server
(`src/server.py`) need to discover an RSS/Atom feed for a given website and
register it in the SQLite‑backed registry.  This module provides a tiny API that
encapsulates that workflow so the two servers can reuse the same logic.
"""

from __future__ import annotations

from typing import Optional, Dict

from .main.tools.rss_finder import find_rss_feed
from .main.tools.registry import add_feed

def discover_feed(site_url: str) -> Optional[str]:
    """Return the RSS/Atom feed URL for *site_url* or ``None`` if not found."""
    return find_rss_feed(site_url)

def register_feed(site_url: str) -> Dict[str, str]:
    """Discover a feed for *site_url* and add it to the registry.

    Returns a dictionary suitable for JSON responses, containing a ``message``
    field describing the outcome.
    """
    feed_url = discover_feed(site_url)
    if not feed_url:
        return {"message": f"No RSS/Atom feed found for {site_url}."}

    added = add_feed(feed_url)
    if added:
        return {"message": f"Feed registered: {feed_url}"}
    else:
        return {"message": f"Feed already registered: {feed_url}"}