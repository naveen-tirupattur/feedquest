# FeedQuest

Small utility to discover and register RSS/Atom feeds for a given site URL.

## Installation (using a virtual environment)
```bash
# Create the venv in the project root
python -m venv .venv

# Activate it (Linux/macOS)
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

## Run the API server (inside the venv)
```bash
# Ensure the venv is active (see Installation above)
python src/app_server.py --reload

# Or via uvicorn
python -m uvicorn app_server:app --app-dir src --host 127.0.0.1 --port 8090 --reload
```

## API endpoints
* `GET /` – health check returning a welcome message.
* `POST /registerFeed?site_url=…` – discovers and stores the feed URL.

Swagger UI is available at `http://127.0.0.1:8090/docs`.

## Registry (SQLite)
Feeds are persisted in a tiny SQLite database `src/feeds.db` with a single table:
```sql
CREATE TABLE IF NOT EXISTS feeds (url TEXT PRIMARY KEY, added TEXT NOT NULL);
```
Helper functions in `src/main/tools/registry.py`:
* `add_feed(url) -> bool` – inserts if not present.
* `list_feeds() -> List[str]` – returns stored URLs.

## FastMCP tool server (inside the venv)
Run the minimal FastMCP server to expose the same functionality over MCP:
```bash
python src/server.py
```
It provides the tools `register_feed(site_url)` and `list_registered_feeds()`.

## Tests
```bash
pytest -q
```

## Contributing
Feel free to open issues or submit pull requests for enhancements, bug fixes, or additional tests.
