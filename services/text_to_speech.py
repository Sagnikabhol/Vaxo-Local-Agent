"""
Vaxo Text-to-Speech Service

Provides voice output using pyttsx3 (offline, no internet required).
Thread-safe with configurable voice settings.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_pyttsx3_available = False

try:
    import pyttsx3
    _pyttsx3_available = True
except ImportError:
    pyttsx3 = None  # type: ignore
    logger.warning("pyttsx3 not installed. Voice output unavailable.")


class TextToSpeechService:
    """
    Handles text-to-speech output using pyttsx3.

    This works completely offline — no internet required.
    Uses the system's built-in speech synthesis engine (SAPI5 on Windows).
    """

    def __init__(self):
        self._engine: Optional[object] = None
        self._lock = threading.Lock()
        self._initialized = False

        if _pyttsx3_available:
            self._init_engine()

    def _init_engine(self) -> None:
        """Initialize the TTS engine with default settings."""
        try:
            from config.settings import get_settings
            settings = get_settings()

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", settings.TTS_RATE)
            self._engine.setProperty("volume", settings.TTS_VOLUME)
            self._initialized = True
            logger.info("TTS engine initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize TTS engine: %s", e)
            self._engine = None
            self._initialized = False

    def is_available(self) -> bool:
        """Check if text-to-speech is available."""
        return _pyttsx3_available and self._initialized and self._engine is not None

    def speak(self, text: str) -> bool:
        """
        Speak the given text aloud.

        Args:
            text: The text to speak.

        Returns:
            True if speech was successful, False otherwise.
        """
        if not self.is_available() or self._engine is None:
            logger.warning("TTS not available, cannot speak")
            return False

        if not text.strip():
            return False

        # Clean text for speech (remove markdown formatting)
        clean_text = text.replace("**", "").replace("*", "")
        clean_text = clean_text.replace("`", "").replace("#", "")
        clean_text = clean_text.replace("⚠️", "Warning: ")
        clean_text = clean_text.replace("🔴", "Error: ")
        clean_text = clean_text.replace("✅", "")
        clean_text = clean_text.replace("⏱️", "")

        # Truncate very long text for speech
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "... I'll stop here. You can read the full response."

        try:
            with self._lock:
                self._engine.say(clean_text)
                self._engine.runAndWait()
            return True
        except RuntimeError:
            # Engine might be busy, try reinitializing
            try:
                self._init_engine()
                if self._engine:
                    with self._lock:
                        self._engine.say(clean_text)
                        self._engine.runAndWait()
                    return True
            except Exception as e:
                logger.error("TTS error after reinit: %s", e)
            return False
        except Exception as e:
            logger.error("TTS speak error: %s", e)
            return False

    def stop(self) -> None:
        """Stop current speech output."""
        if self._engine is not None:
            try:
                with self._lock:
                    self._engine.stop()
            except Exception as e:
                logger.error("TTS stop error: %s", e)

    def set_rate(self, rate: int) -> None:
        """Set speech rate (words per minute). Default: 175."""
        if self._engine is not None:
            try:
                self._engine.setProperty("rate", max(50, min(400, rate)))
            except Exception as e:
                logger.error("Error setting TTS rate: %s", e)

    def set_volume(self, volume: float) -> None:
        """Set speech volume (0.0 to 1.0)."""
        if self._engine is not None:
            try:
                self._engine.setProperty("volume", max(0.0, min(1.0, volume)))
            except Exception as e:
                logger.error("Error setting TTS volume: %s", e)

    def get_voices(self) -> list[dict]:
        """Get list of available system voices."""
        if self._engine is None:
            return []
        try:
            voices = self._engine.getProperty("voices")
            return [
                {
                    "id": voice.id,
                    "name": voice.name,
                    "languages": getattr(voice, "languages", []),
                }
                for voice in voices
            ]
        except Exception as e:
            logger.error("Error getting voices: %s", e)
            return []

    def set_voice(self, voice_id: str) -> None:
        """Set the active voice by ID."""
        if self._engine is not None:
            try:
                self._engine.setProperty("voice", voice_id)
            except Exception as e:
                logger.error("Error setting voice: %s", e)

    def get_status(self) -> dict[str, str]:
        """Get current TTS service status."""
        return {
            "library_installed": str(_pyttsx3_available),
            "engine_initialized": str(self._initialized),
            "available": str(self.is_available()),
            "engine": "pyttsx3 / SAPI5 (offline)" if self.is_available() else "Not available",
            "voices_count": str(len(self.get_voices())),
        }
