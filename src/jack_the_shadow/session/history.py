"""
Jack The Shadow — Session History Persistence

Append-only JSONL session files in ~/.jshadow/sessions/.
Each turn is written immediately (survives crashes).

File format:
  Line 1: metadata JSON (session_id, date, target, model, phase, …)
  Lines 2+: individual message JSON objects (appended per-turn)

Inspired by Claude Code's append-only session architecture.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from jack_the_shadow.session.paths import JSHADOW_DIR, ensure_session_dir
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("session.history")

SESSIONS_DIR: Path = JSHADOW_DIR / "sessions"
LAST_SESSION_FILE: Path = JSHADOW_DIR / ".last_session"


def _ensure_sessions_dir() -> Path:
    ensure_session_dir()
    return SESSIONS_DIR


def generate_session_id() -> str:
    """Create a short unique session ID."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


# ── Active Session Writer ─────────────────────────────────────────────

class SessionWriter:
    """Manages the active session file with append-only writes.

    Each message is written immediately so no data is lost on crash.
    """

    def __init__(self, state: Any) -> None:
        self._sessions_dir = _ensure_sessions_dir()
        self._session_id = generate_session_id()
        self._filepath = self._sessions_dir / f"{self._session_id}.jsonl"
        self._message_count = 0
        self._tool_count = 0
        self._start_time = time.time()
        self._state = state
        self._closed = False

        self._write_metadata(state)
        _save_last_session_id(self._session_id)

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def filepath(self) -> str:
        return str(self._filepath)

    def _write_metadata(self, state: Any) -> None:
        """Write the metadata header line."""
        metadata = {
            "type": "metadata",
            "session_id": self._session_id,
            "date": datetime.now(timezone.utc).isoformat(),
            "target": getattr(state, "target", ""),
            "model": getattr(state, "model", ""),
            "language": getattr(state, "language", "en"),
            "phase": getattr(state, "phase", "recon"),
            "yolo_mode": getattr(state, "yolo_mode", False),
            "message_count": 0,
        }
        self._append_line(json.dumps(metadata, ensure_ascii=False))

    def append_message(self, msg: dict[str, Any]) -> None:
        """Append a single message to the session file (immediate flush)."""
        if self._closed:
            return
        safe = _sanitize_message(msg)
        self._append_line(json.dumps(safe, ensure_ascii=False))
        self._message_count += 1
        if safe.get("role") == "tool":
            self._tool_count += 1

    def finalize(self, state: Any) -> Optional[str]:
        """Update the metadata line with final counts and mark closed."""
        if self._closed or self._message_count == 0:
            return None
        self._closed = True

        duration = time.time() - self._start_time
        metadata = {
            "type": "metadata",
            "session_id": self._session_id,
            "date": datetime.now(timezone.utc).isoformat(),
            "target": getattr(state, "target", ""),
            "model": getattr(state, "model", ""),
            "language": getattr(state, "language", "en"),
            "phase": getattr(state, "phase", "recon"),
            "yolo_mode": getattr(state, "yolo_mode", False),
            "message_count": self._message_count,
            "tool_count": self._tool_count,
            "duration_seconds": round(duration, 1),
        }

        # Rewrite the first line with final metadata
        try:
            self._rewrite_header(json.dumps(metadata, ensure_ascii=False))
        except OSError as exc:
            logger.warning("Failed to finalize session header: %s", exc)

        logger.info(
            "Session finalized: %s (%d msgs, %d tools, %.0fs)",
            self._filepath.name, self._message_count, self._tool_count, duration,
        )
        return str(self._filepath)

    def _append_line(self, line: str) -> None:
        """Append a line to the JSONL file with immediate flush."""
        try:
            with open(self._filepath, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
        except OSError as exc:
            logger.error("Failed to append to session file: %s", exc)

    def _rewrite_header(self, new_header: str) -> None:
        """Rewrite just the first line (metadata) of the JSONL file."""
        try:
            with open(self._filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                lines[0] = new_header + "\n"
                with open(self._filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)
        except OSError as exc:
            logger.error("Failed to rewrite session header: %s", exc)


# ── Last Session Tracking ─────────────────────────────────────────────

def _save_last_session_id(session_id: str) -> None:
    """Remember the last active session ID for --continue."""
    try:
        LAST_SESSION_FILE.write_text(session_id, encoding="utf-8")
    except OSError:
        pass


def get_last_session_id() -> Optional[str]:
    """Return the last active session ID, or None."""
    try:
        if LAST_SESSION_FILE.exists():
            sid = LAST_SESSION_FILE.read_text(encoding="utf-8").strip()
            return sid if sid else None
    except OSError:
        pass
    return None


# ── Legacy save (for backward compatibility) ──────────────────────────

def save_session(state: Any) -> Optional[str]:
    """Save current conversation to a JSONL file (one-shot). Returns filepath or None.

    Prefer SessionWriter for incremental saves; this exists for
    crash-recovery paths that don't have an active writer.
    """
    if not state.context_messages:
        return None

    sessions_dir = _ensure_sessions_dir()
    session_id = generate_session_id()
    filepath = sessions_dir / f"{session_id}.jsonl"

    metadata = {
        "type": "metadata",
        "session_id": session_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "target": getattr(state, "target", ""),
        "model": getattr(state, "model", ""),
        "language": getattr(state, "language", "en"),
        "phase": getattr(state, "phase", "recon"),
        "yolo_mode": getattr(state, "yolo_mode", False),
        "message_count": len(state.context_messages),
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            for msg in state.context_messages:
                safe_msg = _sanitize_message(msg)
                f.write(json.dumps(safe_msg, ensure_ascii=False) + "\n")
        _save_last_session_id(session_id)
        logger.info("Session saved: %s (%d messages)", filepath, len(state.context_messages))
        return str(filepath)
    except OSError as exc:
        logger.error("Failed to save session: %s", exc)
        return None


# ── Message Sanitizer ─────────────────────────────────────────────────

def _sanitize_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Keep only JSON-serializable fields from a message."""
    safe: dict[str, Any] = {"role": msg.get("role", "unknown")}
    if "content" in msg:
        safe["content"] = str(msg["content"]) if msg["content"] is not None else ""
    if "tool_calls" in msg:
        safe["tool_calls"] = msg["tool_calls"]
    if "tool_call_id" in msg:
        safe["tool_call_id"] = msg["tool_call_id"]
    return safe


# ── Session Loading ───────────────────────────────────────────────────

def load_session(session_id: str) -> Optional[dict[str, Any]]:
    """Load a session by ID. Returns dict with 'metadata' and 'messages'."""
    sessions_dir = _ensure_sessions_dir()
    filepath = sessions_dir / f"{session_id}.jsonl"

    if not filepath.exists():
        # Try partial match (user might type just the date prefix)
        candidates = sorted(sessions_dir.glob(f"{session_id}*.jsonl"))
        if candidates:
            filepath = candidates[-1]  # newest match
        else:
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


# ── Session Listing ───────────────────────────────────────────────────

def list_sessions(limit: int = 20) -> list[dict[str, Any]]:
    """List saved sessions, newest first. Includes enriched metadata."""
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
                "phase": meta.get("phase", ""),
                "messages": meta.get("message_count", 0),
                "tools": meta.get("tool_count", 0),
                "duration": meta.get("duration_seconds", 0),
            })
        except (OSError, json.JSONDecodeError):
            continue

    return sessions


# ── Session Export ────────────────────────────────────────────────────

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
    lines.append(f"**Phase:** {getattr(state, 'phase', 'recon')}")
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
