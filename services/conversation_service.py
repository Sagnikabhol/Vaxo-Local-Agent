"""
Vaxo Conversation Service

Manages conversation flow, message history, and integrates
with the LLM service and database for persistence.
"""

import logging
from typing import Optional

from config.settings import get_settings
from database.history_repository import HistoryRepository

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Manages conversation state and history.

    Maintains an in-memory conversation history and persists
    messages to SQLite via HistoryRepository.
    """

    def __init__(self, repository: Optional[HistoryRepository] = None):
        self._settings = get_settings()
        self._history: list[dict] = []
        self._repository = repository or HistoryRepository()
        self._conversation_id: int | None = None

    def start_new_conversation(self, title: str = "New Conversation") -> int:
        """Start a new conversation and return its ID."""
        self._history = []
        self._conversation_id = self._repository.create_conversation(title)
        return self._conversation_id

    def get_conversation_id(self) -> int | None:
        """Get the current conversation ID."""
        return self._conversation_id

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.

        Args:
            role: 'user' or 'assistant'
            content: The message content.
        """
        if role not in ("user", "assistant", "system"):
            logger.warning("Invalid role '%s', defaulting to 'user'", role)
            role = "user"

        message = {"role": role, "content": content}
        self._history.append(message)

        # Persist to database
        if self._conversation_id is not None:
            try:
                self._repository.save_message(
                    self._conversation_id, role, content
                )
            except Exception as e:
                logger.error("Error persisting message: %s", e)

    def get_history(self) -> list[dict]:
        """Get the full in-memory conversation history."""
        return list(self._history)

    def get_context(self, max_messages: int | None = None) -> list[dict]:
        """
        Get recent conversation context for LLM.

        Args:
            max_messages: Maximum messages to include. Defaults to settings value.

        Returns:
            List of recent messages for context.
        """
        limit = max_messages or self._settings.MAX_CONVERSATION_HISTORY
        return self._history[-limit:]

    def clear(self) -> None:
        """Clear the in-memory conversation history."""
        self._history = []
        logger.info("Conversation history cleared")

    def export_history(self) -> str:
        """Export conversation history as formatted text."""
        if not self._history:
            return "No conversation history."

        lines = ["=== Vaxo Conversation History ===\n"]
        for msg in self._history:
            role = msg["role"].capitalize()
            content = msg["content"]
            lines.append(f"[{role}]: {content}\n")
        lines.append("=== End of History ===")
        return "\n".join(lines)

    def get_past_conversations(self, limit: int = 20) -> list[dict]:
        """Get list of past conversations from the database."""
        return self._repository.get_conversations(limit)

    def load_conversation(self, conversation_id: int) -> list[dict]:
        """Load messages from a past conversation."""
        messages = self._repository.get_messages(conversation_id)
        self._conversation_id = conversation_id
        self._history = [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]
        return self._history

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation from the database."""
        return self._repository.delete_conversation(conversation_id)

    def get_stats(self) -> dict:
        """Get conversation statistics."""
        return self._repository.get_conversation_stats()
