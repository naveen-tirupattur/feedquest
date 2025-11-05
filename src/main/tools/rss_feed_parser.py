import feedparser

def is_valid_rss_feed(feed_url: str) -> bool:
    """Check if the given URL points to a valid RSS/Atom feed.

    Parameters
    ----------
    feed_url:
        The URL to check.
    Returns
    -------
    bool
        ``True`` if the URL points to a valid feed, ``False`` otherwise.
    """