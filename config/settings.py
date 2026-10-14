"""
Vaxo Configuration Settings

Loads configuration from environment variables and .env file.
Provides a centralized settings object for the entire application.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class Settings:
    """Application-wide configuration settings."""

    # Ollama LLM settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "tinyllama"
    OLLAMA_TIMEOUT: int = 60

    # Conversation settings
    MAX_CONVERSATION_HISTORY: int = 20
    SYSTEM_PROMPT: str = (
        "You are Vaxo, a helpful and concise AI desktop assistant. "
        "You answer questions clearly and briefly. "
        "When asked to perform actions, describe what you're doing. "
        "If you cannot do something, explain why honestly. "
        "Keep responses under 3 sentences unless more detail is requested."
    )

    # Text-to-Speech settings
    TTS_ENABLED: bool = True
    TTS_RATE: int = 175
    TTS_VOLUME: float = 0.9

    # Speech-to-Text settings
    STT_ENABLED: bool = True

    # Database settings
    DB_PATH: str = "data/vaxo_history.db"

    # Application metadata
    APP_NAME: str = "Vaxo"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Local Voice AI & Desktop Automation Agent"

    # Debug & Demo mode
    DEBUG: bool = False
    DEMO_MODE: bool = False

    def __post_init__(self):
        """Override defaults with environment variables if set."""
        env_mapping = {
            "OLLAMA_BASE_URL": str,
            "OLLAMA_MODEL": str,
            "OLLAMA_TIMEOUT": int,
            "MAX_CONVERSATION_HISTORY": int,
            "SYSTEM_PROMPT": str,
            "TTS_ENABLED": lambda v: v.lower() in ("true", "1", "yes"),
            "TTS_RATE": int,
            "TTS_VOLUME": float,
            "STT_ENABLED": lambda v: v.lower() in ("true", "1", "yes"),
            "DB_PATH": str,
            "DEBUG": lambda v: v.lower() in ("true", "1", "yes"),
            "DEMO_MODE": lambda v: v.lower() in ("true", "1", "yes"),
        }

        for attr, converter in env_mapping.items():
            env_val = os.getenv(attr)
            if env_val is not None:
                try:
                    setattr(self, attr, converter(env_val))
                except (ValueError, TypeError):
                    pass  # Keep default if conversion fails


# Singleton settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
