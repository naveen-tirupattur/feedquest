"""Database utilities for FeedQuest.

This module centralises connection handling and schema initialisation.  By
keeping the *SQL* in a separate ``db_schema.sql`` file we make future schema
migrations straightforward – you can edit the SQL file and add a migration
script without touching the business‑logic code in ``registry.py``.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "feeds.db"))

def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection ready for use.

    ``check_same_thread=False`` allows the same connection object to be used in
    background threads (useful for async fetchers).  Callers are responsible for
    closing the connection when done.
    """
    return sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)

def init_schema() -> None:
    """Create tables if they do not exist.

    The SQL statements live in ``db_schema.sql`` next to this module.  Keeping
    them external makes it easy to version‑control migrations.
    """
    schema_path = Path(__file__).with_name("db_schema.sql")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_connection()
    try:
        conn.executescript(sql)
        conn.commit()
        # ---------------------------------------------------------------------
        # Migration: ensure the ``feeds`` table has an ``id`` primary key.
        # Older versions of the repo created ``feeds`` with only ``url``+``added``.
        # If the column is missing we rename the old table, create the new schema
        # (which now includes ``id``), copy the data, and drop the temporary table.
        # ---------------------------------------------------------------------
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(feeds)")
        cols = [row[1] for row in cur.fetchall()]
        if "id" not in cols:
            # Rename old table
            cur.execute("ALTER TABLE feeds RENAME TO feeds_old")
            # Re‑create the proper feeds table (the schema script already did it)
            # Copy data – ``feeds_old`` has columns (url, added) only.
            cur.execute(
                "INSERT INTO feeds (url, added) SELECT url, added FROM feeds_old"
            )
            cur.execute("DROP TABLE feeds_old")
            conn.commit()
        cur.close()
    finally:
        conn.close()
