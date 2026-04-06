"""
Jack The Shadow — Global Application State

Manages the conversation context window, YOLO mode flag, language,
and session metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jack_the_shadow.config import MAX_CONTEXT_MESSAGES
from jack_the_shadow.config.prompts import get_system_prompt
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.state")


@dataclass
class AppState:
    """Encapsulates all mutable session state."""

    target: str
    model: str
    language: str = "en"
    yolo_mode: bool = False
    context_messages: list[dict[str, Any]] = field(default_factory=list)

    # ── Message helpers

    def add_message(self, role: str, content: str) -> None:
        self.context_messages.append({"role": role, "content": content})
        logger.debug("Added %s message (%d chars)", role, len(content))

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.context_messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
        logger.debug("Added tool result for call %s", tool_call_id)

    def add_assistant_message(self, message: dict[str, Any]) -> None:
        self.context_messages.append(message)
        logger.debug("Added assistant message (raw)")

    def get_messages_for_api(self) -> list[dict[str, Any]]:
        system = {"role": "system", "content": get_system_prompt(self.language)}
        return [system] + list(self.context_messages)

    # ── Context management

    def truncate_context(self) -> None:
        if len(self.context_messages) > MAX_CONTEXT_MESSAGES:
            excess = len(self.context_messages) - MAX_CONTEXT_MESSAGES
            self.context_messages = self.context_messages[excess:]
            logger.info("Truncated context: dropped %d oldest messages", excess)

    def clear_context(self) -> None:
        self.context_messages.clear()
        logger.info("Context window cleared")

    def compact_context(self, keep: int = 10) -> int:
        if len(self.context_messages) <= keep:
            return 0
        dropped = len(self.context_messages) - keep
        self.context_messages = self.context_messages[-keep:]
        logger.info("Compacted context: kept %d, dropped %d", keep, dropped)
        return dropped

    # ── YOLO mode

    def toggle_yolo(self) -> bool:
        self.yolo_mode = not self.yolo_mode
        logger.warning("YOLO mode toggled → %s", self.yolo_mode)
        return self.yolo_mode
