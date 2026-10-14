"""
Vaxo Speech-to-Text Service

Provides voice input using the SpeechRecognition library.
Uses Google Web Speech API for transcription (requires internet).
Handles missing dependencies and audio device errors gracefully.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Track library availability
_sr_available = False
_pyaudio_available = False

try:
    import speech_recognition as sr
    _sr_available = True
except ImportError:
    sr = None  # type: ignore
    logger.warning("SpeechRecognition not installed. Voice input unavailable.")

try:
    import pyaudio
    _pyaudio_available = True
except ImportError:
    pyaudio = None  # type: ignore
    logger.info("PyAudio not installed. Microphone access may be limited.")


class VoiceInputError(Exception):
    """Custom exception for voice input errors."""
    pass


class SpeechToTextService:
    """
    Handles microphone input and speech-to-text transcription.

    Note: Uses Google Web Speech API which requires an internet connection.
    This is NOT offline speech recognition.
    """

    def __init__(self):
        self._recognizer: Optional[object] = None
        if _sr_available:
            self._recognizer = sr.Recognizer()

    def is_available(self) -> bool:
        """Check if speech recognition is available on this system."""
        if not _sr_available:
            return False
        # Check if we can create a microphone (requires PyAudio or system audio)
        try:
            if sr is not None:
                mic = sr.Microphone()
                return True
        except (OSError, AttributeError, Exception) as e:
            logger.warning("Microphone not available: %s", e)
            return False
        return False

    def listen(self, timeout: int = 8, phrase_time_limit: int = 15) -> str:
        """
        Listen for speech and return transcribed text.

        Uses Google Web Speech API (requires internet connection).

        Args:
            timeout: Maximum seconds to wait for speech to start (default 8s).
            phrase_time_limit: Maximum seconds of speech to capture (default 15s).

        Returns:
            Transcribed text string.

        Raises:
            VoiceInputError: If recognition fails or is unavailable.
        """
        if not _sr_available or sr is None or self._recognizer is None:
            raise VoiceInputError(
                "SpeechRecognition library is not installed. "
                "Install it with: pip install SpeechRecognition"
            )

        recognizer = self._recognizer
        recognizer.pause_threshold = 0.8
        recognizer.non_speaking_duration = 0.5

        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise briefly
                recognizer.adjust_for_ambient_noise(source, duration=0.4)

                # Listen for speech
                logger.info("Listening for speech...")
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )

            # Transcribe using Google Web Speech API (requires internet)
            text = recognizer.recognize_google(audio)
            logger.info("Transcribed: %s", text)
            return str(text)

        except sr.WaitTimeoutError:
            raise VoiceInputError(
                "No speech detected. Please speak clearly into your microphone."
            )
        except sr.UnknownValueError:
            raise VoiceInputError(
                "Could not understand the audio. Please try speaking more clearly."
            )
        except sr.RequestError as e:
            raise VoiceInputError(
                f"Speech recognition service error (internet required): {e}"
            )
        except OSError as e:
            raise VoiceInputError(
                f"Microphone error: {e}. Check that a microphone is connected "
                "and PyAudio is installed."
            )
        except Exception as e:
            logger.error("Unexpected speech recognition error: %s", e)
            raise VoiceInputError(f"Voice input error: {e}")

    def get_microphone_list(self) -> list[str]:
        """Get list of available microphone device names."""
        if not _sr_available or sr is None:
            return []
        try:
            return sr.Microphone.list_microphone_names()
        except (OSError, AttributeError, Exception) as e:
            logger.warning("Cannot list microphones: %s", e)
            return []

    def get_status(self) -> dict[str, str]:
        """Get current status of the speech-to-text service."""
        available = self.is_available()
        return {
            "library_installed": str(_sr_available),
            "pyaudio_installed": str(_pyaudio_available),
            "microphone_available": str(available),
            "engine": "Google Web Speech API (requires internet)" if _sr_available else "Not available",
            "microphones_found": str(len(self.get_microphone_list())),
        }
