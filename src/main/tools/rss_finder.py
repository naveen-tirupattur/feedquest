"""Utility to discover an RSS/Atom feed URL for a given website.

The function follows a simple two‑step strategy:
1. Fetch the HTML of the site and look for ``<link>`` tags with ``type`` set to
   ``application/rss+xml`` or ``application/atom+xml``. The ``href`` attribute is
   resolved against the base URL.
2. If step 1 fails, attempt to parse the original URL directly with ``feedparser``;
   some sites serve the feed at the root URL (e.g. ``example.com/feed``) and the
   parser will succeed when entries are present.

Returns the discovered feed URL or ``None`` if no feed could be identified.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import feedparser

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


def find_rss_feed(site_url: str, timeout: int = 5) -> Optional[str]:
    """Return the RSS/Atom feed URL for *site_url* if one can be discovered.

    Parameters
    ----------
    site_url:
        The base website URL (e.g. ``"https://example.com"``).
    timeout:
        HTTP request timeout in seconds.
    """
    try:
        # Use plain ASCII hyphen (-) in the User-Agent to avoid encoding errors
        response = requests.get(site_url, timeout=timeout, headers={"User-Agent": "RSS-Finder/1.0"})
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover – network errors are environment specific
        logger.error("Failed to fetch site %s: %s", site_url, exc)
        return None

    # Try HTML discovery
    soup = BeautifulSoup(response.text, "html.parser")
    link_href = _find_link_tag(soup)
    if link_href:
        feed_url = urljoin(response.url, link_href)
        logger.info("Discovered feed via <link>: %s", feed_url)
        return feed_url

    # Fallback – parse the URL itself as a feed
    parsed = feedparser.parse(site_url)
    if not parsed.bozo and parsed.entries:
        logger.info("Site URL itself is a valid feed: %s", site_url)
        return site_url

    logger.info("No feed found for %s", site_url)
    return None
