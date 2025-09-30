from typing import Dict
from fastmcp import FastMCP
import os

from src.main.tools.rss_feed_fetcher import fetch_rss_feed

# Initialize FastMCP server
mcp = FastMCP()

# Default RSS feed URL
DEFAULT_RSS_URL = "https://hnrss.org/newest?points=300"

def format_story(story: Dict[str, str]) -> str:
    """Format a Hacker News story for display"""
    return f"""Title: {story['title']}
Link: {story['link']}
Published: {story['published']}
Author: {story['author']}"""

@mcp.tool
async def get_stories(
        feed_url: str = DEFAULT_RSS_URL, count: int = 30
) -> str:
    """Get top stories

    Args:
        feed_url: URL of the RSS feed to use (default: Hacker News)
        count: Number of stories to return (default: 30)
    """
    try:
        # Use our RSS tool to fetch and parse the feed
        stories = fetch_rss_feed(feed_url, count)

        if not stories:
            return "No stories found."

        formatted_stories = [format_story(story) for story in stories]
        return "\n---\n".join(formatted_stories)

    except Exception as e:
        return f"Error fetching stories: {str(e)}"


def main():
    # Initialize and run the server
    port = int(os.getenv("MCP_PORT", "8000"))
    print(f"Starting FastMCP server on port {port}...")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()