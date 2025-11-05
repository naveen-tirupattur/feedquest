from fastapi import FastAPI
from src.feed_utils import register_feed as register
from src.main.tools.registry import list_feeds
import uvicorn
from typing import List

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

@app.get(path="/listFeeds", tags=["Feed"], summary="List registered feeds",
         description="Return all registered feed URLs as a newline-separated string.")
async def list_registered_feeds() -> List[str]:
    feeds = list_feeds()
    if not feeds:
        return ["No feeds registered."]
    return feeds


def main():
    # bind to localhost interface and enable reload for development
    uvicorn.run(app, host="127.0.0.1", port=8090, reload=True)

if __name__ == "__main__":
    main()
