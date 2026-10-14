"""
Vaxo History Repository

SQLite-based persistent storage for conversations, messages, and action logs.
Creates database and tables automatically on first use.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import get_settings

logger = logging.getLogger(__name__)


class HistoryRepository:
    """Manages persistent conversation and action history using SQLite."""

    def __init__(self, db_path: str | None = None):
        settings = get_settings()
        self.db_path = db_path or settings.DB_PATH

        # Ensure the directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_database(self) -> None:
        """Create tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        started_at TEXT NOT NULL,
                        title TEXT DEFAULT 'New Conversation',
                        updated_at TEXT
                    );

                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id INTEGER NOT NULL,
                        role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    );

                    CREATE TABLE IF NOT EXISTS action_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_name TEXT NOT NULL,
                        args TEXT DEFAULT '{}',
                        result TEXT DEFAULT '',
                        success INTEGER NOT NULL DEFAULT 0,
                        timestamp TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_messages_conversation
                        ON messages(conversation_id);

                    CREATE INDEX IF NOT EXISTS idx_action_log_timestamp
                        ON action_log(timestamp);
                """)
            logger.info("Database initialized at %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("Database initialization error: %s", e)
            raise

    def create_conversation(self, title: str = "New Conversation") -> int:
        """Create a new conversation and return its ID."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO conversations (started_at, title, updated_at) VALUES (?, ?, ?)",
                    (now, title, now),
                )
                conv_id = cursor.lastrowid
                logger.info("Created conversation %d: %s", conv_id, title)
                return conv_id
        except sqlite3.Error as e:
            logger.error("Error creating conversation: %s", e)
            raise

    def save_message(self, conversation_id: int, role: str, content: str) -> None:
        """Save a message to the database."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO messages (conversation_id, role, content, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (conversation_id, role, content, now),
                )
                # Update conversation timestamp
                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (now, conversation_id),
                )
        except sqlite3.Error as e:
            logger.error("Error saving message: %s", e)

    def get_messages(self, conversation_id: int) -> list[dict]:
        """Get all messages for a conversation."""
        try:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT role, content, timestamp FROM messages "
                    "WHERE conversation_id = ? ORDER BY id ASC",
                    (conversation_id,),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Error getting messages: %s", e)
            return []

    def get_conversations(self, limit: int = 20) -> list[dict]:
        """Get recent conversations."""
        try:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT id, started_at, title, updated_at FROM conversations "
                    "ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Error getting conversations: %s", e)
            return []

    def log_action(self, action_name: str, args: dict, result: str, success: bool) -> None:
        """Log an executed action."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO action_log (action_name, args, result, success, timestamp) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (action_name, json.dumps(args), result, int(success), now),
                )
        except sqlite3.Error as e:
            logger.error("Error logging action: %s", e)

    def get_action_log(self, limit: int = 50) -> list[dict]:
        """Get recent action log entries."""
        try:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT action_name, args, result, success, timestamp "
                    "FROM action_log ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                results = []
                for row in rows:
                    entry = dict(row)
                    try:
                        entry["args"] = json.loads(entry["args"])
                    except (json.JSONDecodeError, TypeError):
                        entry["args"] = {}
                    entry["success"] = bool(entry["success"])
                    results.append(entry)
                return results
        except sqlite3.Error as e:
            logger.error("Error getting action log: %s", e)
            return []

    def get_conversation_stats(self) -> dict:
        """Get aggregate statistics about conversations and actions."""
        try:
            with self._get_connection() as conn:
                conv_count = conn.execute(
                    "SELECT COUNT(*) FROM conversations"
                ).fetchone()[0]
                msg_count = conn.execute(
                    "SELECT COUNT(*) FROM messages"
                ).fetchone()[0]
                action_count = conn.execute(
                    "SELECT COUNT(*) FROM action_log"
                ).fetchone()[0]
                success_count = conn.execute(
                    "SELECT COUNT(*) FROM action_log WHERE success = 1"
                ).fetchone()[0]
                return {
                    "total_conversations": conv_count,
                    "total_messages": msg_count,
                    "total_actions": action_count,
                    "successful_actions": success_count,
                }
        except sqlite3.Error as e:
            logger.error("Error getting stats: %s", e)
            return {
                "total_conversations": 0,
                "total_messages": 0,
                "total_actions": 0,
                "successful_actions": 0,
            }

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and its messages."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM messages WHERE conversation_id = ?",
                    (conversation_id,),
                )
                conn.execute(
                    "DELETE FROM conversations WHERE id = ?",
                    (conversation_id,),
                )
                return True
        except sqlite3.Error as e:
            logger.error("Error deleting conversation: %s", e)
            return False
