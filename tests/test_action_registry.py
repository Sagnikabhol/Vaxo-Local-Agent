"""
Tests for the Action Registry and Windows Actions.

All tests mock subprocess and OS-level calls to prevent
actual application launches or system modifications.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from automation.action_registry import ActionRegistry, Action, ActionResult
from automation.windows_actions import (
    create_default_registry,
    open_calculator,
    open_notepad,
    open_browser,
    get_current_time,
    get_system_info,
    stop_voice,
    show_history,
)


# ─────────────────────────────────────────────
#   ActionRegistry Tests
# ─────────────────────────────────────────────

class TestActionRegistry:
    """Tests for the ActionRegistry class."""

    def test_register_action(self):
        """Test registering an action."""
        registry = ActionRegistry()
        action = Action(
            name="test_action",
            description="A test action",
            keywords=["test", "testing"],
            handler=lambda: ActionResult(success=True, message="OK"),
        )
        registry.register(action)
        assert registry.is_registered("test_action")

    def test_unregistered_action_rejected(self):
        """Test that unregistered actions cannot be executed."""
        registry = ActionRegistry()
        result = registry.execute("not_registered")
        assert not result.success
        assert "not registered" in result.message.lower()

    def test_execute_registered_action(self):
        """Test executing a registered action."""
        registry = ActionRegistry()
        action = Action(
            name="greet",
            description="Say hello",
            keywords=["hello"],
            handler=lambda: ActionResult(success=True, message="Hello!"),
        )
        registry.register(action)
        result = registry.execute("greet")
        assert result.success
        assert result.message == "Hello!"

    def test_execute_action_with_args(self):
        """Test executing an action with arguments."""
        registry = ActionRegistry()
        action = Action(
            name="echo",
            description="Echo text",
            keywords=["echo"],
            handler=lambda text="": ActionResult(success=True, message=f"Echo: {text}"),
        )
        registry.register(action)
        result = registry.execute("echo", {"text": "hello world"})
        assert result.success
        assert "hello world" in result.message

    def test_execute_action_with_invalid_args(self):
        """Test executing an action with invalid arguments."""
        registry = ActionRegistry()
        action = Action(
            name="strict",
            description="Strict action",
            keywords=["strict"],
            handler=lambda: ActionResult(success=True, message="OK"),
        )
        registry.register(action)
        # Passing args to a handler that doesn't accept them
        result = registry.execute("strict", {"unexpected": "value"})
        assert not result.success
        assert "invalid arguments" in result.message.lower() or "error" in result.message.lower()

    def test_find_action_by_keyword(self):
        """Test finding an action by keyword matching."""
        registry = ActionRegistry()
        action = Action(
            name="calculator",
            description="Open calculator",
            keywords=["calculator", "calc", "math"],
            handler=lambda: ActionResult(success=True, message="Opened"),
        )
        registry.register(action)

        found = registry.find_action("open the calculator please")
        assert found is not None
        assert found.name == "calculator"

    def test_find_action_no_match(self):
        """Test that unmatched input returns None."""
        registry = ActionRegistry()
        action = Action(
            name="calculator",
            description="Open calculator",
            keywords=["calculator"],
            handler=lambda: ActionResult(success=True, message="Opened"),
        )
        registry.register(action)

        found = registry.find_action("play some music")
        assert found is None

    def test_get_all_actions(self):
        """Test getting all registered actions."""
        registry = ActionRegistry()
        for i in range(3):
            registry.register(Action(
                name=f"action_{i}",
                description=f"Action {i}",
                keywords=[f"key{i}"],
                handler=lambda: ActionResult(success=True, message="OK"),
            ))
        actions = registry.get_all_actions()
        assert len(actions) == 3

    def test_get_categories(self):
        """Test getting actions grouped by category."""
        registry = ActionRegistry()
        registry.register(Action(
            name="a", description="A", keywords=["a"],
            handler=lambda: ActionResult(success=True, message="OK"),
            category="apps"
        ))
        registry.register(Action(
            name="b", description="B", keywords=["b"],
            handler=lambda: ActionResult(success=True, message="OK"),
            category="info"
        ))
        categories = registry.get_categories()
        assert "apps" in categories
        assert "info" in categories

    def test_execution_log(self):
        """Test that action executions are logged."""
        registry = ActionRegistry()
        registry.register(Action(
            name="logged",
            description="Logged action",
            keywords=["logged"],
            handler=lambda: ActionResult(success=True, message="Done"),
        ))
        registry.execute("logged")
        registry.execute("unregistered")

        log = registry.get_execution_log()
        assert len(log) == 2
        assert log[0]["success"] is True
        assert log[1]["success"] is False

    def test_handler_exception_caught(self):
        """Test that handler exceptions are caught gracefully."""
        registry = ActionRegistry()
        registry.register(Action(
            name="broken",
            description="Broken action",
            keywords=["broken"],
            handler=lambda: (_ for _ in ()).throw(RuntimeError("Test error")),
        ))
        # Use a handler that actually raises
        def bad_handler():
            raise RuntimeError("boom")
        
        registry._actions["broken"].handler = bad_handler
        result = registry.execute("broken")
        assert not result.success
        assert "error" in result.message.lower()


# ─────────────────────────────────────────────
#   Default Registry Tests
# ─────────────────────────────────────────────

class TestDefaultRegistry:
    """Test the pre-loaded default registry."""

    def test_default_registry_created(self):
        """Test that the default registry has all expected actions."""
        registry = create_default_registry()
        expected = [
            "open_calculator", "open_notepad", "open_browser",
            "get_time", "get_system_info", "stop_voice", "show_history"
        ]
        for action_name in expected:
            assert registry.is_registered(action_name), f"{action_name} not registered"

    def test_default_registry_action_count(self):
        """Test the default registry has the expected number of actions."""
        registry = create_default_registry()
        actions = registry.get_all_actions()
        assert len(actions) >= 7


# ─────────────────────────────────────────────
#   Windows Action Tests (Mocked)
# ─────────────────────────────────────────────

class TestWindowsActions:
    """Tests for individual Windows actions. All subprocess calls are mocked."""

    @patch("automation.windows_actions.subprocess.Popen")
    def test_open_calculator(self, mock_popen):
        """Test opening calculator (mocked)."""
        result = open_calculator()
        assert result.success
        mock_popen.assert_called_once()
        assert "calc" in str(mock_popen.call_args).lower()

    @patch("automation.windows_actions.subprocess.Popen")
    def test_open_notepad(self, mock_popen):
        """Test opening notepad (mocked)."""
        result = open_notepad()
        assert result.success
        mock_popen.assert_called_once()

    @patch("automation.windows_actions.subprocess.Popen", side_effect=FileNotFoundError)
    def test_open_calculator_not_found(self, mock_popen):
        """Test handling of missing calculator."""
        result = open_calculator()
        assert not result.success

    @patch("automation.windows_actions.webbrowser.open")
    def test_open_browser_no_url(self, mock_open):
        """Test opening browser without URL."""
        result = open_browser()
        assert result.success
        mock_open.assert_called_once()

    @patch("automation.windows_actions.webbrowser.open")
    def test_open_browser_with_valid_url(self, mock_open):
        """Test opening browser with a valid https URL."""
        result = open_browser("https://www.google.com")
        assert result.success
        mock_open.assert_called_once_with("https://www.google.com")

    def test_open_browser_invalid_url_scheme(self):
        """Test that non-http/https URLs are rejected."""
        result = open_browser("file:///etc/passwd")
        assert not result.success
        assert "only http" in result.message.lower()

    def test_open_browser_javascript_url_rejected(self):
        """Test that javascript: URLs are rejected."""
        result = open_browser("javascript:alert(1)")
        assert not result.success

    def test_get_current_time(self):
        """Test getting current time."""
        result = get_current_time()
        assert result.success
        assert result.data is not None
        assert "datetime" in result.data

    @patch("automation.windows_actions.psutil")
    def test_get_system_info(self, mock_psutil):
        """Test getting system info (mocked)."""
        # Setup mocks
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.cpu_count.side_effect = [4, 8]

        mock_mem = MagicMock()
        mock_mem.total = 8 * 1024**3
        mock_mem.used = 4 * 1024**3
        mock_mem.available = 4 * 1024**3
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        mock_disk = MagicMock()
        mock_disk.total = 500 * 1024**3
        mock_disk.used = 250 * 1024**3
        mock_disk.free = 250 * 1024**3
        mock_disk.percent = 50.0
        mock_psutil.disk_usage.return_value = mock_disk

        mock_psutil.boot_time.return_value = 1000000.0

        result = get_system_info()
        assert result.success
        assert result.data is not None

    def test_stop_voice(self):
        """Test the stop voice action."""
        result = stop_voice()
        assert result.success
        assert result.data["action"] == "stop_voice"

    def test_show_history(self):
        """Test the show history action."""
        result = show_history()
        assert result.success
        assert result.data["action"] == "show_history"
