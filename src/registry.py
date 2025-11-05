"""Simple persistent registry for RSS feed URLs.

Feeds are stored one per line in a file named ``feeds.txt`` located in the repository
root.  The functions provide lightweight add/list operations suitable for a single‑
process environment.
"""

from __future__ import annotations

import os
from typing import List

FEED_FILE = os.path.join(os.path.dirname(__file__), "feeds.txt")


def _ensure_file_exists() -> None:
    if not os.path.exists(FEED_FILE):
        # Create an empty file so later reads/writes work reliably.
        open(FEED_FILE, "a", encoding="utf-8").close()


def add_feed(feed_url: str) -> bool:
    """Add *feed_url* to the registry if it is not already present.

    Returns ``True`` when the feed was added, ``False`` if it was already registered.
    """
    _ensure_file_exists()
    feed_url = feed_url.strip()
    if not feed_url:
        return False

    existing = set(list_feeds())
    if feed_url in existing:
        return False

    with open(FEED_FILE, "a", encoding="utf-8") as f:
        f.write(feed_url + "\n")
    return True


def list_feeds() -> List[str]:
    """Return a list of all registered feed URLs (empty list if none)."""
    _ensure_file_exists()
    with open(FEED_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

