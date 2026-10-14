"""
Vaxo Windows Desktop Actions

Predefined, safe desktop automation actions for Windows.
Each action uses subprocess with shell=False and an explicit allowlist.
Never enables shell mode or executes arbitrary commands.
"""

import logging
import platform
import subprocess
import webbrowser
from datetime import datetime

import psutil

from automation.action_registry import Action, ActionRegistry, ActionResult

logger = logging.getLogger(__name__)

# Allowlist of executable paths
ALLOWED_EXECUTABLES = {
    "calc": "calc.exe",
    "notepad": "notepad.exe",
}


def open_calculator() -> ActionResult:
    """Open the Windows Calculator application."""
    try:
        subprocess.Popen(
            ["calc.exe"],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return ActionResult(
            success=True,
            message="✅ Windows Calculator has been opened.",
        )
    except FileNotFoundError:
        return ActionResult(
            success=False,
            message="❌ Calculator application not found on this system.",
        )
    except OSError as e:
        return ActionResult(success=False, message=f"❌ Failed to open Calculator: {e}")


def open_notepad() -> ActionResult:
    """Open the Windows Notepad application."""
    try:
        subprocess.Popen(
            ["notepad.exe"],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return ActionResult(
            success=True,
            message="✅ Notepad has been opened.",
        )
    except FileNotFoundError:
        return ActionResult(
            success=False,
            message="❌ Notepad application not found on this system.",
        )
    except OSError as e:
        return ActionResult(success=False, message=f"❌ Failed to open Notepad: {e}")


def open_browser(url: str = "") -> ActionResult:
    """
    Open the default web browser, optionally navigating to a URL.

    Only http:// and https:// URLs are allowed for safety.
    """
    try:
        if url:
            # Validate URL scheme for safety
            url = url.strip()
            if not url.startswith(("http://", "https://")):
                return ActionResult(
                    success=False,
                    message="⚠️ Only http:// and https:// URLs are allowed for security.",
                )
            webbrowser.open(url)
            return ActionResult(
                success=True,
                message=f"✅ Browser opened with URL: {url}",
            )
        else:
            webbrowser.open("https://www.google.com")
            return ActionResult(
                success=True,
                message="✅ Default browser has been opened.",
            )
    except Exception as e:
        return ActionResult(success=False, message=f"❌ Failed to open browser: {e}")


def get_current_time() -> ActionResult:
    """Get the current date and time."""
    now = datetime.now()
    formatted = now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
    return ActionResult(
        success=True,
        message=f"🕐 Current date and time: **{formatted}**",
        data={"datetime": now.isoformat(), "formatted": formatted},
    )


def get_system_info() -> ActionResult:
    """Get basic system information using psutil."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "processor": platform.processor(),
            "architecture": platform.machine(),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "cpu_usage": f"{cpu_percent}%",
            "ram_total": f"{memory.total / (1024**3):.1f} GB",
            "ram_used": f"{memory.used / (1024**3):.1f} GB",
            "ram_available": f"{memory.available / (1024**3):.1f} GB",
            "ram_usage": f"{memory.percent}%",
            "disk_total": f"{disk.total / (1024**3):.1f} GB",
            "disk_used": f"{disk.used / (1024**3):.1f} GB",
            "disk_free": f"{disk.free / (1024**3):.1f} GB",
            "disk_usage": f"{disk.percent}%",
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        message = (
            f"💻 **System Information**\n\n"
            f"**Platform:** {info['platform']} {info['platform_version']}\n"
            f"**Processor:** {info['processor']}\n"
            f"**Architecture:** {info['architecture']}\n"
            f"**CPU:** {info['cpu_cores']} cores / {info['cpu_threads']} threads — {info['cpu_usage']} usage\n"
            f"**RAM:** {info['ram_used']} / {info['ram_total']} ({info['ram_usage']} used)\n"
            f"**Disk:** {info['disk_used']} / {info['disk_total']} ({info['disk_usage']} used)\n"
            f"**Uptime since:** {info['boot_time']}"
        )

        return ActionResult(success=True, message=message, data=info)

    except Exception as e:
        return ActionResult(success=False, message=f"❌ Error getting system info: {e}")


def stop_voice() -> ActionResult:
    """Signal to stop voice interaction."""
    return ActionResult(
        success=True,
        message="🔇 Voice interaction stopped.",
        data={"action": "stop_voice"},
    )


def show_history() -> ActionResult:
    """Signal to show conversation history."""
    return ActionResult(
        success=True,
        message="📋 Showing conversation history.",
        data={"action": "show_history"},
    )


def create_default_registry() -> ActionRegistry:
    """
    Create an ActionRegistry pre-loaded with all approved Windows actions.

    Returns:
        ActionRegistry with all default actions registered.
    """
    registry = ActionRegistry()

    registry.register(Action(
        name="open_calculator",
        description="Open Windows Calculator",
        keywords=["calculator", "calc", "open calculator", "open calc", "math"],
        handler=open_calculator,
        category="applications",
    ))

    registry.register(Action(
        name="open_notepad",
        description="Open Windows Notepad",
        keywords=["notepad", "open notepad", "text editor", "editor", "open editor"],
        handler=open_notepad,
        category="applications",
    ))

    registry.register(Action(
        name="open_browser",
        description="Open default web browser",
        keywords=["browser", "open browser", "web", "internet", "chrome", "edge", "open chrome", "open edge"],
        handler=open_browser,
        category="applications",
    ))

    registry.register(Action(
        name="get_time",
        description="Show current date and time",
        keywords=["time", "date", "current time", "what time", "clock",
                   "what's the time", "tell me the time", "today's date", "what date"],
        handler=get_current_time,
        category="information",
    ))

    registry.register(Action(
        name="get_system_info",
        description="Display system information (CPU, RAM, disk usage)",
        keywords=["system info", "system status", "cpu", "ram", "memory",
                   "disk", "hardware", "system report", "computer info"],
        handler=get_system_info,
        category="information",
    ))

    registry.register(Action(
        name="stop_voice",
        description="Stop voice interaction",
        keywords=["stop listening", "stop voice", "mute", "be quiet",
                   "silence", "stop speaking", "shut up"],
        handler=stop_voice,
        category="voice",
    ))

    registry.register(Action(
        name="show_history",
        description="Show conversation and task history",
        keywords=["show history", "task history", "conversation history",
                   "what did we talk about", "previous conversations"],
        handler=show_history,
        category="information",
    ))

    return registry
