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
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Union

# Re‑use the DB utilities that now own connection handling and schema init.
from src.main.db import get_connection, init_schema

# Pre-compiled timestamp format pattern for efficiency
_TS_FORMAT_PATTERN = re.compile(r'%a, %d %b %Y %H:%M:%S %Z')

def _init_db() -> None:
    init_schema()

# Run once when the module is imported.
_init_db()

_CACHED_TIMESTAMPS: Dict[str, str] = {}

def _normalize_timestamp(ts: str) -> str:
    """Normalize timestamp to ISO 8601 UTC format with caching."""
    if not ts:
        dt = datetime.now(timezone.utc)
    else:
        # Check cache first
        if ts in _CACHED_TIMESTAMPS:
            return _CACHED_TIMESTAMPS[ts]
        try:
            dt = datetime.strptime(ts, '%a, %d %b %Y %H:%M:%S %Z')
        except ValueError:
            dt = datetime.now(timezone.utc)
    result = dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if ts:
        _CACHED_TIMESTAMPS[ts] = result
    return result

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
        with get_connection() as conn:
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
                    return True

            conn.commit()
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
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT url, title, etag, last_modified, added FROM feeds ORDER BY rowid"
            )
            rows = cur.fetchall()
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


def get_feed(url: str) -> Dict[str, str] | None:
    """Get a single feed by URL (avoids N+1 query)."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT url, title, etag, last_modified, added FROM feeds WHERE url = ?"
                , (url,)
            )
            row = cur.fetchone()
            if not row:
                return None
            url, title, etag, last_modified, added = row
            entry: Dict[str, str] = {"url": url, "added": added}
            if title:
                entry["title"] = title
            if etag:
                entry["etag"] = etag
            if last_modified:
                entry["last_modified"] = last_modified
            return entry
    except Exception:
        return None

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
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM feeds WHERE url = ?", (feed_url,))
        feed_row = cur.fetchone()
        if not feed_row:
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
            return entry_id
        except Exception:
            raise


def add_embedding(entry_id: int, vector: bytes, model: str = "default") -> bool:
    """Store a dense embedding for *entry_id*.

    ``vector`` must be a ``bytes`` object (e.g., ``np.float32.tobytes()``).  The
    function overwrites any existing embedding for the same entry.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO entry_embeddings (entry_id, model, vector) VALUES (?, ?, ?)",
                (entry_id, model, vector),
            )
            conn.commit()
            return True
    except Exception:
        return False


def get_entry_by_id(entry_id: int) -> Dict[str, str] | None:
    """Retrieve a single entry by its ID.

    Returns a dictionary with entry details or None if not found.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, url, title, published, content, summary, tags, ai_summary, ai_tags, added
                FROM entries WHERE id = ?
                """,
                (entry_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            
            entry_id, url, title, published, content, summary, tags, ai_summary, ai_tags, added = row
            entry: Dict[str, str] = {
                "id": entry_id,
                "url": url,
                "title": title,
                "added": added,
            }
            if published:
                entry["published"] = published
            if content:
                entry["content"] = content
            if summary:
                entry["summary"] = summary
            if tags:
                entry["tags"] = tags
            if ai_summary:
                entry["ai_summary"] = ai_summary
            if ai_tags:
                entry["ai_tags"] = ai_tags
            return entry
    except Exception:
        return None


def list_entries_by_feed(feed_url: str, limit: int = 100) -> List[Dict[str, str]]:
    """Retrieve all entries for a specific feed.

    Returns a list of entries ordered by publication date (newest first).
    Limit default is 100 entries.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT e.id, e.url, e.title, e.published
                FROM entries e
                JOIN feeds f ON e.feed_id = f.id
                WHERE f.url = ?
                ORDER BY e.published DESC
                LIMIT ?
                """,
                (feed_url, limit),
            )
            rows = cur.fetchall()
            if not rows:
                return []
            
            entries: List[Dict[str, str]] = []
            for entry_id, url, title, published in rows:
                entry: Dict[str, str] = {
                    "id": entry_id,
                    "url": url,
                    "title": title,
                }
                if published:
                    entry["published"] = published
                entries.append(entry)
            return entries
    except Exception:
        return []
