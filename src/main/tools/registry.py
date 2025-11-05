"""SQLite‑backed registry for RSS feed URLs.

Each feed is stored in a lightweight SQLite database located at ``src/feeds.db``.
The table schema is simple:

```
CREATE TABLE IF NOT EXISTS feeds (
    url   TEXT PRIMARY KEY,
    added TEXT NOT NULL
);
```

The helper functions ``add_feed`` and ``list_feeds`` operate on this table.
``add_feed`` returns ``True`` when a new URL is inserted and ``False`` when the URL
was already present or invalid.
``list_feeds`` returns the URLs in insertion order.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import List

# Resolve the SQLite database file path. ``registry.py`` resides in
# ``src/main/tools``; the database lives in the top‑level ``src`` directory.
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "feeds.db"))

# Correct SQLite schema for the ``feeds`` table.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS feeds (
    url   TEXT PRIMARY KEY,
    added TEXT NOT NULL
);
"""


def _get_connection() -> sqlite3.Connection:
    """Open a SQLite connection and ensure the schema exists."""
    conn = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)
    conn.execute(_SCHEMA)
    return conn


def add_feed(feed_url: str) -> bool:
    """Add *feed_url* to the registry.

    Returns ``True`` if the URL was newly inserted, ``False`` if it was already
    present or if ``feed_url`` is empty/invalid.
    """
    feed_url = (feed_url or "").strip()
    if not feed_url:
        return False

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO feeds (url, added) VALUES (?, ?)",
            (feed_url, ts),
        )
        conn.commit()
        inserted = cur.rowcount  # rowcount is 1 if inserted, 0 if ignored
        conn.close()
        return inserted == 1
    except Exception:
        return False


def list_feeds() -> List[str]:
    """Return all registered feed URLs ordered by insertion time."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT url FROM feeds ORDER BY rowid")
        rows = cur.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception:
        return []
