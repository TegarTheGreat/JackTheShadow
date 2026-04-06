"""
Jack The Shadow — Session History Persistence

Saves/loads conversation sessions as JSONL files in ~/.jshadow/sessions/.
Each session file contains:
  Line 1: metadata JSON (date, target, model, language)
  Lines 2+: individual message JSON objects
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from jack_the_shadow.session.paths import JSHADOW_DIR, ensure_session_dir
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("session.history")

SESSIONS_DIR: Path = JSHADOW_DIR / "sessions"


def _ensure_sessions_dir() -> Path:
    ensure_session_dir()
    return SESSIONS_DIR


def generate_session_id() -> str:
    """Create a short unique session ID."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def save_session(state: Any) -> Optional[str]:
    """Save current conversation to a JSONL file. Returns filepath or None."""
    if not state.context_messages:
        return None

    sessions_dir = _ensure_sessions_dir()
    session_id = generate_session_id()
    filepath = sessions_dir / f"{session_id}.jsonl"

    metadata = {
        "type": "metadata",
        "session_id": session_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "target": state.target,
        "model": state.model,
        "language": state.language,
        "message_count": len(state.context_messages),
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            for msg in state.context_messages:
                # Only save serializable messages
                safe_msg = _sanitize_message(msg)
                f.write(json.dumps(safe_msg, ensure_ascii=False) + "\n")
        logger.info("Session saved: %s (%d messages)", filepath, len(state.context_messages))
        return str(filepath)
    except OSError as exc:
        logger.error("Failed to save session: %s", exc)
        return None


def _sanitize_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Keep only JSON-serializable fields from a message."""
    safe: dict[str, Any] = {"role": msg.get("role", "unknown")}
    if "content" in msg:
        safe["content"] = str(msg["content"])
    if "tool_calls" in msg:
        safe["tool_calls"] = msg["tool_calls"]
    if "tool_call_id" in msg:
        safe["tool_call_id"] = msg["tool_call_id"]
    return safe


def load_session(session_id: str) -> Optional[dict[str, Any]]:
    """Load a session by ID. Returns dict with 'metadata' and 'messages'."""
    sessions_dir = _ensure_sessions_dir()
    filepath = sessions_dir / f"{session_id}.jsonl"

    if not filepath.exists():
        logger.warning("Session file not found: %s", filepath)
        return None

    return _read_session_file(filepath)


def _read_session_file(filepath: Path) -> Optional[dict[str, Any]]:
    """Parse a JSONL session file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as exc:
        logger.error("Failed to read session: %s", exc)
        return None

    if not lines:
        return None

    try:
        metadata = json.loads(lines[0])
    except json.JSONDecodeError:
        metadata = {"type": "metadata"}

    messages: list[dict[str, Any]] = []
    for line in lines[1:]:
        line = line.strip()
        if line:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return {"metadata": metadata, "messages": messages}


def list_sessions(limit: int = 20) -> list[dict[str, Any]]:
    """List saved sessions, newest first."""
    sessions_dir = _ensure_sessions_dir()
    session_files = sorted(sessions_dir.glob("*.jsonl"), reverse=True)

    sessions: list[dict[str, Any]] = []
    for filepath in session_files[:limit]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                first_line = f.readline()
            meta = json.loads(first_line)
            sessions.append({
                "id": meta.get("session_id", filepath.stem),
                "date": meta.get("date", "unknown"),
                "target": meta.get("target", ""),
                "model": meta.get("model", ""),
                "messages": meta.get("message_count", 0),
            })
        except (OSError, json.JSONDecodeError):
            continue

    return sessions


def export_session(state: Any, filepath: Optional[str] = None) -> Optional[str]:
    """Export current conversation as a markdown report."""
    if not state.context_messages:
        return None

    if not filepath:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_slug = state.target.replace("/", "_").replace(":", "_")[:30] if state.target else "session"
        filepath = f"jshadow_report_{target_slug}_{ts}.md"

    lines: list[str] = []
    lines.append("# Jack The Shadow — Session Report\n")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Target:** {state.target or '(none)'}")
    lines.append(f"**Model:** {state.model}")
    lines.append(f"**Language:** {state.language}\n")
    lines.append("---\n")

    for msg in state.context_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            lines.append(f"## 🧑 User\n\n{content}\n")
        elif role == "assistant":
            if content:
                lines.append(f"## 🗡 Jack\n\n{content}\n")
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    lines.append(f"**Tool call:** `{func.get('name', '?')}`")
                    lines.append(f"```json\n{func.get('arguments', '{}')}\n```\n")
        elif role == "tool":
            content_preview = content[:500] + "..." if len(content) > 500 else content
            lines.append(f"**Tool result:**\n```\n{content_preview}\n```\n")

    lines.append("---\n*Generated by Jack The Shadow*\n")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Session exported to: %s", filepath)
        return filepath
    except OSError as exc:
        logger.error("Failed to export session: %s", exc)
        return None
