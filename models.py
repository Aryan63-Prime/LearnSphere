"""
LearnSphere — Database Models
SQLite-backed storage for bookmarks and usage tracking.
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'learnsphere.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT    NOT NULL,
                topic       TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                metadata    TEXT    DEFAULT '{}',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS usage_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                modality    TEXT    NOT NULL,
                topic       TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_bookmarks_type ON bookmarks(type);
            CREATE INDEX IF NOT EXISTS idx_usage_modality ON usage_log(modality);
            CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_log(created_at);
        """)


# ── Bookmarks ─────────────────────────────────────────────────

def add_bookmark(bm_type: str, topic: str, content: str, metadata: str = '{}') -> dict:
    """Save a bookmark."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO bookmarks (type, topic, content, metadata) VALUES (?, ?, ?, ?)",
            (bm_type, topic, content, metadata)
        )
        return {'success': True, 'id': cursor.lastrowid}


def get_bookmarks(bm_type: str = None, limit: int = 50) -> list:
    """Get bookmarks, optionally filtered by type."""
    with get_db() as conn:
        if bm_type:
            rows = conn.execute(
                "SELECT * FROM bookmarks WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (bm_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM bookmarks ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def delete_bookmark(bm_id: int) -> dict:
    """Delete a bookmark by ID."""
    with get_db() as conn:
        conn.execute("DELETE FROM bookmarks WHERE id = ?", (bm_id,))
        return {'success': True}


# ── Usage Tracking ─────────────────────────────────────────────

def log_usage(modality: str, topic: str) -> dict:
    """Log a usage event."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO usage_log (modality, topic) VALUES (?, ?)",
            (modality, topic)
        )
        return {'success': True}


def get_usage_stats() -> dict:
    """Get aggregated usage statistics."""
    with get_db() as conn:
        # Total per modality
        modality_counts = {}
        for row in conn.execute(
            "SELECT modality, COUNT(*) as count FROM usage_log GROUP BY modality"
        ).fetchall():
            modality_counts[row['modality']] = row['count']

        # Recent topics
        recent = conn.execute(
            "SELECT modality, topic, created_at FROM usage_log ORDER BY created_at DESC LIMIT 20"
        ).fetchall()

        # Weekly counts (last 7 days)
        weekly = conn.execute("""
            SELECT strftime('%w', created_at) as day, COUNT(*) as count
            FROM usage_log
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY day
        """).fetchall()
        weekly_data = [0] * 7
        for row in weekly:
            weekly_data[int(row['day'])] = row['count']

        return {
            'modality_counts': modality_counts,
            'recent': [dict(r) for r in recent],
            'weekly': weekly_data,
            'total': sum(modality_counts.values()),
        }


# Initialize on import
init_db()
