import logging
from typing import List, Dict
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.main.tools.rss_feed_fetcher import fetch_rss_feed, get_feed_metadata
from src.main.tools.summarizer import auto_summarize, SummaryConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_entry_content(entry: Dict) -> str:
    """Extract the best available content from an entry"""
    # Try different fields where content might be available
    content_fields = ['content', 'summary', 'description']
    for field in content_fields:
        if field in entry and entry[field]:
            return entry[field]
    return entry.get('title', '')  # Fallback to title if no content found

def process_feed_with_summaries(url: str, entry_limit: int = 3) -> List[Dict]:
    """
    Fetch RSS feed entries and generate summaries for their content
    """
    logger.info(f"Processing feed: {url}")

    try:
        # First get feed metadata
        metadata = get_feed_metadata(url)
        logger.info(f"Processing feed: {metadata['title']}")

        # Fetch feed entries
        entries = fetch_rss_feed(url, limit=entry_limit)
        logger.info(f"Fetched {len(entries)} entries")

        # Configure summarizer
        config = SummaryConfig(
            model="gpt-oss:20b",
            temperature=0.7,
            max_tokens=2000,
            length="medium"
        )

        # Process each entry
        processed_entries = []
        for i, entry in enumerate(entries, 1):
            logger.info(f"Processing entry {i}/{len(entries)}: {entry['title']}")

            # Get the best available content for summarization
            content = get_entry_content(entry)
            if not content:
                logger.warning(f"No content found for entry: {entry['title']}")
                continue

            # Generate summary of the content
            try:
                summary = auto_summarize(content, config)
                entry['summary'] = summary
                entry['original_content'] = content
            except Exception as e:
                logger.error(f"Failed to generate summary for entry {entry['title']}: {e}")
                entry['summary'] = "Failed to generate summary"

            processed_entries.append(entry)

        return processed_entries

    except Exception as e:
        logger.error(f"Error processing feed: {str(e)}")
        raise

def main():
    """
    Test RSS feed fetching and summarization with multiple feeds
    """
    # Test feeds - using more reliable RSS feeds
    feeds = [
        "https://importai.substack.com/feed",
    ]

    for feed_url in feeds:
        print(f"\nProcessing feed: {feed_url}")
        print("-" * 80)

        try:
            entries = process_feed_with_summaries(feed_url, entry_limit=1)

            # Display results
            for entry in entries:
                print(f"\nTitle: {entry['title']}")
                print(f"Original Link: {entry['link']}")
                print(f"Published: {entry['published']}")
                print("\nOriginal Content:")
                print("-" * 20)
                print(entry.get('original_content', 'No content available'))
                print("\nSummary:")
                print("-" * 20)
                print(entry.get('summary', 'No summary available'))
                print("-" * 40)

        except Exception as e:
            print(f"Failed to process feed {feed_url}: {e}")
            continue

if __name__ == "__main__":
    main()
