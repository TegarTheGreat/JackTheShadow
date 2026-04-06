"""
Jack The Shadow — CVE Lookup Tool

Searches the NIST NVD for CVE information.
"""

from __future__ import annotations

from typing import Any, ClassVar

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result


class CVELookupTool(BaseTool):
    name: ClassVar[str] = "cve_lookup"
    description: ClassVar[str] = (
        "Search the NIST National Vulnerability Database (NVD) for CVE information. "
        "Provide a keyword (e.g. 'Apache Log4j') or a specific CVE ID (e.g. 'CVE-2021-44228'). "
        "Returns CVE IDs, descriptions, CVSS scores, and severity ratings."
    )
    risk_aware: ClassVar[bool] = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "CVE ID (e.g. 'CVE-2021-44228') or keyword to search (e.g. 'Apache Log4j').",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5, max: 10).",
                },
            },
            "required": ["query"],
        }


def handle_cve_lookup(
    executor: Any,
    query: str,
    max_results: int = 5,
) -> dict[str, str]:
    """Search NVD for CVE data."""
    from jack_the_shadow.services.nvd import NVDClient

    max_results = min(max(1, max_results), 10)
    client = NVDClient()

    # If it looks like a CVE ID, do a direct lookup
    if query.upper().startswith("CVE-"):
        detail = client.get_cve_details(query.upper())
        if detail is None:
            return result("error", message=f"CVE not found: {query}")
        import json
        return result("success", output=json.dumps(detail, indent=2, ensure_ascii=False))

    # Otherwise keyword search
    results = client.search_cve(query, results_per_page=max_results)
    if not results:
        return result("success", output=f"No CVEs found for keyword: {query}")

    import json
    return result("success", output=json.dumps(results, indent=2, ensure_ascii=False))
