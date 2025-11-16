"""Shared utilities for FeedQuest.

Both the FastAPI HTTP server (`src/app_server.py`) and the FastMCP tool server
(`src/server.py`) need to discover an RSS/Atom feed for a given website and
register it in the SQLite‑backed registry.  This module provides a tiny API that
encapsulates that workflow so the two servers can reuse the same logic.
"""

from __future__ import annotations

from typing import Dict


from src.main.tools.rss_feed_utils import find_rss_feed


