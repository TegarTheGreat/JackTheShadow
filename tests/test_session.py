"""Tests for the session auth module."""

import json
from pathlib import Path
from unittest.mock import patch

from jack_the_shadow.session.auth import (
    clear_credentials,
    is_logged_in,
    load_credentials,
    save_credentials,
)


def test_save_and_load_credentials(tmp_path: Path) -> None:
    cred_file = tmp_path / "credentials.json"
    with patch("jack_the_shadow.session.auth.get_credentials_path", return_value=cred_file):
        with patch("jack_the_shadow.session.auth.ensure_session_dir"):
            save_credentials("acc_123", "tok_456")

    data = json.loads(cred_file.read_text())
    assert data["cloudflare_account_id"] == "acc_123"
    assert data["cloudflare_api_token"] == "tok_456"

    with patch("jack_the_shadow.session.auth.get_credentials_path", return_value=cred_file):
        account_id, api_token = load_credentials()
    assert account_id == "acc_123"
    assert api_token == "tok_456"


def test_load_credentials_fallback_env(tmp_path: Path) -> None:
    cred_file = tmp_path / "nonexistent.json"
    with patch("jack_the_shadow.session.auth.get_credentials_path", return_value=cred_file):
        with patch.dict("os.environ", {
            "CLOUDFLARE_ACCOUNT_ID": "env_acc",
            "CLOUDFLARE_API_TOKEN": "env_tok",
        }):
            account_id, api_token = load_credentials()
    assert account_id == "env_acc"
    assert api_token == "env_tok"


def test_clear_credentials(tmp_path: Path) -> None:
    cred_file = tmp_path / "credentials.json"
    cred_file.write_text('{"cloudflare_account_id":"a","cloudflare_api_token":"b"}')

    with patch("jack_the_shadow.session.auth.get_credentials_path", return_value=cred_file):
        assert clear_credentials() is True
        assert not cred_file.exists()
        assert clear_credentials() is False


def test_is_logged_in(tmp_path: Path) -> None:
    cred_file = tmp_path / "credentials.json"
    with patch("jack_the_shadow.session.auth.get_credentials_path", return_value=cred_file):
        with patch.dict("os.environ", {}, clear=True):
            assert is_logged_in() is False

    cred_file.write_text('{"cloudflare_account_id":"a","cloudflare_api_token":"b"}')
    with patch("jack_the_shadow.session.auth.get_credentials_path", return_value=cred_file):
        assert is_logged_in() is True
