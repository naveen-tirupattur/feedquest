from xml.etree import  ElementTree
import sys
from registry import add_feed, list_feeds

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
        print(feed.get("xmlUrl", ""))
        add_feed(feed.get("xmlUrl", ""))

    for feed in list_feeds():
        print(feed)
