"""
Tests for the LLM Service.

Tests connection handling, model listing, chat functionality,
and intent detection. All network calls to Ollama are mocked.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import requests
from services.llm_service import VaxoLLM


class TestVaxoLLM:
    """Tests for VaxoLLM service with mocked Ollama."""

    def test_create_service(self):
        """Test creating the LLM service."""
        llm = VaxoLLM()
        assert llm.base_url == "http://localhost:11434"
        assert llm.model == "tinyllama"

    def test_custom_config(self):
        """Test creating service with custom config."""
        llm = VaxoLLM(base_url="http://localhost:9999", model="phi3")
        assert llm.base_url == "http://localhost:9999"
        assert llm.model == "phi3"

    @patch("services.llm_service.requests.get")
    def test_check_connection_success(self, mock_get):
        """Test successful Ollama connection check."""
        mock_get.return_value = MagicMock(status_code=200)
        llm = VaxoLLM()
        assert llm.check_connection() is True

    @patch("services.llm_service.requests.get", side_effect=requests.ConnectionError)
    def test_check_connection_failure(self, mock_get):
        """Test connection check when Ollama is offline."""
        llm = VaxoLLM()
        assert llm.check_connection() is False

    @patch("services.llm_service.requests.get", side_effect=requests.Timeout)
    def test_check_connection_timeout(self, mock_get):
        """Test connection check timeout."""
        llm = VaxoLLM()
        assert llm.check_connection() is False

    @patch("services.llm_service.requests.get")
    def test_get_available_models(self, mock_get):
        """Test listing available models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "tinyllama:latest"},
                {"name": "phi3:mini"},
            ]
        }
        mock_get.return_value = mock_response

        llm = VaxoLLM()
        models = llm.get_available_models()
        assert "tinyllama:latest" in models
        assert "phi3:mini" in models

    @patch("services.llm_service.requests.get", side_effect=requests.ConnectionError)
    def test_get_models_offline(self, mock_get):
        """Test model listing when Ollama is offline."""
        llm = VaxoLLM()
        models = llm.get_available_models()
        assert models == []

    @patch("services.llm_service.requests.post")
    def test_chat_success(self, mock_post):
        """Test successful chat response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "Hello! I'm Vaxo, how can I help?"
            }
        }
        mock_post.return_value = mock_response

        llm = VaxoLLM()
        response = llm.chat("Hello")
        assert "Hello" in response or "Vaxo" in response or "help" in response

    @patch("services.llm_service.requests.post", side_effect=requests.ConnectionError)
    def test_chat_ollama_offline(self, mock_post):
        """Test chat response when Ollama is offline."""
        llm = VaxoLLM()
        response = llm.chat("Hello")
        assert "cannot connect" in response.lower() or "not running" in response.lower()
        # Must NOT pretend to generate a real response
        assert "ollama" in response.lower()

    @patch("services.llm_service.requests.post", side_effect=requests.Timeout)
    def test_chat_timeout(self, mock_post):
        """Test chat timeout handling."""
        llm = VaxoLLM()
        response = llm.chat("Hello")
        assert "too long" in response.lower() or "timeout" in response.lower()

    @patch("services.llm_service.requests.post")
    def test_chat_model_not_found(self, mock_post):
        """Test chat with non-existent model."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        llm = VaxoLLM()
        response = llm.chat("Hello")
        assert "not installed" in response.lower()

    def test_chat_empty_message(self):
        """Test chat with empty message."""
        llm = VaxoLLM()
        response = llm.chat("")
        assert "didn't receive" in response.lower() or "try again" in response.lower()

    def test_chat_whitespace_message(self):
        """Test chat with whitespace-only message."""
        llm = VaxoLLM()
        response = llm.chat("   ")
        assert "didn't receive" in response.lower() or "try again" in response.lower()

    @patch("services.llm_service.requests.post")
    def test_chat_empty_response(self, mock_post):
        """Test handling of empty LLM response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": ""}}
        mock_post.return_value = mock_response

        llm = VaxoLLM()
        response = llm.chat("Hello")
        assert "empty response" in response.lower()

    @patch("services.llm_service.requests.post")
    def test_chat_includes_conversation_history(self, mock_post):
        """Test that conversation history is sent to the model."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "I remember!"}
        }
        mock_post.return_value = mock_response

        llm = VaxoLLM()
        history = [
            {"role": "user", "content": "My name is Test"},
            {"role": "assistant", "content": "Nice to meet you, Test!"},
        ]
        llm.chat("What's my name?", history)

        # Check that the history was included in the request
        call_args = mock_post.call_args
        sent_messages = call_args[1]["json"]["messages"]
        # Should have: system + 2 history + 1 new message = 4
        assert len(sent_messages) == 4

    def test_set_model(self):
        """Test changing the model."""
        llm = VaxoLLM()
        llm.set_model("phi3:mini")
        assert llm.model == "phi3:mini"

    def test_get_model_info(self):
        """Test getting model info dict."""
        llm = VaxoLLM()
        info = llm.get_model_info()
        assert "model" in info
        assert "base_url" in info
        assert "connected" in info

    def test_demo_mode_response(self):
        """Test simulated responses when demo_mode is True."""
        llm = VaxoLLM(demo_mode=True)
        resp = llm.chat("Who are you?")
        assert "Portfolio Demo Mode" in resp
        assert "Vaxo" in resp

    def test_demo_mode_general_query(self):
        """Test general query fallback in demo mode."""
        llm = VaxoLLM(demo_mode=True)
        resp = llm.chat("Explain recursion")
        assert "Portfolio Demo Mode" in resp
        assert "recursion" in resp


# ─────────────────────────────────────────────
#   Intent Detection Tests
# ─────────────────────────────────────────────

class TestIntentDetection:
    """Tests for keyword-based intent detection."""

    def test_calculator_intent(self):
        """Test detecting calculator intent."""
        llm = VaxoLLM()
        result = llm.generate_intent("open calculator")
        assert result["intent"] == "open_calculator"

    def test_time_intent(self):
        """Test detecting time intent."""
        llm = VaxoLLM()
        result = llm.generate_intent("what time is it?")
        assert result["intent"] == "get_time"

    def test_system_info_intent(self):
        """Test detecting system info intent."""
        llm = VaxoLLM()
        result = llm.generate_intent("show me system info")
        assert result["intent"] == "get_system_info"

    def test_notepad_intent(self):
        """Test detecting notepad intent."""
        llm = VaxoLLM()
        result = llm.generate_intent("open notepad")
        assert result["intent"] == "open_notepad"

    def test_browser_intent(self):
        """Test detecting browser intent."""
        llm = VaxoLLM()
        result = llm.generate_intent("open the browser")
        assert result["intent"] == "open_browser"

    def test_stop_voice_intent(self):
        """Test detecting stop voice intent."""
        llm = VaxoLLM()
        result = llm.generate_intent("stop listening")
        assert result["intent"] == "stop_voice"

    def test_chat_intent_fallback(self):
        """Test that unmatched input defaults to chat."""
        llm = VaxoLLM()
        result = llm.generate_intent("What is quantum computing?")
        assert result["intent"] == "chat"

    def test_intent_case_insensitive(self):
        """Test that intent detection is case-insensitive."""
        llm = VaxoLLM()
        result = llm.generate_intent("OPEN CALCULATOR")
        assert result["intent"] == "open_calculator"
