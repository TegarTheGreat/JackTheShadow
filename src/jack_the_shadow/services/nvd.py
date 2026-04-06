"""
Jack The Shadow — NVD / CVE Client

Query the NIST National Vulnerability Database for CVE information.
Uses the public NVD API v2.0 (no API key required, but rate-limited).
"""

from __future__ import annotations

from typing import Any, Optional

import requests

from jack_the_shadow.utils.logger import get_logger

logger = get_logger("services.nvd")

_NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_TIMEOUT = 30


class NVDClient:
    """Lightweight client for the NIST NVD CVE API v2.0."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._session = requests.Session()
        if api_key:
            self._session.headers["apiKey"] = api_key

    def search_cve(
        self,
        keyword: str,
        results_per_page: int = 5,
    ) -> list[dict[str, Any]]:
        params = {
            "keywordSearch": keyword,
            "resultsPerPage": results_per_page,
        }
        try:
            resp = self._session.get(_NVD_BASE, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("NVD search failed: %s", exc)
            return []

        return self._simplify(data)

    def get_cve_details(self, cve_id: str) -> Optional[dict[str, Any]]:
        params = {"cveId": cve_id}
        try:
            resp = self._session.get(_NVD_BASE, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("NVD lookup failed for %s: %s", cve_id, exc)
            return None

        results = self._simplify(data)
        return results[0] if results else None

    @staticmethod
    def _simplify(raw: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for vuln in raw.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            desc_list = cve.get("descriptions", [])
            en_desc = next(
                (d["value"] for d in desc_list if d.get("lang") == "en"),
                "No description available.",
            )
            metrics = cve.get("metrics", {})
            cvss_data = metrics.get("cvssMetricV31", [{}])
            score = (
                cvss_data[0].get("cvssData", {}).get("baseScore")
                if cvss_data
                else None
            )
            severity = (
                cvss_data[0].get("cvssData", {}).get("baseSeverity")
                if cvss_data
                else None
            )
            items.append({
                "id": cve.get("id", ""),
                "description": en_desc,
                "published": cve.get("published", ""),
                "cvss_score": score,
                "severity": severity,
            })
        return items
