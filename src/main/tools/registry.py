"""High‑level registry API.

The low‑level SQLite connection and schema creation lives in ``src/main/tools/db``.
This module offers convenient helpers for the application layer:

* ``add_feed`` / ``list_feeds`` – manage RSS source URLs.
* ``add_entry`` – store a parsed article belonging to a feed.
* ``add_embedding`` – optional dense vector for semantic search.

All functions operate on the single SQLite file ``src/feeds.db``; the schema is
defined in ``db_schema.sql`` and initialised by ``db.init_schema()`` on import.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Union

# Re‑use the DB utilities that now own connection handling and schema init.
from src.main.db import get_connection, init_schema

def _init_db() -> None:
    init_schema()

# Run once when the module is imported.
_init_db()

def _normalize_timestamp(ts: str) -> str:
    # print(ts)
    if not ts:
        dt = datetime.now(timezone.utc)
    else:
        try:
            format_pattern = '%a, %d %b %Y %H:%M:%S %Z'
            dt = datetime.strptime(ts, format_pattern)
        except ValueError:
            dt = datetime.now(timezone.utc)
    # print(dt)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def add_feed(
    feed_info: dict[str, str]
) -> bool:
    """Insert a new feed URL or update its metadata.

    ``feed_info`` must contain at least a ``url`` key. Optional keys are
    ``title``, ``etag`` and ``last_modified``. Missing values are ignored.
    The function is idempotent – it inserts a row if the URL does not exist or
    updates the supplied metadata fields for an existing entry.
    """
    feed_url = (feed_info.get("url", "") or "").strip()
    if not feed_url:
        return False

    title = feed_info.get("title")
    etag = feed_info.get("etag")
    last_modified = _normalize_timestamp(feed_info.get("last_modified"))

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Insert with IGNORE – if the URL exists we will update missing metadata.
        cur.execute(
            "INSERT OR IGNORE INTO feeds (url, added, title, etag, last_modified) "
            "VALUES (?, ?, ?, ?, ?)",
            (feed_url, ts, title, etag, last_modified or ts),
        )
        inserted = cur.rowcount

        # If the row already existed, apply any provided metadata updates.
        if inserted == 0:
            updates = []
            params: list = []
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if etag is not None:
                updates.append("etag = ?")
                params.append(etag)
            if last_modified is not None:
                updates.append("last_modified = ?")
                params.append(last_modified)
            if updates:
                params.append(feed_url)
                cur.execute(
                    f"UPDATE feeds SET {', '.join(updates)} WHERE url = ?",
                    tuple(params),
                )
                conn.commit()
                conn.close()
                return True

        conn.commit()
        conn.close()
        return inserted == 1 or inserted == 0
    except Exception:
        return False


def list_feeds() -> List[Dict[str, str]]:
    """Return all stored feeds with their metadata.

    The result is a list of dictionaries ordered by insertion time.  Each dict
    contains the keys ``url``, ``title``, ``etag``, ``last_modified`` and
    ``added``.  Missing optional values are omitted from the dict.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT url, title, etag, last_modified, added FROM feeds ORDER BY rowid"
        )
        rows = cur.fetchall()
        conn.close()
        feeds: List[Dict[str, str]] = []
        for url, title, etag, last_modified, added in rows:
            entry: Dict[str, str] = {"url": url, "added": added}
            if title:
                entry["title"] = title
            if etag:
                entry["etag"] = etag
            if last_modified:
                entry["last_modified"] = last_modified
            feeds.append(entry)
        return feeds
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Entry‑level helpers (articles/posts)
# ---------------------------------------------------------------------------
def add_entry(
    *, feed_url: str, title: Optional[str] = None, url: Optional[str] = None,
    published: Optional[str] = None, content: Optional[str] = None,
    summary: Optional[str] = None, tags: Optional[List[str]] = None,
    ai_summary: Optional[str] = None, ai_tags: Optional[List[str]] = None
) -> int | None:
    """Insert a new entry linked to *feed_url*.

    Returns the generated ``entries.id`` on success or ``None`` on failure (e.g.,
    unknown feed or duplicate URL).
    """
    # Resolve the feed id first.
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM feeds WHERE url = ?", (feed_url,))
    feed_row = cur.fetchone()
    if not feed_row:
        conn.close()
        return None
    feed_id = feed_row[0]
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if tags:
        tags = ",".join(tags)
    else:
        tags = None
    if ai_tags:
        ai_tags = ",".join(ai_tags)
    else:
        ai_tags = None
    try:
        print(feed_id, title, url, published, content, summary, ai_summary, ts, tags, ai_tags)
        cur.execute(
            """
            INSERT OR IGNORE INTO entries (
                feed_id, title, url, published, content, summary, ai_summary, added, tags, ai_tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (feed_id, title, url, published, content, summary, ai_summary, ts, tags, ai_tags),
        )
        conn.commit()
        entry_id = cur.lastrowid if cur.rowcount else None
        conn.close()
        return entry_id
    except Exception:
        conn.close()
        raise


def add_embedding(entry_id: int, vector: bytes, model: str = "default") -> bool:
    """Store a dense embedding for *entry_id*.

    ``vector`` must be a ``bytes`` object (e.g., ``np.float32.tobytes()``).  The
    function overwrites any existing embedding for the same entry.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO entry_embeddings (entry_id, model, vector) VALUES (?, ?, ?)",
            (entry_id, model, vector),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
