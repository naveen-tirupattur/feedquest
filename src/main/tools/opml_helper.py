from xml.etree import ElementTree
import sys
import os
import pathlib
# Ensure the repository root is on ``sys.path`` so absolute imports of the
# ``src`` package work when this file is executed directly (e.g. ``python
# src/main/tools/opml_helper.py``).
# ``parents[3]`` reaches the project root (``feedquest``), which contains the
# top‑level ``src`` package.
repo_root = pathlib.Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import using the full package path – now safe after adjusting ``sys.path``.
from src.main.tools.rss_feed_utils import find_rss_feed
from src.main.tools.registry import add_feed
def parse_opml(file_path: str) -> list[dict[str]]:
    """Parse an OPML file and extract feed information.

    Parameters
    ----------
    file_path:
        Path to the OPML file.
    Returns
    -------
    list[dict[str]]:
    A list of dictionaries containing feed information."""
    feeds = []
    with open(file_path, "rt", encoding="utf-8") as f:
        tree = ElementTree.parse(f)
    for outline in tree.findall(".//outline"):
        feed_info = {
            "text": outline.attrib.get("text", ""),
            "type": outline.attrib.get("type", ""),
            "xmlUrl": outline.attrib.get("xmlUrl", ""),
            "htmlUrl": outline.attrib.get("htmlUrl", "")
        }
        feeds.append(feed_info)

    return feeds

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python opml_helper.py <path_to_opml_file>")
        sys.exit(1)

    opml_file = sys.argv[1]
    feed_list = parse_opml(opml_file)
    for feed in feed_list:
        url = feed.get("htmlUrl", "")
        print(url)
        if url:
            feed_url = find_rss_feed(url)
            if feed_url:
                added = add_feed(feed_url)
                status = "registered" if added else "already registered"
                print(f"Feed {status}: {feed_url}")
            else:
                print(f"No RSS/Atom feed found for {url}.")
