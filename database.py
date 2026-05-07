"""
database.py - MySQL database handler for News Fetcher + Bookmark System.

Connection settings are read from environment variables so the project can run
on different machines without changing source code:

    MYSQL_HOST      default: localhost
    MYSQL_PORT      default: 3306
    MYSQL_USER      default: root
    MYSQL_PASSWORD  default: empty
    MYSQL_DATABASE  default: news_fetcher
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator

try:
    import mysql.connector
    from mysql.connector import Error, IntegrityError
    from mysql.connector.connection import MySQLConnection
except ImportError as exc:  # pragma: no cover - handled at app startup
    raise ImportError(
        "mysql-connector-python is required. Install it with: "
        "py -m pip install mysql-connector-python"
    ) from exc


logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "Wow@1234"),
    "database": os.getenv("MYSQL_DATABASE", "news_fetcher"),
}


def _server_config() -> dict:
    """Return connection settings without a database name."""
    config = DB_CONFIG.copy()
    config.pop("database", None)
    return config


def _row_to_dict(row: dict | None) -> dict | None:
    return dict(row) if row else None


@contextmanager
def get_connection() -> Iterator[MySQLConnection]:
    """
    Returns a MySQL connection configured to return rows as dictionaries.
    Commits are still explicit in write operations.
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> None:
    """Creates the configured MySQL database and bookmarks table if needed."""
    create_database_sql = (
        f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS bookmarks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        description TEXT,
        url VARCHAR(768) NOT NULL UNIQUE,
        category VARCHAR(100) DEFAULT 'General',
        sentiment VARCHAR(20) DEFAULT 'Neutral',
        tag VARCHAR(50) DEFAULT 'None',
        saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_bookmarks_category (category),
        INDEX idx_bookmarks_title (title(191))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    try:
        server_conn = mysql.connector.connect(**_server_config())
        server_cursor = server_conn.cursor()
        server_cursor.execute(create_database_sql)
        server_conn.commit()
        server_cursor.close()
        server_conn.close()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
        logger.info("MySQL database initialised successfully: %s", DB_CONFIG["database"])
    except Error as exc:
        logger.error("Failed to initialise MySQL database: %s", exc)
        raise


def insert_bookmark(
    title: str,
    description: str,
    url: str,
    category: str = "General",
    sentiment: str = "Neutral",
    tag: str = "None",
) -> bool:
    """Inserts a new bookmark. Returns False when the URL already exists."""
    sql = """
    INSERT INTO bookmarks (title, description, url, category, sentiment, tag)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (title, description, url, category, sentiment, tag))
            conn.commit()
            cursor.close()
        logger.info("Bookmark saved: %s", title)
        return True
    except IntegrityError:
        logger.warning("Duplicate URL - bookmark not saved: %s", url)
        return False
    except Error as exc:
        logger.error("Insert failed, rolling back: %s", exc)
        return False


def fetch_all_bookmarks() -> list:
    """Returns all bookmarks ordered by most recently saved."""
    sql = "SELECT * FROM bookmarks ORDER BY saved_at DESC"
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
        return rows
    except Error as exc:
        logger.error("Fetch all failed: %s", exc)
        return []


def fetch_bookmarks_by_category(category: str) -> list:
    """Returns bookmarks filtered by category."""
    sql = "SELECT * FROM bookmarks WHERE category = %s ORDER BY saved_at DESC"
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (category,))
            rows = cursor.fetchall()
            cursor.close()
        return rows
    except Error as exc:
        logger.error("Fetch by category failed: %s", exc)
        return []


def search_bookmarks(keyword: str) -> list:
    """Keyword search over title and description."""
    pattern = f"%{keyword}%"
    sql = """
    SELECT * FROM bookmarks
    WHERE title LIKE %s OR description LIKE %s
    ORDER BY saved_at DESC
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (pattern, pattern))
            rows = cursor.fetchall()
            cursor.close()
        return rows
    except Error as exc:
        logger.error("Search failed: %s", exc)
        return []


def fetch_bookmark_by_id(bookmark_id: int) -> dict | None:
    """Returns a single bookmark by its primary key."""
    sql = "SELECT * FROM bookmarks WHERE id = %s"
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (bookmark_id,))
            row = cursor.fetchone()
            cursor.close()
        return _row_to_dict(row)
    except Error as exc:
        logger.error("Fetch by id failed: %s", exc)
        return None


def update_bookmark_tag(bookmark_id: int, tag: str) -> bool:
    """Updates the tag field of an existing bookmark."""
    allowed_tags = {"Important", "Read Later", "None"}
    if tag not in allowed_tags:
        logger.error("Invalid tag value: %s", tag)
        return False

    sql = "UPDATE bookmarks SET tag = %s WHERE id = %s"
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (tag, bookmark_id))
            conn.commit()
            updated = cursor.rowcount > 0
            cursor.close()
        if updated:
            logger.info("Tag updated to '%s' for bookmark id=%d", tag, bookmark_id)
        return updated
    except Error as exc:
        logger.error("Update failed, rolling back: %s", exc)
        return False


def update_bookmark_category(bookmark_id: int, category: str) -> bool:
    """Updates the category of a bookmark."""
    sql = "UPDATE bookmarks SET category = %s WHERE id = %s"
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (category, bookmark_id))
            conn.commit()
            updated = cursor.rowcount > 0
            cursor.close()
        return updated
    except Error as exc:
        logger.error("Category update failed: %s", exc)
        return False


def delete_bookmark(bookmark_id: int) -> bool:
    """Deletes a bookmark by its primary key."""
    sql = "DELETE FROM bookmarks WHERE id = %s"
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (bookmark_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            cursor.close()
        if deleted:
            logger.info("Bookmark id=%d deleted.", bookmark_id)
        return deleted
    except Error as exc:
        logger.error("Delete failed, rolling back: %s", exc)
        return False


def delete_all_bookmarks() -> bool:
    """Deletes every bookmark."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bookmarks")
            conn.commit()
            cursor.close()
        logger.info("All bookmarks deleted.")
        return True
    except Error as exc:
        logger.error("Delete all failed: %s", exc)
        return False


def get_all_categories() -> list:
    """Returns the distinct list of categories stored in the DB."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT DISTINCT category FROM bookmarks ORDER BY category")
            rows = cursor.fetchall()
            cursor.close()
        return [row["category"] for row in rows]
    except Error as exc:
        logger.error("Fetch categories failed: %s", exc)
        return []


def bookmark_exists(url: str) -> bool:
    """Checks if a URL is already bookmarked."""
    sql = "SELECT 1 FROM bookmarks WHERE url = %s LIMIT 1"
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (url,))
            row = cursor.fetchone()
            cursor.close()
        return row is not None
    except Error as exc:
        logger.error("Existence check failed: %s", exc)
        return False
