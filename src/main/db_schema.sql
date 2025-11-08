-- SQLite schema for FeedQuest

CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    etag TEXT,
    last_modified TEXT,
    added TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
    title TEXT,
    url TEXT UNIQUE,
    published TEXT,
    content TEXT,
    summary TEXT,
    tags TEXT,
    ai_summary TEXT,
    ai_tags TEXT,
    added TEXT NOT NULL
);

-- Optional table for dense embeddings (binary BLOB)
CREATE TABLE IF NOT EXISTS entry_embeddings (
    entry_id INTEGER PRIMARY KEY REFERENCES entries(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    vector BLOB NOT NULL
);
