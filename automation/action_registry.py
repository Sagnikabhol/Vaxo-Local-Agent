"""
Vaxo Action Registry

A strict allowlist-based action registry that maps recognized intents
to predefined, validated actions. Never executes arbitrary commands.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Result of an executed action."""
    success: bool
    message: str
    data: dict | None = None


@dataclass
class Action:
    """Definition of a registered action."""
    name: str
    description: str
    keywords: list[str]
    handler: Callable[..., ActionResult]
    requires_confirmation: bool = False
    category: str = "general"


class ActionRegistry:
    """
    Registry of approved desktop actions.

    Only actions explicitly registered in the allowlist can be executed.
    This prevents the LLM from running arbitrary commands.
    """

    def __init__(self):
        self._actions: dict[str, Action] = {}
        self._execution_log: list[dict] = []

    def register(self, action: Action) -> None:
        """Register an action in the allowlist."""
        self._actions[action.name] = action
        logger.info("Registered action: %s", action.name)

    def is_registered(self, action_name: str) -> bool:
        """Check if an action is in the allowlist."""
        return action_name in self._actions

    def execute(self, action_name: str, args: dict | None = None) -> ActionResult:
        """
        Execute a registered action by name.

        Only executes actions that are explicitly registered.
        Never runs arbitrary or unregistered commands.

        Args:
            action_name: Name of the action to execute.
            args: Optional arguments to pass to the action handler.

        Returns:
            ActionResult with success status and message.
        """
        if not self.is_registered(action_name):
            msg = f"Action '{action_name}' is not registered. Only approved actions can be executed."
            logger.warning("Attempted to execute unregistered action: %s", action_name)
            self._log_execution(action_name, args or {}, msg, False)
            return ActionResult(success=False, message=msg)

        action = self._actions[action_name]

        try:
            if args:
                result = action.handler(**args)
            else:
                result = action.handler()

            self._log_execution(action_name, args or {}, result.message, result.success)
            return result

        except TypeError as e:
            msg = f"Invalid arguments for action '{action_name}': {e}"
            logger.error(msg)
            self._log_execution(action_name, args or {}, msg, False)
            return ActionResult(success=False, message=msg)
        except Exception as e:
            msg = f"Error executing action '{action_name}': {e}"
            logger.error(msg)
            self._log_execution(action_name, args or {}, msg, False)
            return ActionResult(success=False, message=msg)

    def find_action(self, user_input: str) -> Optional[Action]:
        """
        Find a matching action based on keyword matching.

        Args:
            user_input: The user's text input to match against.

        Returns:
            The matching Action or None if no match found.
        """
        input_lower = user_input.lower().strip()

        # Try exact keyword matches first (longer keywords first for specificity)
        all_matches: list[tuple[int, Action]] = []

        for action in self._actions.values():
            for keyword in action.keywords:
                if keyword.lower() in input_lower:
                    all_matches.append((len(keyword), action))

        if all_matches:
            # Return the action with the longest matching keyword (most specific)
            all_matches.sort(key=lambda x: x[0], reverse=True)
            return all_matches[0][1]

        return None

    def get_all_actions(self) -> list[Action]:
        """Get all registered actions."""
        return list(self._actions.values())

    def get_categories(self) -> dict[str, list[Action]]:
        """Get actions grouped by category."""
        categories: dict[str, list[Action]] = {}
        for action in self._actions.values():
            if action.category not in categories:
                categories[action.category] = []
            categories[action.category].append(action)
        return categories

    def get_execution_log(self) -> list[dict]:
        """Get the in-memory execution log."""
        return list(self._execution_log)

    def _log_execution(
        self,
        action_name: str,
        args: dict,
        result_message: str,
        success: bool,
    ) -> None:
        """Log an action execution attempt."""
        from datetime import datetime

        self._execution_log.append({
            "action": action_name,
            "args": args,
            "result": result_message,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        })
