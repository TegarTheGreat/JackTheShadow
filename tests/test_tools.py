"""
Tests for tool schemas and registry.
"""

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.registry import ToolRegistry, build_default_registry


def test_build_default_registry_has_all_tools():
    registry = build_default_registry()
    names = registry.list_names()
    assert len(names) == 30
    expected = {
        "bash_execute", "file_read", "file_write", "file_edit",
        "grep_search", "glob_find", "list_directory", "http_request",
        "web_fetch", "web_search", "cve_lookup",
        "memory_read", "memory_write", "todo_read", "todo_write",
        "git_command", "doctor_check", "batch_execute",
        "apply_patch", "python_repl", "ask_user", "mcp_call",
        "payload_generate", "encode_decode", "network_recon",
        "report_generate", "exploit_search", "wordlist_manage",
        "hash_analyze", "shodan_recon",
    }
    assert set(names) == expected


def test_schemas_are_valid_openai_format():
    registry = build_default_registry()
    schemas = registry.get_all_schemas()
    for schema in schemas:
        assert schema["type"] == "function"
        assert "function" in schema
        func = schema["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func


def test_risk_aware_tools_have_risk_level():
    registry = build_default_registry()
    risk_tools = {"bash_execute", "file_write", "file_edit", "http_request", "mcp_call",
                  "git_command", "batch_execute", "apply_patch", "python_repl",
                  "network_recon"}
    schemas = registry.get_all_schemas()
    for schema in schemas:
        name = schema["function"]["name"]
        params = schema["function"]["parameters"]
        if name in risk_tools:
            assert "risk_level" in params.get("properties", {}), f"{name} missing risk_level"
            assert "risk_level" in params.get("required", []), f"{name} risk_level not required"
