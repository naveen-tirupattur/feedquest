"""Shared utilities for FeedQuest.

Both the FastAPI HTTP server (`src/app_server.py`) and the FastMCP tool server
(`src/server.py`) need to discover an RSS/Atom feed for a given website and
register it in the SQLite‑backed registry.  This module provides a tiny API that
encapsulates that workflow so the two servers can reuse the same logic.
"""

from __future__ import annotations

from typing import Dict

from src.main.tools.registry import add_feed
from src.main.tools.rss_feed_utils import find_rss_feed


def register_feed(site_url: str) -> Dict[str, str]:
    """Discover a feed for *site_url* and add it to the registry.

    The discovery function now returns a dictionary with feed metadata.  The
    registry ``add_feed`` accepts the same structure.  A JSON‑compatible result
    with a ``message`` field is returned.
    """
    feed_info = find_rss_feed(site_url)
    if not feed_info:
        return {"message": f"No RSS/Atom feed found for {site_url}."}

    added = add_feed(feed_info)
    if added:
        return {"message": f"Feed registered: {feed_info.get('url', '')}"}
    else:
        return {"message": f"Feed already registered: {feed_info.get('url', '')}"}
