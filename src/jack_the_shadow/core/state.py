"""
Jack The Shadow — Global Application State

Manages the conversation context window, YOLO mode flag, language,
session metadata, and incremental session persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from jack_the_shadow.config import MAX_CONTEXT_MESSAGES
from jack_the_shadow.config.prompts import get_system_prompt
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.state")


@dataclass
class AppState:
    """Encapsulates all mutable session state."""

    model: str
    language: str = "en"
    target: str = ""
    yolo_mode: bool = False
    phase: str = "recon"  # Current pentest phase
    context_messages: list[dict[str, Any]] = field(default_factory=list)

    # Incremental session writer (set by orchestrator)
    _session_writer: Optional[Any] = field(default=None, repr=False)

    # ── Message helpers

    def add_message(self, role: str, content: str) -> None:
        msg = {"role": role, "content": content}
        self.context_messages.append(msg)
        self._persist_message(msg)
        self.truncate_context()
        logger.debug("Added %s message (%d chars)", role, len(content))

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        msg = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }
        self.context_messages.append(msg)
        self._persist_message(msg)
        logger.debug("Added tool result for call %s", tool_call_id)

    def add_assistant_message(self, message: dict[str, Any]) -> None:
        """Store assistant message, ensuring content is never null."""
        msg = dict(message)
        if msg.get("content") is None:
            msg["content"] = ""
        self.context_messages.append(msg)
        self._persist_message(msg)
        self.truncate_context()
        logger.debug("Added assistant message (raw)")

    def _persist_message(self, msg: dict[str, Any]) -> None:
        """Write message to active session file immediately."""
        if self._session_writer is not None:
            try:
                self._session_writer.append_message(msg)
            except Exception as exc:
                logger.warning("Session write failed: %s", exc)

    def get_messages_for_api(self) -> list[dict[str, Any]]:
        prompt = get_system_prompt(self.language)
        if self.target:
            prompt += f"\n\n## Active Target\nCurrent target scope: `{self.target}`"
        # Inject current pentest phase
        prompt += f"\n\n## Current Phase: {self.phase.upper()}\nFocus your tool calls on {self.phase} techniques."
        # Inject persistent memory (JSHADOW.md, notes, etc.)
        try:
            from jack_the_shadow.core.memory import build_memory_prompt
            memory_section = build_memory_prompt()
            if memory_section:
                prompt += memory_section
        except Exception:
            pass  # memory discovery is optional
        system = {"role": "system", "content": prompt}
        return [system] + list(self.context_messages)

    # ── Context management (smart truncation)

    def truncate_context(self) -> None:
        """Smart context truncation: keep important messages.

        Unlike naive FIFO, this preserves:
        1. The first user message (original intent/target)
        2. All messages from the last N turns
        3. Injects a [context truncated] marker so AI knows history was dropped
        """
        if len(self.context_messages) <= MAX_CONTEXT_MESSAGES:
            return

        keep_count = MAX_CONTEXT_MESSAGES - 2  # Reserve 2 slots: first msg + marker
        if keep_count < 5:
            keep_count = MAX_CONTEXT_MESSAGES  # Too small, just do FIFO

        # Preserve the first user message (if it exists and is a user msg)
        first_msg = None
        if self.context_messages and self.context_messages[0].get("role") == "user":
            first_msg = self.context_messages[0]

        recent = self.context_messages[-keep_count:]
        dropped = len(self.context_messages) - keep_count

        new_context: list[dict[str, Any]] = []
        if first_msg and first_msg not in recent:
            new_context.append(first_msg)
            new_context.append({
                "role": "system",
                "content": (
                    f"[Context truncated: {dropped} older messages were removed "
                    f"to stay within the context window. The first user message "
                    f"and the most recent {keep_count} messages are preserved.]"
                ),
            })
        new_context.extend(recent)

        self.context_messages = new_context
        logger.info(
            "Smart truncation: kept first msg + %d recent, dropped %d",
            keep_count, dropped,
        )

    def clear_context(self) -> None:
        self.context_messages.clear()
        logger.info("Context window cleared")

    def compact_context(self, keep: int = 10) -> int:
        """Compact context, keeping the most recent messages.

        Inserts a summary marker so the AI knows earlier context existed.
        """
        if len(self.context_messages) <= keep:
            return 0
        dropped = len(self.context_messages) - keep
        recent = self.context_messages[-keep:]

        summary_marker = {
            "role": "system",
            "content": (
                f"[Context compacted: {dropped} earlier messages were removed. "
                f"Keeping {keep} most recent messages. Prior conversation context "
                f"may be incomplete — check /memory and /history for full details.]"
            ),
        }
        self.context_messages = [summary_marker] + recent
        logger.info("Compacted context: kept %d, dropped %d", keep, dropped)
        return dropped

    # ── YOLO mode

    def toggle_yolo(self) -> bool:
        self.yolo_mode = not self.yolo_mode
        logger.warning("YOLO mode toggled → %s", self.yolo_mode)
        return self.yolo_mode

    # ── Serialization helpers for session resume

    def to_resume_dict(self) -> dict[str, Any]:
        """Export state fields needed for session resume."""
        return {
            "model": self.model,
            "language": self.language,
            "target": self.target,
            "yolo_mode": self.yolo_mode,
            "phase": self.phase,
        }

    def restore_from_metadata(self, meta: dict[str, Any]) -> None:
        """Restore state fields from session metadata."""
        if meta.get("target"):
            self.target = meta["target"]
        if meta.get("model"):
            self.model = meta["model"]
        if meta.get("language"):
            self.language = meta["language"]
        if meta.get("phase"):
            self.phase = meta["phase"]
        if "yolo_mode" in meta:
            self.yolo_mode = bool(meta["yolo_mode"])
