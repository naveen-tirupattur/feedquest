"""Utility to discover an RSS/Atom feed URL for a given website.

The function follows a simple two‑step strategy:
1. Fetch the HTML of the site and look for ``<link>`` tags with ``type`` set to
   ``application/rss+xml`` or ``application/atom+xml``. The ``href`` attribute is
   resolved against the base URL.
2. If step 1 fails, attempt to parse the original URL directly with ``feedparser``;
   some sites serve the feed at the root URL (e.g. ``example.com/feed``) and the
   parser will succeed when entries are present.

Returns the discovered feed URL and metadata or ``None`` if no feed could be identified.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import feedparser
from feedparser import FeedParserDict

logger = logging.getLogger(__name__)

def _find_link_tag(soup: BeautifulSoup) -> Optional[str]:
    """Search ``<link>`` tags for RSS/Atom declarations.

    Returns the first matching ``href`` (already resolved to an absolute URL) or ``None``.
    """
    for link in soup.find_all("link", rel="alternate"):
        type_attr = (link.get("type") or "").lower()
        if type_attr in {"application/rss+xml", "application/atom+xml"}:
            href = link.get("href")
            if href:
                return href
    return None

def find_rss_feed(site_url: str, timeout: int = 5) -> Dict[str, str]:
    """Discover an RSS/Atom feed for *site_url* and collect basic metadata.

    The function now performs two steps:
    1. Retrieve the HTML page and look for ``<link>`` tags that declare an RSS or
       Atom feed. If a candidate is found, the URL is resolved against the
       response URL.
    2. Once a feed URL is identified (either from the HTML or by treating the
       original ``site_url`` as a feed), the feed is parsed with ``feedparser`` to
       obtain optional metadata such as ``title``, ``etag`` and ``modified``.

    Returns a dictionary containing at least the ``url`` key. Missing metadata
    fields are omitted. If no feed can be located an empty dictionary is
    returned.
    """
    feed_url: str | None = None
    parsed_feed = None
    try:
        response = requests.get(
            site_url,
            timeout=timeout,
            headers={"User-Agent": "RSS-Finder/1.0"},
        )
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover – network errors are environment specific
        logger.error("Failed to fetch site %s: %s", site_url, exc)
        return {}

    # 1️⃣ HTML discovery for <link> tags
    soup = BeautifulSoup(response.text, "html.parser")
    link_href = _find_link_tag(soup)
    if link_href:
        feed_url = urljoin(response.url, link_href)
        logger.info("Discovered feed via <link>: %s", feed_url)
    else:
        # 2️⃣ Fallback – treat the supplied URL itself as a possible feed
        # Parse once to check validity, reuse the result
        parsed_feed = feedparser.parse(site_url)
        if not parsed_feed.bozo and parsed_feed.entries:
            feed_url = site_url
            logger.info("Site URL itself is a valid feed: %s", site_url)

    if not feed_url:
        logger.info("No feed found for %s", site_url)
        return {}

    # Parse the discovered feed to gather metadata (reuse if we already parsed)
    if parsed_feed is None or feed_url != site_url:
        parsed_feed = feedparser.parse(feed_url)

    result: Dict[str, str] = {"url": feed_url}
    # Feed title – may be missing
    if getattr(parsed_feed, "feed", None) and parsed_feed.feed.get("title"):
        result["title"] = parsed_feed.feed["title"]
    # ETag and Last‑Modified headers are available via the parser's ``etag``
    # and ``modified`` attributes when present.
    if getattr(parsed_feed, "etag", None):
        result["etag"] = parsed_feed.etag
    if getattr(parsed_feed, "modified", None):
        result["last_modified"] = parsed_feed.modified
    return result

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def parse_feed(feed_response: FeedParserDict) -> List[Dict[str, str]]:
    """Extract entries from a parsed feed response.

    Parameters
    ----------
    feed_response:
        The dict from ``feedparser.parse()``.
    Returns
    -------
    bool
        ``True`` if the URL points to a valid feed, ``False`` otherwise.

    """
    results: List[Dict[str, str]] = []
    if not feed_response.bozo and bool(feed_response.entries):
        for entry in feed_response.entries:
            cleaned_summary = ""
            cleaned_content = ""
            if "summary" in entry:
                cleaned_summary = clean_html(entry.summary)
            if "content" in entry and entry.content:
                for content_item in entry.content:
                    cleaned_content = clean_html(content_item.value)
            entry_data: Dict[str, str] = {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "tags": [tag.term for tag in entry.get("tags", [])],
                "content": cleaned_content,
                "summary": cleaned_summary,
            }
            results.append(entry_data)
    return results
