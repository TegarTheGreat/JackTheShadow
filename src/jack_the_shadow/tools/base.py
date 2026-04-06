"""
Jack The Shadow — BaseTool ABC

Abstract base class for every tool Jack can call.
Inspired by claude-code's buildTool() factory pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseTool(ABC):
    """Abstract base for every tool Jack can call."""

    name: ClassVar[str]
    description: ClassVar[str]
    risk_aware: ClassVar[bool] = False

    @classmethod
    @abstractmethod
    def parameters_schema(cls) -> dict[str, Any]:
        ...

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
