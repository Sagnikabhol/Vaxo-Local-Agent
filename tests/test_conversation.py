"""
Tests for Conversation Service and History Repository.

Tests database operations, conversation management,
and message persistence using temporary SQLite databases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from database.history_repository import HistoryRepository
from services.conversation_service import ConversationService


# ─────────────────────────────────────────────
#   History Repository Tests
# ─────────────────────────────────────────────

class TestHistoryRepository:
    """Tests for SQLite history repository."""

    def test_create_repository(self, temp_db):
        """Test repository creation and table initialization."""
        repo = HistoryRepository(db_path=temp_db)
        assert Path(temp_db).exists()

    def test_create_conversation(self, temp_db):
        """Test creating a new conversation."""
        repo = HistoryRepository(db_path=temp_db)
        conv_id = repo.create_conversation("Test Chat")
        assert conv_id is not None
        assert conv_id > 0

    def test_save_and_get_messages(self, temp_db):
        """Test saving and retrieving messages."""
        repo = HistoryRepository(db_path=temp_db)
        conv_id = repo.create_conversation("Test")

        repo.save_message(conv_id, "user", "Hello!")
        repo.save_message(conv_id, "assistant", "Hi there!")

        messages = repo.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello!"
        assert messages[1]["role"] == "assistant"

    def test_get_conversations(self, temp_db):
        """Test listing conversations."""
        repo = HistoryRepository(db_path=temp_db)
        repo.create_conversation("Chat 1")
        repo.create_conversation("Chat 2")
        repo.create_conversation("Chat 3")

        convs = repo.get_conversations(limit=10)
        assert len(convs) == 3

    def test_get_conversations_limit(self, temp_db):
        """Test that conversation listing respects limit."""
        repo = HistoryRepository(db_path=temp_db)
        for i in range(10):
            repo.create_conversation(f"Chat {i}")

        convs = repo.get_conversations(limit=5)
        assert len(convs) == 5

    def test_log_action(self, temp_db):
        """Test logging an action."""
        repo = HistoryRepository(db_path=temp_db)
        repo.log_action("open_calculator", {}, "Opened calculator", True)
        repo.log_action("open_browser", {"url": "https://google.com"}, "Opened browser", True)
        repo.log_action("invalid_action", {}, "Not found", False)

        log = repo.get_action_log(limit=10)
        assert len(log) == 3

    def test_action_log_preserves_success_status(self, temp_db):
        """Test that action success status is preserved."""
        repo = HistoryRepository(db_path=temp_db)
        repo.log_action("test_action", {}, "Success", True)
        repo.log_action("test_fail", {}, "Failed", False)

        log = repo.get_action_log(limit=10)
        # Log is ordered DESC, so most recent first
        assert log[0]["success"] is False
        assert log[1]["success"] is True

    def test_conversation_stats(self, temp_db):
        """Test getting aggregate statistics."""
        repo = HistoryRepository(db_path=temp_db)

        conv1 = repo.create_conversation("Chat 1")
        repo.save_message(conv1, "user", "Hello")
        repo.save_message(conv1, "assistant", "Hi")

        conv2 = repo.create_conversation("Chat 2")
        repo.save_message(conv2, "user", "Bye")

        repo.log_action("test", {}, "OK", True)

        stats = repo.get_conversation_stats()
        assert stats["total_conversations"] == 2
        assert stats["total_messages"] == 3
        assert stats["total_actions"] == 1
        assert stats["successful_actions"] == 1

    def test_delete_conversation(self, temp_db):
        """Test deleting a conversation and its messages."""
        repo = HistoryRepository(db_path=temp_db)
        conv_id = repo.create_conversation("To Delete")
        repo.save_message(conv_id, "user", "This will be deleted")

        assert repo.delete_conversation(conv_id) is True

        messages = repo.get_messages(conv_id)
        assert len(messages) == 0

        convs = repo.get_conversations()
        assert len(convs) == 0

    def test_empty_database_stats(self, temp_db):
        """Test stats on empty database."""
        repo = HistoryRepository(db_path=temp_db)
        stats = repo.get_conversation_stats()
        assert stats["total_conversations"] == 0
        assert stats["total_messages"] == 0


# ─────────────────────────────────────────────
#   Conversation Service Tests
# ─────────────────────────────────────────────

class TestConversationService:
    """Tests for the conversation service."""

    def test_create_service(self, temp_db):
        """Test creating a conversation service."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        assert service is not None

    def test_start_new_conversation(self, temp_db):
        """Test starting a new conversation."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        conv_id = service.start_new_conversation("Test Session")
        assert conv_id > 0

    def test_add_and_get_messages(self, temp_db):
        """Test adding and retrieving messages."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        service.start_new_conversation("Test")

        service.add_message("user", "Hello Vaxo")
        service.add_message("assistant", "Hello! How can I help?")

        history = service.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_get_context_with_limit(self, temp_db):
        """Test getting limited conversation context."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        service.start_new_conversation("Test")

        for i in range(10):
            service.add_message("user", f"Message {i}")

        context = service.get_context(max_messages=5)
        assert len(context) == 5

    def test_clear_history(self, temp_db):
        """Test clearing conversation history."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        service.start_new_conversation("Test")

        service.add_message("user", "Test message")
        assert len(service.get_history()) == 1

        service.clear()
        assert len(service.get_history()) == 0

    def test_export_history(self, temp_db):
        """Test exporting conversation as text."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        service.start_new_conversation("Test")

        service.add_message("user", "What time is it?")
        service.add_message("assistant", "It's 3 PM.")

        export = service.export_history()
        assert "What time is it?" in export
        assert "3 PM" in export
        assert "User" in export
        assert "Assistant" in export

    def test_export_empty_history(self, temp_db):
        """Test exporting when no history exists."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        export = service.export_history()
        assert "no conversation" in export.lower()

    def test_invalid_role_defaults_to_user(self, temp_db):
        """Test that invalid roles default to 'user'."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        service.start_new_conversation("Test")

        service.add_message("invalid_role", "Test")
        history = service.get_history()
        assert history[0]["role"] == "user"

    def test_past_conversations(self, temp_db):
        """Test loading past conversations."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)

        service.start_new_conversation("Session 1")
        service.add_message("user", "Hello 1")

        service.start_new_conversation("Session 2")
        service.add_message("user", "Hello 2")

        past = service.get_past_conversations(limit=10)
        assert len(past) == 2

    def test_messages_persisted_to_database(self, temp_db):
        """Test that messages are saved to the database."""
        repo = HistoryRepository(db_path=temp_db)
        service = ConversationService(repository=repo)
        conv_id = service.start_new_conversation("Persist Test")

        service.add_message("user", "Persisted message")

        # Read directly from database
        db_messages = repo.get_messages(conv_id)
        assert len(db_messages) == 1
        assert db_messages[0]["content"] == "Persisted message"
