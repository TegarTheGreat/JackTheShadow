"""
Tests for session history and user config.
"""

import json
import os
from pathlib import Path

import pytest

from jack_the_shadow.core.state import AppState


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Override JSHADOW_DIR to tmp for testing."""
    import jack_the_shadow.session.paths as paths_mod
    import jack_the_shadow.session.history as hist_mod
    import jack_the_shadow.session.user_config as cfg_mod

    monkeypatch.setattr(paths_mod, "JSHADOW_DIR", tmp_path)
    monkeypatch.setattr(hist_mod, "SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(hist_mod, "LAST_SESSION_FILE", tmp_path / ".last_session")
    (tmp_path / "sessions").mkdir(exist_ok=True)
    return tmp_path


def test_save_and_list_sessions(sessions_dir):
    from jack_the_shadow.session.history import list_sessions, save_session

    state = AppState(model="test-model", language="en", target="192.168.1.1")
    state.add_message("user", "scan the target")
    state.add_message("assistant", "running nmap...")

    path = save_session(state)
    assert path is not None
    assert Path(path).exists()

    sessions = list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["target"] == "192.168.1.1"
    assert sessions[0]["messages"] == 2


def test_load_session(sessions_dir):
    from jack_the_shadow.session.history import load_session, save_session

    state = AppState(model="test-model", language="en", target="example.com")
    state.add_message("user", "hello jack")

    save_session(state)

    from jack_the_shadow.session.history import list_sessions
    sessions = list_sessions()
    session_id = sessions[0]["id"]

    data = load_session(session_id)
    assert data is not None
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "hello jack"


def test_export_session(sessions_dir, tmp_path):
    from jack_the_shadow.session.history import export_session

    state = AppState(model="test-model", language="en", target="10.0.0.1")
    state.add_message("user", "what ports are open?")

    outpath = str(tmp_path / "report.md")
    result = export_session(state, filepath=outpath)
    assert result == outpath

    content = Path(outpath).read_text()
    assert "what ports are open?" in content
    assert "10.0.0.1" in content
    assert "Session Report" in content


def test_user_config_save_load(sessions_dir, monkeypatch):
    import jack_the_shadow.session.user_config as cfg_mod
    from jack_the_shadow.session.paths import get_config_path

    monkeypatch.setattr(cfg_mod, "get_config_path", lambda: sessions_dir / "config.json")

    from jack_the_shadow.session.user_config import load_user_config, save_user_config

    save_user_config({"model": "test-model", "language": "id"})
    config = load_user_config()
    assert config["model"] == "test-model"
    assert config["language"] == "id"


def test_user_config_defaults(sessions_dir, monkeypatch):
    import jack_the_shadow.session.user_config as cfg_mod
    monkeypatch.setattr(cfg_mod, "get_config_path", lambda: sessions_dir / "nonexistent.json")

    from jack_the_shadow.session.user_config import load_user_config
    config = load_user_config()
    assert config["model"] == ""
    assert config["language"] == ""
    assert config["yolo_mode"] is False


# ── New: SessionWriter tests ─────────────────────────────────────────

def test_session_writer_incremental(sessions_dir):
    """SessionWriter appends each message immediately to JSONL."""
    from jack_the_shadow.session.history import SessionWriter

    state = AppState(model="test-model", language="en", target="10.0.0.1", phase="enum")
    writer = SessionWriter(state)

    writer.append_message({"role": "user", "content": "test msg 1"})
    writer.append_message({"role": "assistant", "content": "response 1"})

    # File should exist and have 3 lines (metadata + 2 messages)
    filepath = Path(writer.filepath)
    assert filepath.exists()
    lines = filepath.read_text().strip().split("\n")
    assert len(lines) == 3

    # Metadata should have correct fields
    meta = json.loads(lines[0])
    assert meta["target"] == "10.0.0.1"
    assert meta["phase"] == "enum"
    assert meta["type"] == "metadata"


def test_session_writer_finalize(sessions_dir):
    """Finalize updates metadata header with final counts."""
    from jack_the_shadow.session.history import SessionWriter

    state = AppState(model="test-model", language="en", target="box.htb")
    writer = SessionWriter(state)

    writer.append_message({"role": "user", "content": "scan"})
    writer.append_message({"role": "tool", "tool_call_id": "1", "content": "port 80 open"})
    writer.append_message({"role": "assistant", "content": "found port 80"})

    path = writer.finalize(state)
    assert path is not None

    # Read finalized metadata
    with open(path, "r") as f:
        meta = json.loads(f.readline())
    assert meta["message_count"] == 3
    assert meta["tool_count"] == 1
    assert meta["duration_seconds"] >= 0


def test_last_session_tracking(sessions_dir):
    """SessionWriter saves last session ID for --continue."""
    from jack_the_shadow.session.history import SessionWriter, get_last_session_id

    state = AppState(model="test-model", language="en")
    writer = SessionWriter(state)

    last_id = get_last_session_id()
    assert last_id == writer.session_id


def test_session_load_partial_id(sessions_dir):
    """load_session supports partial ID matching."""
    from jack_the_shadow.session.history import load_session, save_session

    state = AppState(model="test-model", language="en", target="test.com")
    state.add_message("user", "hi")
    save_session(state)

    from jack_the_shadow.session.history import list_sessions
    sessions = list_sessions()
    full_id = sessions[0]["id"]

    # Partial match (date prefix)
    partial = full_id[:8]  # e.g., "20260406"
    data = load_session(partial)
    assert data is not None
    assert len(data["messages"]) == 1


def test_session_metadata_enriched(sessions_dir):
    """Session metadata includes phase, yolo_mode, etc."""
    from jack_the_shadow.session.history import save_session, list_sessions

    state = AppState(model="test-model", language="id", target="vuln.app", phase="exploit")
    state.yolo_mode = True
    state.add_message("user", "pwn it")
    save_session(state)

    sessions = list_sessions()
    assert sessions[0]["phase"] == "exploit"


# ── New: Smart truncation tests ──────────────────────────────────────

def test_smart_truncation_keeps_first_message():
    """Smart truncation preserves first user message + recent messages."""
    from jack_the_shadow.config import MAX_CONTEXT_MESSAGES

    state = AppState(model="test-model", language="en")

    # Add enough messages to trigger truncation
    for i in range(MAX_CONTEXT_MESSAGES + 10):
        state.add_message("user", f"msg {i}")

    # First message should be preserved
    assert state.context_messages[0]["content"] == "msg 0"
    # Second should be the truncation marker
    assert "truncated" in state.context_messages[1]["content"].lower()
    # Total should be within limits
    assert len(state.context_messages) <= MAX_CONTEXT_MESSAGES


def test_state_restore_from_metadata():
    """restore_from_metadata restores all fields."""
    state = AppState(model="default-model", language="en")
    meta = {
        "target": "restored.com",
        "model": "restored-model",
        "language": "id",
        "phase": "exploit",
        "yolo_mode": True,
    }
    state.restore_from_metadata(meta)
    assert state.target == "restored.com"
    assert state.model == "restored-model"
    assert state.language == "id"
    assert state.phase == "exploit"
    assert state.yolo_mode is True
