"""
Jack The Shadow — Shodan Recon Tool

Internet-wide reconnaissance via the Shodan API.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.shodan")


class ShodanTool(BaseTool):
    name: ClassVar[str] = "shodan_recon"
    description: ClassVar[str] = (
        "Search Shodan for internet-wide host intelligence, open ports, "
        "vulnerabilities, and service banners. Requires Shodan API key "
        "configured in ~/.jshadow/config.json."
    )
    risk_aware: ClassVar[bool] = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "host_lookup", "search",
                        "exploit_search", "api_info",
                    ],
                    "description": (
                        "host_lookup: get info on specific IP. "
                        "search: search Shodan by query. "
                        "exploit_search: search exploit database. "
                        "api_info: check API key status."
                    ),
                },
                "query": {
                    "type": "string",
                    "description": (
                        "IP address for host_lookup, or search query "
                        "for search/exploit_search."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results (default: 10, max: 20).",
                },
            },
            "required": ["action", "query"],
        }


def handle_shodan_recon(
    executor: "ToolExecutor",
    action: str,
    query: str,
    max_results: int = 10,
) -> dict[str, str]:
    """Execute Shodan reconnaissance."""
    from jack_the_shadow.services.shodan_service import ShodanService

    max_results = min(max(1, max_results), 20)
    client = ShodanService()

    if not client.is_configured() and action != "api_info":
        return result(
            "error",
            message=(
                "Shodan API key not configured. Add your key:\n"
                "1. Edit ~/.jshadow/config.json\n"
                '2. Add: {"shodan_api_key": "YOUR_KEY_HERE"}\n'
                "Get free key at: https://account.shodan.io/"
            ),
        )

    if action == "host_lookup":
        data = client.host_lookup(query)
        if "error" in data:
            return result("error", message=data["error"])
        return result(
            "success",
            output=truncate(json.dumps(data, indent=2, ensure_ascii=False)),
        )

    if action == "search":
        data = client.search(query, max_results)
        if data and "error" in data[0]:
            return result("error", message=data[0]["error"])
        return result(
            "success",
            output=truncate(json.dumps(data, indent=2, ensure_ascii=False)),
        )

    if action == "exploit_search":
        data = client.exploit_search(query, max_results)
        if data and "error" in data[0]:
            return result("error", message=data[0]["error"])
        return result(
            "success",
            output=truncate(json.dumps(data, indent=2, ensure_ascii=False)),
        )

    if action == "api_info":
        data = client.api_info()
        if "error" in data:
            return result("error", message=data["error"])
        return result("success", output=json.dumps(data, indent=2))

    return result("error", message=f"Unknown action: {action}")
