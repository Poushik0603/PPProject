"""
database.py - Simple SQLite storage for news bookmarks.

This version keeps the same public functions the rest of the project expects,
but removes the MySQL dependency so the project runs with standard Python.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).with_name("bookmarks.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        url TEXT NOT NULL UNIQUE,
        category TEXT DEFAULT 'General',
        sentiment TEXT DEFAULT 'Neutral',
        tag TEXT DEFAULT 'None',
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    with get_connection() as conn:
        conn.execute(sql)
        conn.commit()
    logger.info("SQLite database ready: %s", DB_PATH)


def insert_bookmark(
    title: str,
    description: str,
    url: str,
    category: str = "General",
    sentiment: str = "Neutral",
    tag: str = "None",
) -> bool:
    sql = """
    INSERT INTO bookmarks (title, description, url, category, sentiment, tag)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    try:
        with get_connection() as conn:
            conn.execute(sql, (title, description, url, category, sentiment, tag))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        logger.warning("Duplicate bookmark skipped: %s", url)
        return False
    except sqlite3.Error as exc:
        logger.error("Insert failed: %s", exc)
        return False


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]


def fetch_all_bookmarks() -> list[dict]:
    sql = "SELECT * FROM bookmarks ORDER BY saved_at DESC, id DESC"
    try:
        with get_connection() as conn:
            return _rows_to_dicts(conn.execute(sql).fetchall())
    except sqlite3.Error as exc:
        logger.error("Fetch all failed: %s", exc)
        return []


def fetch_bookmarks_by_category(category: str) -> list[dict]:
    sql = "SELECT * FROM bookmarks WHERE category = ? ORDER BY saved_at DESC, id DESC"
    try:
        with get_connection() as conn:
            return _rows_to_dicts(conn.execute(sql, (category,)).fetchall())
    except sqlite3.Error as exc:
        logger.error("Fetch by category failed: %s", exc)
        return []


def search_bookmarks(keyword: str) -> list[dict]:
    sql = """
    SELECT * FROM bookmarks
    WHERE title LIKE ? OR description LIKE ?
    ORDER BY saved_at DESC, id DESC
    """
    pattern = f"%{keyword}%"
    try:
        with get_connection() as conn:
            return _rows_to_dicts(conn.execute(sql, (pattern, pattern)).fetchall())
    except sqlite3.Error as exc:
        logger.error("Search failed: %s", exc)
        return []


def fetch_bookmark_by_id(bookmark_id: int) -> dict | None:
    sql = "SELECT * FROM bookmarks WHERE id = ?"
    try:
        with get_connection() as conn:
            row = conn.execute(sql, (bookmark_id,)).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as exc:
        logger.error("Fetch by id failed: %s", exc)
        return None


def update_bookmark_tag(bookmark_id: int, tag: str) -> bool:
    sql = "UPDATE bookmarks SET tag = ? WHERE id = ?"
    try:
        with get_connection() as conn:
            cursor = conn.execute(sql, (tag, bookmark_id))
            conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Update tag failed: %s", exc)
        return False


def update_bookmark_category(bookmark_id: int, category: str) -> bool:
    sql = "UPDATE bookmarks SET category = ? WHERE id = ?"
    try:
        with get_connection() as conn:
            cursor = conn.execute(sql, (category, bookmark_id))
            conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Update category failed: %s", exc)
        return False


def delete_bookmark(bookmark_id: int) -> bool:
    sql = "DELETE FROM bookmarks WHERE id = ?"
    try:
        with get_connection() as conn:
            cursor = conn.execute(sql, (bookmark_id,))
            conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Delete failed: %s", exc)
        return False


def delete_all_bookmarks() -> bool:
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM bookmarks")
            conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Delete all failed: %s", exc)
        return False


def get_all_categories() -> list[str]:
    sql = "SELECT DISTINCT category FROM bookmarks ORDER BY category"
    try:
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()
        return [row["category"] for row in rows]
    except sqlite3.Error as exc:
        logger.error("Fetch categories failed: %s", exc)
        return []


def bookmark_exists(url: str) -> bool:
    sql = "SELECT 1 FROM bookmarks WHERE url = ? LIMIT 1"
    try:
        with get_connection() as conn:
            row = conn.execute(sql, (url,)).fetchone()
        return row is not None
    except sqlite3.Error as exc:
        logger.error("Exists check failed: %s", exc)
        return False
