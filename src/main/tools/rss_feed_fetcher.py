import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RSSFeedError(Exception):
    """Custom exception for RSS feed errors"""
    pass

def extract_content(entry):
    if hasattr(entry, "content") and entry.content:
        content_values = [c.value for c in entry.content if hasattr(c, "value")]
        if content_values:
            return content_values[0]
    if "summary" in entry:
        return entry.summary
    return entry.title or ""

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join([l for l in lines if l])

def validate_url(url: str) -> bool:
    """
    Validate if the given URL is properly formatted
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"URL validation failed for {url}: {str(e)}")
        return False

def fetch_rss_feed(url: str, limit: Optional[int] = None) -> List[Dict]:
    """
    Fetch and parse an RSS feed from the given URL

    Args:
        url (str): The URL of the RSS feed
        limit (int, optional): Maximum number of entries to return

    Returns:
        List[Dict]: List of feed entries with title, link, description, and published date

    Raises:
        RSSFeedError: If there's an error fetching or parsing the feed
    """
    logger.info(f"Fetching RSS feed from: {url}")
    if not validate_url(url):
        logger.error(f"Invalid URL format: {url}")
        raise RSSFeedError("Invalid URL format")

    try:
        logger.debug(f"Parsing feed with limit: {limit}")
        feed = feedparser.parse(url)

        if feed.bozo:
            logger.error(f"Failed to parse RSS feed: {feed.bozo_exception}")
            raise RSSFeedError(f"Failed to parse RSS feed: {feed.bozo_exception}")

        if not feed.entries:
            logger.warning("No entries found in feed")
            return []

        entries = []
        for entry in feed.entries[:limit] if limit else feed.entries:
            html = extract_content(entry)
            clean_text = clean_html(html)
            parsed_entry = {
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'description': entry.get('description', ''),
                'published': entry.get('published', ''),
                'author': entry.get('author', ''),
                'id': entry.get('id', ''),
                'content': clean_text,
            }
            entries.append(parsed_entry)

        logger.info(f"Successfully fetched {len(entries)} entries from feed")
        return entries

    except Exception as e:
        logger.error(f"Error fetching RSS feed: {str(e)}")
        raise RSSFeedError(f"Error fetching RSS feed: {str(e)}")

def get_feed_metadata(url: str) -> Dict:
    """
    Get metadata about the RSS feed

    Args:
        url (str): The URL of the RSS feed

    Returns:
        Dict: Feed metadata including title, description, and last updated
    """
    logger.info(f"Fetching metadata for feed: {url}")
    if not validate_url(url):
        logger.error(f"Invalid URL format: {url}")
        raise RSSFeedError("Invalid URL format")

    try:
        feed = feedparser.parse(url)

        if feed.bozo:
            logger.error(f"Failed to parse RSS feed: {feed.bozo_exception}")
            raise RSSFeedError(f"Failed to parse RSS feed: {feed.bozo_exception}")

        metadata = {
            'title': feed.feed.get('title', ''),
            'description': feed.feed.get('description', ''),
            'link': feed.feed.get('link', ''),
            'last_updated': feed.feed.get('updated', ''),
            'language': feed.feed.get('language', ''),
        }

        logger.info(f"Successfully fetched metadata for feed: {metadata['title']}")
        return metadata

    except Exception as e:
        logger.error(f"Error fetching feed metadata: {str(e)}")
        raise RSSFeedError(f"Error fetching feed metadata: {str(e)}")

def example_usage():
    """
    Example of how to use the RSS feed functions
    """
    # Example with a popular RSS feed
    try:
        # NASA's Breaking News feed
        url = "https://news.ycombinator.com/rss"

        # Get feed metadata
        metadata = get_feed_metadata(url)
        print("Feed Title:", metadata['title'])
        print("Feed Description:", metadata['description'])

        # Get the latest 3 entries
        entries = fetch_rss_feed(url, limit=3)
        print("\nLatest 3 entries:")
        for entry in entries:
            print(f"\nTitle: {entry['title']}")
            print(f"Link: {entry['link']}")
            print(f"Published: {entry['published']}")

    except RSSFeedError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    example_usage()
