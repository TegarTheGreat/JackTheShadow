"""
Jack The Shadow — BaseTool ABC

Abstract base class for every tool Jack can call.
Inspired by claude-code's buildTool() factory pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional


@dataclass
class ToolResult:
    """Standardised result from tool execution."""
    status: str  # "success" | "error"
    output: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"status": self.status}
        if self.output:
            d["output"] = self.output
        if self.message:
            d["message"] = self.message
        if self.metadata:
            d.update(self.metadata)
        return d


@dataclass
class ToolContext:
    """Runtime context passed to tool.execute()."""
    state: Any  # AppState — avoids circular import
    executor: Any  # ToolExecutor
    risk_level: str = "Low"


class BaseTool(ABC):
    """Abstract base for every tool Jack can call.

    Subclasses must define class-level ``name``, ``description``,
    ``parameters_schema()``.  Optionally override ``execute()`` to
    move execution logic into the tool itself (preferred pattern).
    """

    name: ClassVar[str]
    description: ClassVar[str]
    risk_aware: ClassVar[bool] = False
    read_only: ClassVar[bool] = False
    concurrent_safe: ClassVar[bool] = False
    max_result_chars: ClassVar[int] = 50_000

    @classmethod
    @abstractmethod
    def parameters_schema(cls) -> dict[str, Any]:
        ...

    @classmethod
    def execute(cls, args: dict[str, Any], context: ToolContext) -> Optional[ToolResult]:
        """Execute the tool.  Return None to fall back to ToolExecutor dispatch."""
        return None

    @classmethod
    def to_openai_schema(cls) -> dict[str, Any]:
        params = cls.parameters_schema()
        if cls.risk_aware:
            params = _inject_risk_level(params)
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": params,
            },
        }


def _inject_risk_level(params: dict[str, Any]) -> dict[str, Any]:
    """Auto-inject the risk_level enum into risk-aware tool schemas."""
    params = dict(params)
    props = dict(params.get("properties", {}))
    props["risk_level"] = {
        "type": "string",
        "enum": ["Low", "Medium", "High", "Critical"],
        "description": (
            "Honest assessment of danger. Low = safe/read-only, "
            "Medium = reversible, High = potentially destructive, "
            "Critical = irreversible / production impact."
        ),
    }
    params["properties"] = props
    required = list(params.get("required", []))
    if "risk_level" not in required:
        required.append("risk_level")
    params["required"] = required
    return params
