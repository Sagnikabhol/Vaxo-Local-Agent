"""
Vaxo — Local Voice AI & Desktop Automation Agent

Main Streamlit application with a polished, modern dark interface.
Provides chat, voice interaction, desktop automation, and conversation history.
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from config.settings import get_settings
from services.llm_service import VaxoLLM
from services.conversation_service import ConversationService
from services.text_to_speech import TextToSpeechService
from automation.windows_actions import create_default_registry
from database.history_repository import HistoryRepository

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#   Page Configuration
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Vaxo — AI Desktop Assistant",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
#   Custom CSS — Premium Dark Theme
# ─────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
        /* ── Global Theme ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        .stApp {
            background: linear-gradient(160deg, #0a0e1a 0%, #111827 50%, #0d1321 100%);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* ── Sidebar ── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
            border-right: 1px solid rgba(99, 102, 241, 0.15);
        }

        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2,
        section[data-testid="stSidebar"] .stMarkdown h3 {
            color: #c7d2fe;
        }

        /* ── Voice Orb ── */
        @keyframes pulse-ring {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.15); opacity: 0.25; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.4), 0 0 35px rgba(139, 92, 246, 0.25); }
            50% { box-shadow: 0 0 35px rgba(99, 102, 241, 0.8), 0 0 60px rgba(139, 92, 246, 0.5); }
        }
        @keyframes wave-bar {
            0%, 100% { height: 6px; }
            50% { height: 28px; }
        }

        .voice-orb-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 16px 0 10px;
        }

        .voice-orb {
            width: 88px;
            height: 88px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            position: relative;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .voice-orb.idle {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            box-shadow: 0 0 18px rgba(99, 102, 241, 0.35);
        }

        .voice-orb.listening {
            background: linear-gradient(135deg, #7f1d1d 0%, #dc2626 100%);
            animation: glow 1.2s ease-in-out infinite;
        }

        .voice-orb.processing {
            background: linear-gradient(135deg, #4338ca 0%, #7c3aed 100%);
            animation: glow 0.8s ease-in-out infinite;
        }

        .voice-orb.speaking {
            background: linear-gradient(135deg, #4f46e5 0%, #8b5cf6 100%);
            animation: glow 1.6s ease-in-out infinite;
        }

        .voice-orb::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            border: 2px solid rgba(139, 92, 246, 0.4);
            animation: pulse-ring 2.2s ease-in-out infinite;
        }

        /* ── Audio Equalizer Sound Wave ── */
        .sound-wave {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            height: 32px;
            margin-top: 10px;
        }
        .sound-wave .bar {
            width: 4px;
            border-radius: 3px;
            background: linear-gradient(180deg, #818cf8 0%, #c084fc 100%);
            animation: wave-bar 1.2s ease-in-out infinite;
        }
        .sound-wave .bar:nth-child(1) { animation-delay: 0.1s; }
        .sound-wave .bar:nth-child(2) { animation-delay: 0.3s; }
        .sound-wave .bar:nth-child(3) { animation-delay: 0.5s; }
        .sound-wave .bar:nth-child(4) { animation-delay: 0.2s; }
        .sound-wave .bar:nth-child(5) { animation-delay: 0.4s; }

        /* ── Status Badges ── */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 500;
            letter-spacing: 0.02em;
        }
        .status-online { background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3); }
        .status-offline { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); }
        .status-idle { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); }

        /* ── Chat Messages ── */
        .chat-message {
            padding: 14px 18px;
            border-radius: 14px;
            margin: 8px 0;
            max-width: 85%;
            line-height: 1.6;
            font-size: 0.92rem;
        }
        .chat-user {
            background: linear-gradient(135deg, #1e1b4b, #312e81);
            border: 1px solid rgba(99, 102, 241, 0.25);
            color: #e0e7ff;
            margin-left: auto;
            text-align: right;
        }
        .chat-assistant {
            background: linear-gradient(135deg, #111827, #1f2937);
            border: 1px solid rgba(75, 85, 99, 0.3);
            color: #d1d5db;
        }

        /* ── Cards ── */
        .info-card {
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(31, 41, 55, 0.6));
            border: 1px solid rgba(75, 85, 99, 0.3);
            border-radius: 12px;
            padding: 18px;
            margin: 8px 0;
        }

        .action-card {
            background: rgba(17, 24, 39, 0.6);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 10px;
            padding: 12px 16px;
            margin: 6px 0;
            transition: all 0.2s ease;
        }
        .action-card:hover {
            border-color: rgba(99, 102, 241, 0.5);
            background: rgba(30, 27, 75, 0.4);
        }

        /* ── Header ── */
        .vaxo-header {
            text-align: center;
            padding: 10px 0 20px;
        }
        .vaxo-header h1 {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #818cf8 0%, #a78bfa 50%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 4px;
        }
        .vaxo-header p {
            color: #6b7280;
            font-size: 0.88rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        /* ── Misc ── */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        div[data-testid="stChatMessage"] {
            background: transparent !important;
        }

        .stTextInput > div > div > input {
            background: rgba(17, 24, 39, 0.8) !important;
            border: 1px solid rgba(75, 85, 99, 0.4) !important;
            border-radius: 10px !important;
            color: #e5e7eb !important;
        }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#   Session State Initialization
# ─────────────────────────────────────────────
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "messages": [],
        "voice_state": "idle",  # idle, listening, processing, speaking
        "tts_enabled": True,
        "stt_enabled": True,
        "current_page": "assistant",
        "llm": None,
        "conversation_service": None,
        "tts_service": None,
        "action_registry": None,
        "repository": None,
        "initialized": False,
        "ollama_connected": False,
        "available_models": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def initialize_services():
    """Initialize all backend services."""
    if st.session_state.initialized:
        return

    settings = get_settings()

    # Initialize repository
    st.session_state.repository = HistoryRepository()

    # Initialize LLM service
    st.session_state.llm = VaxoLLM()
    st.session_state.ollama_connected = st.session_state.llm.check_connection()
    if st.session_state.ollama_connected:
        st.session_state.available_models = st.session_state.llm.get_available_models()
    else:
        # Auto-enable demo mode when Ollama is offline so user can chat immediately
        st.session_state.llm.demo_mode = True

    # Initialize conversation service
    st.session_state.conversation_service = ConversationService(
        st.session_state.repository
    )
    st.session_state.conversation_service.start_new_conversation("Vaxo Session")

    # Initialize TTS
    st.session_state.tts_service = TextToSpeechService()

    # Initialize action registry
    st.session_state.action_registry = create_default_registry()

    st.session_state.initialized = True


# ─────────────────────────────────────────────
#   Message Processing
# ─────────────────────────────────────────────
def process_user_input(user_input: str) -> str:
    """
    Process user input: detect intent, execute action or chat with LLM.

    Returns the assistant's response.
    """
    llm: VaxoLLM = st.session_state.llm
    registry = st.session_state.action_registry
    conversation: ConversationService = st.session_state.conversation_service

    # Check for direct action match in registry first (most accurate keyword matching)
    matched_action = registry.find_action(user_input)
    action_name = matched_action.name if matched_action else None
    action_args = {}

    # If registry didn't find direct match, fallback to LLM intent detection
    if not action_name:
        intent = llm.generate_intent(user_input)
        if intent.get("intent") != "chat":
            action_name = intent["intent"]
            action_args = intent.get("args", {})

    if action_name and registry.is_registered(action_name):
        result = registry.execute(action_name, action_args if action_args else None)

        # Log to database
        st.session_state.repository.log_action(
            action_name, action_args, result.message, result.success
        )

        # Handle special actions
        if result.data and result.data.get("action") == "stop_voice":
            st.session_state.tts_enabled = False
            st.session_state.voice_state = "idle"

        if result.data and result.data.get("action") == "show_history":
            st.session_state.current_page = "history"

        return result.message

    # No action match — chat with LLM
    context = conversation.get_context()
    response = llm.chat(user_input, context)
    return response


# ─────────────────────────────────────────────
#   Sidebar
# ─────────────────────────────────────────────
def render_sidebar():
    """Render the sidebar with navigation and status."""
    with st.sidebar:
        st.markdown("""
        <div class="vaxo-header">
            <h1>🔮 Vaxo</h1>
            <p>AI Desktop Assistant</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation
        st.markdown("### 🧭 Navigation")
        pages = {
            "assistant": "🏠 Assistant",
            "history": "📜 History",
            "actions": "⚡ Actions",
            "settings": "⚙️ Settings",
            "about": "ℹ️ About",
        }

        for key, label in pages.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.current_page = key
                st.rerun()

        st.markdown("---")

        # System Status
        st.markdown("### 📊 Status")

        # Ollama / AI status
        if st.session_state.ollama_connected:
            st.markdown(
                '<span class="status-badge status-online">● Ollama Connected</span>',
                unsafe_allow_html=True,
            )
            st.caption(f"Model: `{st.session_state.llm.model}`")
        elif st.session_state.llm and getattr(st.session_state.llm, "demo_mode", False):
            st.markdown(
                '<span class="status-badge status-idle">● Demo Mode Active</span>',
                unsafe_allow_html=True,
            )
            st.caption("Offline simulated responses")
        else:
            st.markdown(
                '<span class="status-badge status-offline">● Ollama Offline</span>',
                unsafe_allow_html=True,
            )
            st.caption("Install Ollama or enable Demo Mode")

        # TTS status
        tts: TextToSpeechService = st.session_state.tts_service
        if tts and tts.is_available():
            st.markdown(
                '<span class="status-badge status-online">● TTS Ready</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="status-badge status-offline">● TTS Unavailable</span>',
                unsafe_allow_html=True,
            )

        # Voice state
        voice_icons = {
            "idle": ("status-idle", "Idle"),
            "listening": ("status-online", "Listening"),
            "processing": ("status-online", "Processing"),
            "speaking": ("status-online", "Speaking"),
        }
        css, label = voice_icons.get(
            st.session_state.voice_state, ("status-idle", "Idle")
        )
        st.markdown(
            f'<span class="status-badge {css}">● Voice: {label}</span>',
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Quick stats
        if st.session_state.repository:
            stats = st.session_state.repository.get_conversation_stats()
            col1, col2 = st.columns(2)
            col1.metric("Conversations", stats["total_conversations"])
            col2.metric("Messages", stats["total_messages"])


# ─────────────────────────────────────────────
#   Page: Assistant (Main Chat)
# ─────────────────────────────────────────────
def render_assistant_page():
    """Render the main chat assistant page."""

    # Header with animated voice orb and equalizer
    orb_state = st.session_state.voice_state
    orb_emoji = {"idle": "🔮", "listening": "🔴", "processing": "⚡", "speaking": "🔊"}.get(orb_state, "🔮")
    state_labels = {
        "idle": "Vaxo is Ready — Tap to speak or type a command",
        "listening": "🎙️ Listening... Speak your command clearly",
        "processing": "⚡ Processing command...",
        "speaking": "🔊 Speaking response...",
    }

    wave_html = ""
    if orb_state in ("listening", "speaking", "processing"):
        wave_html = """
        <div class="sound-wave">
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
        </div>
        """

    st.markdown(f"""
    <div class="voice-orb-container">
        <div class="voice-orb {orb_state}" title="{state_labels.get(orb_state, 'Vaxo')}">
            {orb_emoji}
        </div>
        <div style="margin-top: 10px; font-weight: 500; font-size: 0.9rem; color: #c7d2fe; letter-spacing: 0.03em;">
            {state_labels.get(orb_state, 'Vaxo')}
        </div>
        {wave_html}
    </div>
    """, unsafe_allow_html=True)

    # Voice controls
    col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])

    with col1:
        voice_btn = st.button("🎙️ Push to Talk", use_container_width=True, key="ptt_btn", help="Click and speak into your microphone")

    with col2:
        tts_toggle = st.toggle(
            "🔊 Voice Output",
            value=st.session_state.tts_enabled,
            key="tts_toggle",
            help="Toggle spoken replies using offline Windows speech engine",
        )
        st.session_state.tts_enabled = tts_toggle

    with col3:
        if st.button("🗑️ Clear Chat", use_container_width=True, help="Clear conversation history"):
            st.session_state.messages = []
            st.session_state.conversation_service.clear()
            st.session_state.conversation_service.start_new_conversation("Vaxo Session")
            st.rerun()

    with col4:
        if st.button("🔄 Reconnect", use_container_width=True, help="Refresh connection to Ollama"):
            st.session_state.ollama_connected = st.session_state.llm.check_connection()
            if st.session_state.ollama_connected:
                st.session_state.available_models = st.session_state.llm.get_available_models()
            st.rerun()

    # Interactive One-Click Suggestion Pills
    st.markdown("###### ⚡ Instant Desktop Actions")
    p1, p2, p3, p4, p5, p6 = st.columns(6)
    with p1:
        if st.button("🧮 Calculator", key="pill_calc", use_container_width=True):
            handle_text_input("Open calculator")
    with p2:
        if st.button("📝 Notepad", key="pill_note", use_container_width=True):
            handle_text_input("Open notepad")
    with p3:
        if st.button("🌐 Browser", key="pill_web", use_container_width=True):
            handle_text_input("Open browser")
    with p4:
        if st.button("🕐 Date & Time", key="pill_time", use_container_width=True):
            handle_text_input("What time is it?")
    with p5:
        if st.button("📊 Diagnostics", key="pill_diag", use_container_width=True):
            handle_text_input("Show system info")
    with p6:
        if st.button("💡 Features", key="pill_help", use_container_width=True):
            handle_text_input("What can you do?")

    st.markdown("---")

    # Handle Push-to-Talk
    if voice_btn:
        handle_voice_input()

    # Chat messages display
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🔮"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and len(msg["content"]) > 0:
                # Small audio replay pill
                col_rep, _ = st.columns([1, 10])
                with col_rep:
                    if st.button("🔊", key=f"rep_{idx}", help="Replay this response aloud"):
                        tts: TextToSpeechService = st.session_state.tts_service
                        if tts and tts.is_available():
                            tts.speak(msg["content"])

    # Text input
    if prompt := st.chat_input("Type a message or command...", key="chat_input"):
        handle_text_input(prompt)


def handle_text_input(user_input: str):
    """Process typed user input."""
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    # Add to conversation service
    st.session_state.conversation_service.add_message("user", user_input)

    # Process and get response
    with st.chat_message("assistant", avatar="🔮"):
        st.session_state.voice_state = "processing"
        with st.spinner("Thinking..."):
            response = process_user_input(user_input)
        st.markdown(response)

    # Save response
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.conversation_service.add_message("assistant", response)

    # Speak response if enabled
    if st.session_state.tts_enabled and st.session_state.tts_service:
        tts: TextToSpeechService = st.session_state.tts_service
        if tts.is_available():
            st.session_state.voice_state = "speaking"
            tts.speak(response)

    st.session_state.voice_state = "idle"
    st.rerun()


def handle_voice_input():
    """Handle push-to-talk voice input."""
    try:
        from services.speech_to_text import SpeechToTextService, VoiceInputError

        stt = SpeechToTextService()
        if not stt.is_available():
            st.warning(
                "🎙️ Voice input is not available. "
                "Install SpeechRecognition and PyAudio: `pip install SpeechRecognition PyAudio`"
            )
            return

        st.session_state.voice_state = "listening"
        st.toast("🔴 Microphone active — Speak your command now!")
        with st.spinner("🔴 Listening for your voice... Speak now!"):
            text = stt.listen(timeout=8, phrase_time_limit=15)

        if text:
            st.toast(f"🎙️ Transcribed: \"{text}\"")
            st.success(f"🎙️ Heard: *\"{text}\"*")
            handle_text_input(text)
        else:
            st.info("Didn't catch that. Please speak clearly into your microphone.")

    except Exception as e:
        st.error(f"Voice input error: {e}")
        st.info("💡 Tip: You can also click any Quick Action pill or type in the chat box below.")

    st.session_state.voice_state = "idle"


# ─────────────────────────────────────────────
#   Page: Conversation History
# ─────────────────────────────────────────────
def render_history_page():
    """Render the conversation history page."""
    st.markdown("## 📜 Conversation History")

    conversation_service: ConversationService = st.session_state.conversation_service

    # Current session history
    st.markdown("### Current Session")
    current_messages = conversation_service.get_history()
    if current_messages:
        for msg in current_messages:
            role_icon = "🧑" if msg["role"] == "user" else "🔮"
            st.markdown(f"{role_icon} **{msg['role'].capitalize()}:** {msg['content']}")
    else:
        st.info("No messages in the current session yet.")

    st.markdown("---")

    # Past conversations
    st.markdown("### Past Conversations")
    past = conversation_service.get_past_conversations(limit=20)
    if past:
        for conv in past:
            with st.expander(f"💬 {conv['title']} — {conv.get('started_at', 'Unknown')[:16]}"):
                messages = st.session_state.repository.get_messages(conv["id"])
                if messages:
                    for msg in messages:
                        role_icon = "🧑" if msg["role"] == "user" else "🔮"
                        st.markdown(f"{role_icon} **{msg['role'].capitalize()}:** {msg['content']}")
                else:
                    st.caption("No messages.")

                if st.button(f"🗑️ Delete", key=f"del_{conv['id']}"):
                    conversation_service.delete_conversation(conv["id"])
                    st.rerun()
    else:
        st.info("No past conversations found.")

    st.markdown("---")

    # Action log
    st.markdown("### ⚡ Action Log")
    action_log = st.session_state.repository.get_action_log(limit=20)
    if action_log:
        for entry in action_log:
            icon = "✅" if entry["success"] else "❌"
            st.markdown(
                f"{icon} **{entry['action_name']}** — {entry['timestamp'][:16]}"
            )
            st.caption(entry.get("result", ""))
    else:
        st.info("No actions recorded yet.")


# ─────────────────────────────────────────────
#   Page: Approved Actions
# ─────────────────────────────────────────────
def render_actions_page():
    """Render the approved actions page."""
    st.markdown("## ⚡ Approved Actions")
    st.markdown(
        "These are the **only** desktop actions Vaxo can execute. "
        "All commands are validated against this allowlist."
    )

    registry = st.session_state.action_registry
    categories = registry.get_categories()

    for category, actions in categories.items():
        st.markdown(f"### {category.capitalize()}")
        for action in actions:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                <div class="action-card">
                    <strong>{action.description}</strong><br>
                    <small style="color: #9ca3af;">
                        Command: <code>{action.name}</code> &nbsp;|&nbsp;
                        Keywords: {', '.join(f'<code>{k}</code>' for k in action.keywords[:4])}
                    </small>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button(f"▶ Run", key=f"run_{action.name}", use_container_width=True):
                    result = registry.execute(action.name)
                    if result.success:
                        st.success(result.message)
                        st.toast(f"✅ Executed: {action.description}")

                        # If system info, show interactive progress gauges
                        if result.data and "cpu_num" in result.data:
                            g1, g2, g3 = st.columns(3)
                            g1.metric("CPU Usage", f"{result.data['cpu_num']:.1f}%")
                            g1.progress(min(1.0, max(0.0, result.data['cpu_num'] / 100.0)))
                            g2.metric("RAM Usage", f"{result.data['ram_num']:.1f}%")
                            g2.progress(min(1.0, max(0.0, result.data['ram_num'] / 100.0)))
                            g3.metric("Disk Usage", f"{result.data['disk_num']:.1f}%")
                            g3.progress(min(1.0, max(0.0, result.data['disk_num'] / 100.0)))

                        # Speak result if voice output is enabled
                        if st.session_state.tts_enabled and st.session_state.tts_service:
                            tts: TextToSpeechService = st.session_state.tts_service
                            if tts and tts.is_available():
                                tts.speak(result.message)
                    else:
                        st.error(result.message)

                    # Log the action
                    st.session_state.repository.log_action(
                        action.name, {}, result.message, result.success
                    )


# ─────────────────────────────────────────────
#   Page: Settings
# ─────────────────────────────────────────────
def render_settings_page():
    """Render the settings page."""
    st.markdown("## ⚙️ Settings")

    settings = get_settings()

    # Model Settings
    st.markdown("### 🤖 AI Model")
    col1, col2 = st.columns(2)

    with col1:
        new_url = st.text_input(
            "Ollama URL",
            value=st.session_state.llm.base_url,
            key="settings_url",
        )

    with col2:
        available = st.session_state.available_models
        if available:
            selected_model = st.selectbox(
                "Model",
                options=available,
                index=available.index(st.session_state.llm.model) if st.session_state.llm.model in available else 0,
                key="settings_model",
            )
        else:
            selected_model = st.text_input(
                "Model name",
                value=st.session_state.llm.model,
                key="settings_model_text",
            )

    if st.button("💾 Apply Model Settings"):
        demo_mode_current = getattr(st.session_state.llm, "demo_mode", False)
        st.session_state.llm = VaxoLLM(base_url=new_url, model=selected_model, demo_mode=demo_mode_current)
        st.session_state.ollama_connected = st.session_state.llm.check_connection()
        if st.session_state.ollama_connected:
            st.session_state.available_models = st.session_state.llm.get_available_models()
            st.success(f"✅ Connected to Ollama with model: {selected_model}")
        else:
            st.warning("⚠️ Cannot connect to Ollama at the specified URL.")
        st.rerun()

    st.markdown("---")

    # Demo Mode Settings
    st.markdown("### 🧪 Portfolio Demonstration Mode")
    demo_active = getattr(st.session_state.llm, "demo_mode", False)
    new_demo_mode = st.toggle(
        "Enable Demo Mode (Offline simulated responses without Ollama)",
        value=demo_active,
        key="demo_mode_toggle",
        help="Allows recruiters and testers to test conversational flow and UI features without installing Ollama locally.",
    )
    if new_demo_mode != demo_active:
        st.session_state.llm.demo_mode = new_demo_mode
        st.success(f"Demo Mode {'enabled' if new_demo_mode else 'disabled'}.")
        st.rerun()

    st.markdown("---")

    # Voice Settings
    st.markdown("### 🎙️ Voice")
    col1, col2 = st.columns(2)

    with col1:
        tts_rate = st.slider("Speech Rate (WPM)", 50, 400, settings.TTS_RATE, key="tts_rate")
    with col2:
        tts_vol = st.slider("Volume", 0.0, 1.0, settings.TTS_VOLUME, 0.1, key="tts_vol")

    if st.button("💾 Apply Voice Settings"):
        tts: TextToSpeechService = st.session_state.tts_service
        if tts and tts.is_available():
            tts.set_rate(tts_rate)
            tts.set_volume(tts_vol)
            st.success("✅ Voice settings updated.")
        else:
            st.warning("TTS service is not available.")

    st.markdown("---")

    # Ollama Setup Instructions
    if not st.session_state.ollama_connected:
        st.markdown("### 📦 Ollama Setup Guide")
        st.markdown("""
        **Ollama is not currently running.** Follow these steps to set up local AI:

        1. **Download Ollama** from [ollama.ai](https://ollama.ai)
        2. **Install** and run the installer
        3. **Start Ollama** — it should run automatically after install
        4. **Pull a model** (open a terminal):
           ```
           ollama pull tinyllama
           ```
           For better quality (needs more RAM):
           ```
           ollama pull phi3:mini
           ```
        5. **Click "Reconnect"** on the Assistant page

        > **Note:** Your system has ~8 GB RAM. Recommended models:
        > - `tinyllama` (1.1B params, ~1 GB) — Fast, basic
        > - `qwen2:0.5b` (0.5B params, ~0.4 GB) — Very light
        > - `phi3:mini` (3.8B params, ~2.3 GB) — Better quality
        """)


# ─────────────────────────────────────────────
#   Page: About / System Status
# ─────────────────────────────────────────────
def render_about_page():
    """Render the about and system status page."""
    st.markdown("## ℹ️ About Vaxo")

    settings = get_settings()

    st.markdown(f"""
    <div class="info-card">
        <h3 style="color: #a5b4fc; margin-top: 0;">🔮 {settings.APP_NAME} v{settings.APP_VERSION}</h3>
        <p style="color: #9ca3af;">{settings.APP_DESCRIPTION}</p>
        <p style="color: #6b7280; font-size: 0.85rem;">
            A local-first AI desktop assistant that runs on your machine.
            No cloud APIs required for core functionality.
            Built with Python, Streamlit, and Ollama.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💻 System Status")

    # Collect status info
    import platform
    import psutil

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**System**")
        st.markdown(f"- **OS:** {platform.system()} {platform.version()}")
        st.markdown(f"- **Python:** {platform.python_version()}")
        st.markdown(f"- **CPU:** {psutil.cpu_percent()}% usage")

        mem = psutil.virtual_memory()
        st.markdown(f"- **RAM:** {mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB ({mem.percent}%)")

    with col2:
        st.markdown("**Services**")

        llm_info = st.session_state.llm.get_model_info()
        st.markdown(f"- **Ollama:** {'🟢 Connected' if llm_info['connected'] == 'True' else '🔴 Offline'}")
        st.markdown(f"- **Model:** {llm_info['model']}")
        st.markdown(f"- **Available models:** {llm_info['available_models']}")

        tts_status = st.session_state.tts_service.get_status() if st.session_state.tts_service else {}
        st.markdown(f"- **TTS:** {'🟢 Ready' if tts_status.get('available') == 'True' else '🔴 Unavailable'}")

    st.markdown("---")

    # Statistics
    st.markdown("### 📊 Usage Statistics")
    stats = st.session_state.repository.get_conversation_stats()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Conversations", stats["total_conversations"])
    col2.metric("Total Messages", stats["total_messages"])
    col3.metric("Actions Executed", stats["total_actions"])
    col4.metric("Successful Actions", stats["successful_actions"])

    st.markdown("---")

    st.markdown("### 🛡️ Security & Privacy")
    st.markdown("""
    - All AI processing happens **locally** via Ollama — no data sent to external APIs.
    - Voice recognition uses Google Web Speech API (requires internet) — audio is processed by Google.
    - Text-to-speech is **fully offline** using system voices.
    - Only **allowlisted** desktop actions can be executed — no arbitrary command execution.
    - Conversation history is stored in a **local SQLite database**.
    - No API keys, passwords, or personal data are collected or transmitted.
    """)

    st.markdown("---")

    st.markdown("### 🚀 Tech Stack")
    st.markdown("""
    | Component | Technology |
    |-----------|-----------|
    | Language | Python 3.12 |
    | UI Framework | Streamlit |
    | LLM Runtime | Ollama (local) |
    | Speech-to-Text | SpeechRecognition + Google Web Speech |
    | Text-to-Speech | pyttsx3 (SAPI5, offline) |
    | Database | SQLite |
    | System Info | psutil |
    | Testing | pytest |
    """)


# ─────────────────────────────────────────────
#   Main Application
# ─────────────────────────────────────────────
def main():
    """Main application entry point."""
    inject_custom_css()
    init_session_state()
    initialize_services()
    render_sidebar()

    # Route to active page
    page = st.session_state.current_page
    if page == "assistant":
        render_assistant_page()
    elif page == "history":
        render_history_page()
    elif page == "actions":
        render_actions_page()
    elif page == "settings":
        render_settings_page()
    elif page == "about":
        render_about_page()
    else:
        render_assistant_page()


if __name__ == "__main__":
    main()
