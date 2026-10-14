"""
Tests for input validation and security measures.

Verifies that:
- Only allowlisted actions can be executed.
- Invalid/malicious inputs are rejected.
- URL validation works correctly.
- No arbitrary command execution is possible.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from automation.action_registry import ActionRegistry, Action, ActionResult
from automation.windows_actions import open_browser, create_default_registry


class TestInputValidation:
    """Test input validation and security."""

    def test_arbitrary_command_rejected(self):
        """Test that arbitrary commands cannot be executed."""
        registry = create_default_registry()

        # Try to execute non-existent actions
        dangerous_commands = [
            "rm -rf /",
            "del /f /q C:\\",
            "format C:",
            "shutdown /s",
            "net user",
            "powershell",
            "cmd.exe",
            "eval",
            "exec",
        ]

        for cmd in dangerous_commands:
            result = registry.execute(cmd)
            assert not result.success, f"Dangerous command '{cmd}' should not execute"

    def test_url_validation(self):
        """Test URL scheme validation for browser opening."""
        invalid_urls = [
            "file:///etc/passwd",
            "ftp://evil.com",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "//evil.com",
            "",
        ]

        for url in invalid_urls:
            if url:  # skip empty, tested separately
                result = open_browser(url)
                assert not result.success, f"URL '{url}' should be rejected"

    def test_valid_urls_accepted(self):
        """Test that valid http/https URLs are accepted."""
        from unittest.mock import patch

        valid_urls = [
            "https://www.google.com",
            "http://localhost:8080",
            "https://example.org/path?q=test",
        ]

        with patch("automation.windows_actions.webbrowser.open"):
            for url in valid_urls:
                result = open_browser(url)
                assert result.success, f"URL '{url}' should be accepted"

    def test_empty_action_name_rejected(self):
        """Test that empty action names are rejected."""
        registry = ActionRegistry()
        result = registry.execute("")
        assert not result.success

    def test_none_args_handled(self):
        """Test that None args don't crash execution."""
        registry = ActionRegistry()
        registry.register(Action(
            name="test",
            description="Test",
            keywords=["test"],
            handler=lambda: ActionResult(success=True, message="OK"),
        ))
        result = registry.execute("test", None)
        assert result.success

    def test_action_names_are_explicit(self):
        """Verify all default actions use explicit, descriptive names."""
        registry = create_default_registry()
        for action in registry.get_all_actions():
            assert "_" in action.name or action.name.isalpha(), \
                f"Action name '{action.name}' should be descriptive"
            assert len(action.name) > 3, \
                f"Action name '{action.name}' too short"
            assert len(action.description) > 5, \
                f"Action '{action.name}' needs a proper description"

    def test_no_shell_execution_in_actions(self):
        """Verify actions don't use shell=True using AST analysis."""
        import ast
        import inspect
        from automation import windows_actions

        source = inspect.getsource(windows_actions)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "shell":
                        assert not (isinstance(keyword.value, ast.Constant) and keyword.value.value is True), \
                            "Subprocess or function call must never specify shell=True"

    def test_confirmation_flag_respected(self):
        """Test that actions can require confirmation."""
        registry = ActionRegistry()
        action = Action(
            name="delete_stuff",
            description="Delete things",
            keywords=["delete"],
            handler=lambda: ActionResult(success=True, message="Deleted"),
            requires_confirmation=True,
        )
        registry.register(action)

        # The registry doesn't enforce confirmation itself (UI handles it),
        # but the flag should be accessible
        assert registry._actions["delete_stuff"].requires_confirmation


class TestKeywordMatching:
    """Test intent/keyword matching."""

    def test_keyword_case_insensitive(self):
        """Test that keyword matching is case-insensitive."""
        registry = create_default_registry()
        action = registry.find_action("OPEN CALCULATOR")
        assert action is not None
        assert action.name == "open_calculator"

    def test_partial_match(self):
        """Test partial keyword matching."""
        registry = create_default_registry()
        action = registry.find_action("can you open the calculator for me?")
        assert action is not None
        assert action.name == "open_calculator"

    def test_no_match_returns_none(self):
        """Test that unmatched input returns None."""
        registry = create_default_registry()
        action = registry.find_action("what is the meaning of life?")
        assert action is None

    def test_specific_match_wins(self):
        """Test that the most specific (longest) keyword wins."""
        registry = create_default_registry()
        action = registry.find_action("open calculator")
        assert action is not None
        assert action.name == "open_calculator"
