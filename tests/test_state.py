"""
Tests for AppState.
"""


def test_add_message(state):
    state.add_message("user", "hello")
    assert len(state.context_messages) == 1
    assert state.context_messages[0]["role"] == "user"


def test_clear_context(state):
    state.add_message("user", "hello")
    state.add_message("assistant", "hi")
    state.clear_context()
    assert len(state.context_messages) == 0


def test_toggle_yolo(state):
    assert state.yolo_mode is False
    result = state.toggle_yolo()
    assert result is True
    assert state.yolo_mode is True
    result = state.toggle_yolo()
    assert result is False


def test_compact_context(state):
    for i in range(20):
        state.add_message("user", f"msg {i}")
    dropped = state.compact_context(keep=5)
    assert dropped == 15
    # 5 kept messages + 1 summary marker = 6 total
    assert len(state.context_messages) == 6
    assert "compacted" in state.context_messages[0]["content"].lower()


def test_get_messages_for_api_includes_system(state):
    state.add_message("user", "test")
    msgs = state.get_messages_for_api()
    assert msgs[0]["role"] == "system"
    assert len(msgs) == 2
