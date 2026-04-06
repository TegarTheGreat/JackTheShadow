"""
Jack The Shadow — Tool Registry

Centralised registry of all available tools.
"""

from __future__ import annotations

from typing import Any, Optional

from jack_the_shadow.tools.base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, type[BaseTool]] = {}

    def register(self, tool_cls: type[BaseTool]) -> None:
        self._tools[tool_cls.name] = tool_cls

    def get_tool(self, name: str) -> Optional[type[BaseTool]]:
        return self._tools.get(name)

    def get_all_schemas(self) -> list[dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())


def build_default_registry() -> ToolRegistry:
    """Create a registry pre-loaded with all 26 built-in tools."""
    from jack_the_shadow.tools.builtin.ask import AskUserTool
    from jack_the_shadow.tools.builtin.bash import BashExecuteTool
    from jack_the_shadow.tools.builtin.batch import BatchExecuteTool
    from jack_the_shadow.tools.builtin.cve import CVELookupTool
    from jack_the_shadow.tools.builtin.directory import ListDirectoryTool
    from jack_the_shadow.tools.builtin.doctor import DoctorTool
    from jack_the_shadow.tools.builtin.exploit_search import ExploitSearchTool
    from jack_the_shadow.tools.builtin.files import FileEditTool, FileReadTool, FileWriteTool
    from jack_the_shadow.tools.builtin.git import GitCommandTool
    from jack_the_shadow.tools.builtin.http import HttpRequestTool
    from jack_the_shadow.tools.builtin.memory import MemoryReadTool, MemoryWriteTool
    from jack_the_shadow.tools.builtin.network import NetworkReconTool
    from jack_the_shadow.tools.builtin.patch import ApplyPatchTool
    from jack_the_shadow.tools.builtin.repl import ReplTool
    from jack_the_shadow.tools.builtin.report import ReportGenerateTool
    from jack_the_shadow.tools.builtin.search import GlobFindTool, GrepSearchTool
    from jack_the_shadow.tools.builtin.todo import TodoReadTool, TodoWriteTool
    from jack_the_shadow.tools.builtin.web_fetch import WebFetchTool
    from jack_the_shadow.tools.builtin.wordlist import WordlistTool
    from jack_the_shadow.tools.builtin.web_search import WebSearchTool
    from jack_the_shadow.tools.mcp.tool import MCPCallTool

    registry = ToolRegistry()
    for tool_cls in [
        BashExecuteTool,
        FileReadTool,
        FileWriteTool,
        FileEditTool,
        GrepSearchTool,
        GlobFindTool,
        ListDirectoryTool,
        HttpRequestTool,
        WebFetchTool,
        WebSearchTool,
        CVELookupTool,
        MemoryReadTool,
        MemoryWriteTool,
        NetworkReconTool,
        TodoReadTool,
        TodoWriteTool,
        GitCommandTool,
        DoctorTool,
        BatchExecuteTool,
        ApplyPatchTool,
        ReplTool,
        ReportGenerateTool,
        AskUserTool,
        MCPCallTool,
        ExploitSearchTool,
        WordlistTool,
    ]:
        registry.register(tool_cls)
    return registry
