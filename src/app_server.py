from fastapi import  FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the FeedQuest's FastAPI server!"}

@app.get("/extractFeed ")
async def extract_feed(url: str):
    return {"feed_url": "https://example.com/feed"}

