"""
Vaxo LLM Service

Connects to a locally running Ollama instance for AI chat inference.
Handles connection errors, timeouts, and model unavailability gracefully.
Never pretends to generate a response when Ollama is unavailable.
"""

import json
import logging
from typing import Any

import requests

from config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Raised when the LLM service encounters an error."""
    pass


class VaxoLLM:
    """Service for interacting with locally-hosted LLM via Ollama."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        demo_mode: bool | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.system_prompt = settings.SYSTEM_PROMPT
        self.demo_mode = demo_mode if demo_mode is not None else settings.DEMO_MODE

    def check_connection(self) -> bool:
        """Check if Ollama service is running and reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            logger.warning("Ollama is not reachable at %s", self.base_url)
            return False
        except requests.Timeout:
            logger.warning("Ollama connection timed out")
            return False
        except Exception as e:
            logger.error("Unexpected error checking Ollama: %s", e)
            return False

    def get_available_models(self) -> list[str]:
        """Get list of models installed in Ollama."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return [m["name"] for m in models if "name" in m]
        except requests.ConnectionError:
            logger.warning("Cannot reach Ollama to list models")
            return []
        except requests.Timeout:
            logger.warning("Timeout listing Ollama models")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Error parsing Ollama model list: %s", e)
            return []
        except Exception as e:
            logger.error("Unexpected error listing models: %s", e)
            return []

    def chat(self, message: str, conversation_history: list[dict] | None = None) -> str:
        """
        Send a message to the local LLM and get a response.

        Args:
            message: The user's message.
            conversation_history: Previous messages for context.

        Returns:
            The assistant's response text, or an error message explaining
            why the local AI is unavailable.
        """
        if not message.strip():
            return "I didn't receive a message. Could you try again?"

        if self.demo_mode:
            return self._generate_demo_response(message)

        # Build message list with system prompt and history
        messages = [{"role": "system", "content": self.system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )

            if resp.status_code == 404:
                return (
                    f"⚠️ Model '{self.model}' is not installed in Ollama. "
                    f"Please run: ollama pull {self.model}"
                )

            resp.raise_for_status()
            data = resp.json()

            # Extract response content
            response_message = data.get("message", {})
            content = response_message.get("content", "").strip()

            if not content:
                return "The AI model returned an empty response. Please try again."

            return content

        except requests.ConnectionError:
            return (
                "🔴 Cannot connect to Ollama. The local AI service is not running.\n\n"
                "**To start Ollama:**\n"
                "1. Install Ollama from https://ollama.ai\n"
                "2. Run `ollama serve` in a terminal\n"
                f"3. Pull a model: `ollama pull {self.model}`\n\n"
                "I can still help with desktop actions like opening apps, "
                "checking the time, and system info. Or enable **Demo Mode** in Settings."
            )
        except requests.Timeout:
            return (
                "⏱️ The AI model took too long to respond. "
                "This may happen with large models on limited hardware. "
                "Try a smaller model like 'tinyllama' or increase the timeout."
            )
        except json.JSONDecodeError:
            return "⚠️ Received an invalid response from Ollama. The service may be starting up."
        except requests.HTTPError as e:
            return f"⚠️ Ollama returned an error: {e}"
        except Exception as e:
            logger.error("Unexpected LLM error: %s", e)
            return f"⚠️ An unexpected error occurred: {str(e)}"

    def _generate_demo_response(self, message: str) -> str:
        """
        Generate a simulated local AI response for portfolio demonstration
        when running without an active Ollama instance.
        """
        msg_lower = message.lower().strip()

        if any(w in msg_lower for w in ["who are you", "what is vaxo", "introduce yourself"]):
            return (
                "🤖 **[Portfolio Demo Mode]** I am **Vaxo**, a local voice AI & desktop automation assistant. "
                "I am built with Python, Ollama for local LLM inference, and safe allowlisted OS automation."
            )
        elif any(w in msg_lower for w in ["what can you do", "features", "capabilities", "help"]):
            return (
                "⚡ **[Portfolio Demo Mode]** Here is what I can do for you:\n"
                "- **Open Apps:** Say *'open calculator'*, *'open notepad'*, or *'open browser'*\n"
                "- **System Stats:** Say *'system info'* or *'cpu usage'*\n"
                "- **Time & Date:** Say *'what time is it'* or *'date today'*\n"
                "- **Voice Controls:** Push-to-talk mic input and offline voice replies\n"
                "- **Local AI Chat:** Answer general questions privately with Ollama\n"
                "- **History:** View past conversations and action logs in the sidebar!"
            )
        elif any(w in msg_lower for w in ["how are you", "how's it going", "how do you do"]):
            return (
                "😊 **[Portfolio Demo Mode]** I'm doing great, thank you! All systems are online and ready to assist you. "
                "What would you like me to do?"
            )
        elif any(w in msg_lower for w in ["joke", "funny"]):
            return (
                "😄 **[Portfolio Demo Mode]** Why do programmers prefer dark mode?\n\n"
                "Because light attracts bugs!"
            )
        elif any(w in msg_lower for w in ["stack", "technology", "built with", "architecture"]):
            return (
                "🛠️ **[Portfolio Demo Mode]** Vaxo is built with Python 3.12, Streamlit for the responsive UI, "
                "Ollama for local LLM inference, SQLite with WAL mode for message persistence, and pyttsx3 for offline speech synthesis."
            )
        elif any(w in msg_lower for w in ["mca", "project", "developer", "creator", "portfolio"]):
            return (
                "🎓 **[Portfolio Demo Mode]** This project is built as a portfolio piece for MCA graduate roles in "
                "Python development, backend engineering, and local AI integration, focusing on security and clean architecture."
            )
        elif any(w in msg_lower for w in ["hello", "hi", "hey", "greetings"]):
            return (
                "👋 **[Portfolio Demo Mode]** Hello! I'm Vaxo, your local voice AI assistant. "
                "Try saying *'open calculator'*, *'what time is it'*, *'system info'*, or ask me anything!"
            )
        else:
            return (
                f"💡 **[Portfolio Demo Mode]** I received your query: *\"{message}\"*\n\n"
                "In local production mode, this query is processed 100% privately on your machine by your local Ollama LLM "
                f"(`{self.model}`) with zero external API calls. "
                "To enable full neural inference, install Ollama and run `ollama pull tinyllama`."
            )

    def generate_intent(self, message: str) -> dict[str, Any]:
        """
        Attempt to classify the user's intent using keyword matching first,
        then fall back to LLM classification if available.

        Returns:
            dict with 'intent' (action name or 'chat') and 'args' (dict).
        """
        # Quick keyword-based intent detection (works without LLM)
        msg_lower = message.lower().strip()

        intent_keywords = {
            "open_calculator": ["open calculator", "calculator", "calc", "open calc", "cal culator", "open cal culator"],
            "open_notepad": ["open notepad", "notepad", "note pad", "open note pad", "text editor", "open editor", "open notes", "notes"],
            "open_browser": ["open browser", "browser", "open chrome", "open edge", "internet", "web browser", "open google"],
            "get_time": ["what time", "current time", "what's the time", "tell me the time",
                         "time now", "date today", "what date", "today's date", "clock"],
            "get_system_info": ["system info", "system status", "cpu usage", "ram usage",
                                "memory usage", "disk space", "hardware info", "system report"],
            "stop_voice": ["stop listening", "stop voice", "mute", "be quiet",
                           "silence", "stop speaking", "shut up"],
            "show_history": ["show history", "task history", "conversation history",
                             "what did we talk about", "previous conversations"],
        }

        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in msg_lower:
                    return {"intent": intent, "args": {}}

        # Default to chat intent
        return {"intent": "chat", "args": {}}

    def set_model(self, model_name: str) -> None:
        """Change the active model."""
        self.model = model_name
        logger.info("Model changed to: %s", model_name)

    def get_model_info(self) -> dict[str, str]:
        """Get current model configuration info."""
        connected = self.check_connection()
        models = self.get_available_models() if connected else []
        return {
            "model": self.model,
            "base_url": self.base_url,
            "connected": str(connected),
            "available_models": ", ".join(models) if models else "None found",
            "timeout": str(self.timeout),
        }
