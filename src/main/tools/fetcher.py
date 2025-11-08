"""Utilities for fetching new entries from registered RSS/Atom feeds.

The module provides a single public function ``fetch_all_entries`` that loops over
all feeds stored in the ``feeds`` table, parses each feed, and stores any new
articles via ``registry.add_entry``.  It returns a tuple ``(processed, added)``
where ``processed`` is the total number of feeds examined and ``added`` is the
number of entries successfully inserted.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Tuple

import feedparser
import requests

from src.main.tools.registry import add_entry, list_feeds, add_feed
from src.main.tools.summarizer import summarize_text
from src.main.tools.rss_feed_utils import parse_feed
# Global async lock to serialize SQLite writes across concurrent feed fetches.
_db_write_lock = asyncio.Lock()


# ``parse_feed`` from ``rss_feed_utils`` expects a URL and performs discovery.
# In this module we deal directly with the HTTP response, so we parse the feed
# content with ``feedparser``.


def _sync_fetch(url: str, *, etag: str | None = None, last_modified: str | None = None) -> requests.Response:
    """Blocking fetch using ``requests`` with conditional headers.

    ``etag`` and ``last_modified`` are optional values taken from the ``feeds``
    table. They are sent as ``If-None-Match`` and ``If-Modified-Since`` to allow
    the server to return a ``304`` when the feed has not changed.
    """
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    resp = requests.get(url, timeout=10.0, headers=headers)
    # ``raise_for_status`` will raise on 4xx/5xx *except* 304 which is a valid
    # ‘not modified’ response.
    if resp.status_code != 304:
        resp.raise_for_status()
    return resp


logger = logging.getLogger(__name__)

async def _process_feed(feed_url: str, _: None = None) -> int:
    """Fetch a feed asynchronously (via thread) and store any new entries.

    The ``_: None`` placeholder keeps the signature compatible with the previous
    implementation that accepted a client; it is ignored.
    """
    # Retrieve stored etag/last_modified for conditional GET.
    stored = next((f for f in list_feeds() if f.get("url") == feed_url), {})
    stored_etag = stored.get("etag")
    stored_last_modified = stored.get("last_modified")

    try:
        response = await asyncio.to_thread(
            _sync_fetch, feed_url, etag=stored_etag, last_modified=stored_last_modified
        )
    except Exception as exc:
        logger.error("Error fetching feed %s: %s", feed_url, exc)
        return 0

    # 304 means no new content.
    if response.status_code == 304:
        return 0

    # Update feed metadata if server provided new values.
    new_etag = response.headers.get("ETag")
    new_last_modified = response.headers.get("Last-Modified")
    if new_etag or new_last_modified:
        # Updating feed metadata also writes to SQLite; serialize it.
        async with _db_write_lock:
            add_feed({"url": feed_url, "etag": new_etag, "last_modified": new_last_modified})

    # Parse the feed content safely using feedparser directly.
    try:
        feed_response = feedparser.parse(response.content)
        parsed = parse_feed(feed_response)
    except Exception as exc:
        logger.error("Failed to parse feed %s: %s", feed_url, exc)
        return 0


    if not parsed:
        logger.info("No entries found in feed %s", feed_url)
        return 0

    # Limit to the 5 most recent entries.
    entries = parsed[:5]
    added = 0
    for entry in entries:
        try:
            # Determine text to summarise – prefer full content if available.
            feed_content = None
            if entry.get("content"):
                # ``content`` can be a list of dicts with ``value``.
                first = entry.get("content")
                if isinstance(first, list) and first:
                    feed_content = first[0].get("value")
                else:
                    feed_content = str(first)
            elif entry.get("summary"):
                feed_content = entry.get("summary")
            if not feed_content:
                continue
            # Summarize the content, handling possible LLM service failures.
            try:
                ai_summary = summarize_text(feed_content)
            except Exception as exc:  # pragma: no cover – network/LLM errors
                logger.error("Summarization failed for %s: %s", feed_url, exc)
                ai_summary = {"summary": "", "ai_tags": []}

            # Convert feedparser tag dicts to a plain list of strings.
            raw_tags = entry.get("tags") or []
            if isinstance(raw_tags, list):
                tags = []
                for t in raw_tags:
                    if isinstance(t, dict) and "term" in t:
                        tags.append(t["term"])
                    else:
                        tags.append(str(t))
            else:
                tags = []

            # Serialize DB writes to avoid SQLite "database is locked" errors.
            async with _db_write_lock:
                result = add_entry(
                    feed_url=feed_url,
                    title=entry.get("title"),
                    url=entry.get("link"),
                    published=entry.get("published"),
                    content=entry.get("content"),
                    summary=entry.get("summary"),
                    tags=tags,
                    ai_summary=ai_summary.get("summary"),
                    ai_tags=ai_summary.get("ai_tags"),
                )
            if result is not None:
                added += 1
        except Exception as exc:
            logger.error("Failed to store entry from %s: %s", feed_url, exc)
            continue
    return added


async def fetch_all_entries() -> Tuple[int, int]:
    """Fetch entries for every registered feed concurrently.

    Returns a ``(feeds_processed, total_entries_added)`` tuple.
    """
    feeds = list_feeds()
    tasks = []
    for feed in feeds:
        url = feed.get("url")
        if not url:
            continue
        tasks.append(_process_feed(url))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_added = sum(r if isinstance(r, int) else 0 for r in results)
    return len(feeds), total_added


async def fetch_feed(feed_url: str) -> int:
    """Fetch a single feed and return the number of new entries added.

    This thin wrapper re‑uses the internal ``_process_feed`` logic, exposing a
    public async API that callers (e.g., the FastAPI endpoint) can use when they
    only need to process one specific feed.
    """
    return await _process_feed(feed_url)

if __name__ == "__main__":
    import asyncio

    async def main():
        added = await fetch_feed("https://simonwillison.net/atom/everything/")
        print(f"added {added} new entries.")

    asyncio.run(main())
