"""
Jack The Shadow — Shodan Integration Service

Query Shodan for internet-wide reconnaissance data.
Requires a Shodan API key stored in ~/.jshadow/config.json.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import requests

from jack_the_shadow.session.paths import JSHADOW_DIR
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("services.shodan")

_SHODAN_API_BASE = "https://api.shodan.io"
_TIMEOUT = 15


class ShodanService:
    """Client for the Shodan REST API."""

    def __init__(self) -> None:
        self._api_key = self._load_api_key()
        self._session = requests.Session()

    @staticmethod
    def _load_api_key() -> Optional[str]:
        """Load Shodan API key from ~/.jshadow/config.json."""
        config_path = JSHADOW_DIR / "config.json"
        if not config_path.exists():
            return None
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data.get("shodan_api_key")
        except (json.JSONDecodeError, OSError):
            return None

    def is_configured(self) -> bool:
        return self._api_key is not None

    def host_lookup(self, ip: str) -> dict[str, Any]:
        """Get all available information on a host."""
        if not self._api_key:
            return {
                "error": (
                    "Shodan API key not configured. Set it with "
                    "/config shodan_api_key YOUR_KEY or add to "
                    "~/.jshadow/config.json"
                ),
            }
        try:
            resp = self._session.get(
                f"{_SHODAN_API_BASE}/shodan/host/{ip}",
                params={"key": self._api_key},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._simplify_host(data)
        except requests.RequestException as exc:
            logger.error("Shodan host lookup failed: %s", exc)
            return {"error": str(exc)}

    def search(
        self, query: str, max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search Shodan for hosts matching a query."""
        if not self._api_key:
            return [{"error": "Shodan API key not configured."}]
        try:
            resp = self._session.get(
                f"{_SHODAN_API_BASE}/shodan/host/search",
                params={"key": self._api_key, "query": query},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            results: list[dict[str, Any]] = []
            for match in data.get("matches", [])[:max_results]:
                banner_raw = match.get("data", "")
                results.append({
                    "ip": match.get("ip_str", ""),
                    "port": match.get("port", ""),
                    "org": match.get("org", ""),
                    "os": match.get("os", ""),
                    "product": match.get("product", ""),
                    "version": match.get("version", ""),
                    "country": match.get("location", {}).get("country_name", ""),
                    "city": match.get("location", {}).get("city", ""),
                    "hostnames": match.get("hostnames", []),
                    "banner": (
                        banner_raw[:200] + "..."
                        if len(banner_raw) > 200
                        else banner_raw
                    ),
                })
            return results
        except requests.RequestException as exc:
            logger.error("Shodan search failed: %s", exc)
            return [{"error": str(exc)}]

    def exploit_search(
        self, query: str, max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search Shodan's exploit database (no API key required for this)."""
        try:
            resp = self._session.get(
                "https://exploits.shodan.io/api/search",
                params={"query": query, "key": self._api_key or ""},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            results: list[dict[str, Any]] = []
            for match in data.get("matches", [])[:max_results]:
                results.append({
                    "description": match.get("description", "")[:200],
                    "source": match.get("source", ""),
                    "id": match.get("id", ""),
                    "type": match.get("type", ""),
                    "platform": match.get("platform", ""),
                    "date": match.get("date", ""),
                })
            return results
        except requests.RequestException as exc:
            logger.error("Shodan exploit search failed: %s", exc)
            return [{"error": str(exc)}]

    def api_info(self) -> dict[str, Any]:
        """Check API key status and usage."""
        if not self._api_key:
            return {"error": "Shodan API key not configured."}
        try:
            resp = self._session.get(
                f"{_SHODAN_API_BASE}/api-info",
                params={"key": self._api_key},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            return {"error": str(exc)}

    @staticmethod
    def _simplify_host(data: dict[str, Any]) -> dict[str, Any]:
        """Extract key information from host lookup."""
        ports = data.get("ports", [])
        vulns = data.get("vulns", [])
        return {
            "ip": data.get("ip_str", ""),
            "hostnames": data.get("hostnames", []),
            "country": data.get("country_name", ""),
            "city": data.get("city", ""),
            "org": data.get("org", ""),
            "isp": data.get("isp", ""),
            "os": data.get("os", ""),
            "ports": sorted(ports),
            "vulns": vulns[:20],
            "last_update": data.get("last_update", ""),
            "services": [
                {
                    "port": svc.get("port"),
                    "transport": svc.get("transport", ""),
                    "product": svc.get("product", ""),
                    "version": svc.get("version", ""),
                    "banner": (
                        svc.get("data", "")[:150] + "..."
                        if len(svc.get("data", "")) > 150
                        else svc.get("data", "")
                    ),
                }
                for svc in data.get("data", [])[:10]
            ],
        }
