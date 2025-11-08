from fastapi import FastAPI
from typing import Optional
from src.main.tools.utils import register_feed as register
from src.main.tools.registry import list_feeds
from src.main.tools.fetcher import fetch_all_entries, fetch_feed
import uvicorn
from typing import List, Dict

app = FastAPI(
    title="FeedQuest API",
    description="Extract RSS/Atom feed URLs from a given site URL.",
    version="0.1.0",
    docs_url="/docs",        # Swagger UI
    redoc_url="/redoc",      # ReDoc UI
    openapi_url="/openapi.json",
)

@app.get("/", tags=["Root"], summary="API root")
async def read_root():
    return {"message": "Welcome to the FeedQuest's FastAPI server!"}

@app.post("/registerFeed", tags=["Feed"], summary="Register feed URL",
          description="Register the discovered feed URL in the local registry.")
async def register_feed(site_url: str) -> dict:
    # Reuse the shared registration logic
    return register(site_url)

@app.get(
    path="/listFeeds",
    tags=["Feed"],
    summary="List registered feeds",
    description="Return all registered feeds with metadata as a JSON list.",
)
async def list_registered_feeds() -> List[Dict[str, str]]:
    feeds = list_feeds()
    if not feeds:
        # Return an empty list; the client can interpret as no feeds.
        return []
    return feeds


@app.post(
    "/fetchEntries",
    tags=["Feed"],
    summary="Fetch new entries",
    description=(
        "Fetch the latest articles either for a specific RSS/Atom feed (if ``url`` "
        "is supplied) or for all registered feeds. Returns a JSON summary with "
        "the number of feeds processed and entries added."
    ),
)
async def fetch_entries_endpoint(url: Optional[str] = None) -> dict:
    """FastAPI wrapper that supports optional single‑feed fetching.

    * If ``url`` is provided, only that feed is fetched via ``fetch_feed``.
    * Otherwise, ``fetch_all_entries`` processes every registered feed.
    """
    if url:
        added = await fetch_feed(url)
        processed = 1
    else:
        processed, added = await fetch_all_entries()
    return {"processed_feeds": processed, "added_entries": added}


def main():
    # bind to localhost interface and enable reload for development
    uvicorn.run(app, host="127.0.0.1", port=8090, reload=True)

if __name__ == "__main__":
    main()
