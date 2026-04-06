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
