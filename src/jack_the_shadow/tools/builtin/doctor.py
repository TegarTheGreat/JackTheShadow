"""
Jack The Shadow — Doctor Check Tool

System diagnostics: verify which security tools are installed and report versions.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Any

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.doctor")

PENTEST_TOOLS: dict[str, list[str]] = {
    "recon": [
        "nmap", "masscan", "whois", "dig", "dnsrecon",
        "amass", "subfinder", "theHarvester",
    ],
    "web": [
        "nikto", "gobuster", "dirb", "sqlmap", "wfuzz",
        "ffuf", "whatweb", "wpscan", "nuclei", "httpx",
    ],
    "exploitation": [
        "metasploit-framework:msfconsole", "searchsploit",
        "hydra", "john", "hashcat", "crackmapexec",
    ],
    "network": [
        "tcpdump", "wireshark:tshark", "netcat:nc",
        "socat", "proxychains4:proxychains", "responder",
    ],
    "crypto": [
        "openssl", "sslscan", "testssl.sh:testssl", "hashid",
    ],
    "forensics": [
        "volatility:vol.py", "binwalk", "foremost",
        "exiftool", "strings",
    ],
    "general": [
        "python3", "pip3", "git", "curl", "wget",
        "jq", "tmux", "screen",
    ],
}


def _parse_tool_entry(entry: str) -> tuple[str, str]:
    """Return (display_name, binary_name) from an entry like 'display:binary' or 'name'."""
    if ":" in entry:
        display, binary = entry.split(":", 1)
        return display, binary
    return entry, entry


def _get_version(binary: str) -> str:
    """Try to get the first line of --version output."""
    try:
        proc = subprocess.run(
            [binary, "--version"],
            capture_output=True, text=True,
            timeout=5,
        )
        output = (proc.stdout or proc.stderr or "").strip()
        if output:
            return output.splitlines()[0]
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


class DoctorTool(BaseTool):
    name = "doctor_check"
    description = (
        "Check system readiness for pentesting. Verifies which security "
        "tools are installed and reports their versions."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "all", "recon", "exploitation", "web",
                        "network", "crypto", "forensics",
                    ],
                    "description": (
                        "Category of tools to check (default: all)."
                    ),
                },
            },
            "required": [],
        }


def handle_doctor_check(
    executor: "ToolExecutor",
    category: str = "all",
) -> dict[str, str]:
    if category == "all":
        categories = list(PENTEST_TOOLS.keys())
    elif category in PENTEST_TOOLS:
        categories = [category]
    else:
        return result("error", message=f"Unknown category: {category}")

    lines: list[str] = []
    total = 0
    available = 0

    for cat in categories:
        lines.append(f"\n=== {cat.upper()} ===")
        for entry in PENTEST_TOOLS[cat]:
            display_name, binary = _parse_tool_entry(entry)
            total += 1
            path = shutil.which(binary)
            if path:
                available += 1
                version = _get_version(binary)
                version_str = f" {version}" if version else ""
                lines.append(f"[✓] {display_name}{version_str}")
            else:
                lines.append(f"[✗] {display_name} — not installed")

    label = category if category != "all" else "all categories"
    summary = f"\n{available}/{total} tools available in {label}"
    lines.append(summary)

    output = truncate("\n".join(lines))
    logger.info("doctor check: %d/%d available", available, total)
    return result("success", output=output)
