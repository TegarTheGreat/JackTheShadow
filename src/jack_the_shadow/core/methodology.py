"""
Jack The Shadow — Methodology Engine

Provides predefined attack chains and smart follow-up suggestions.
Instead of relying on the AI to invent tool chains from scratch,
this module provides concrete step-by-step playbooks that the
orchestrator can inject as context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.methodology")


# ── Phase Definitions ────────────────────────────────────────────────

PHASES = ("recon", "enum", "vuln", "exploit", "post_exploit", "report")

# Tools relevant to each phase (others are always available)
PHASE_TOOLS: dict[str, frozenset[str]] = {
    "recon": frozenset({
        "network_recon", "web_search", "web_fetch", "cve_lookup",
        "shodan_recon", "doctor_check", "http_request",
    }),
    "enum": frozenset({
        "http_request", "web_fetch", "grep_search", "glob_find",
        "list_directory", "exploit_search", "network_recon",
    }),
    "vuln": frozenset({
        "http_request", "web_fetch", "cve_lookup", "exploit_search",
        "payload_generate", "encode_decode", "web_search",
    }),
    "exploit": frozenset({
        "payload_generate", "python_repl", "encode_decode",
        "http_request", "exploit_search", "hash_analyze",
    }),
    "post_exploit": frozenset({
        "file_read", "file_write", "grep_search", "glob_find",
        "list_directory", "hash_analyze", "python_repl",
    }),
    "report": frozenset({
        "report_generate", "file_write", "git_command",
    }),
}

# Core tools always sent regardless of phase
CORE_TOOLS: frozenset[str] = frozenset({
    "bash_execute", "file_read", "file_write", "file_edit",
    "memory_read", "memory_write", "todo_read", "todo_write",
    "batch_execute", "ask_user", "web_search", "web_fetch",
    "python_repl", "mcp_call",
})


def get_phase_tools(phase: str) -> frozenset[str]:
    """Get tool names relevant for the given phase + core tools."""
    phase_specific = PHASE_TOOLS.get(phase, frozenset())
    return CORE_TOOLS | phase_specific


# ── Auto-Recon Playbook ──────────────────────────────────────────────

@dataclass
class ReconStep:
    """A single step in an automated recon chain."""
    tool: str
    args: dict[str, Any]
    description: str


def build_auto_recon_chain(target: str) -> list[ReconStep]:
    """Build the initial recon batch for a domain/IP target."""
    is_ip = _looks_like_ip(target)
    domain = target.strip().lower()

    steps: list[ReconStep] = []

    if not is_ip:
        steps.extend([
            ReconStep("network_recon", {
                "action": "dns_lookup", "target": domain, "risk_level": "Low",
            }, f"DNS lookup {domain}"),
            ReconStep("network_recon", {
                "action": "whois", "target": domain, "risk_level": "Low",
            }, f"WHOIS {domain}"),
            ReconStep("web_fetch", {
                "url": f"https://{domain}", "max_length": 5000,
            }, f"Fetch homepage https://{domain}"),
            ReconStep("network_recon", {
                "action": "ssl_info", "target": domain, "risk_level": "Low",
            }, f"SSL/TLS info {domain}"),
        ])
    else:
        steps.extend([
            ReconStep("network_recon", {
                "action": "reverse_dns", "target": domain, "risk_level": "Low",
            }, f"Reverse DNS {domain}"),
        ])

    # Common for both domain and IP
    steps.extend([
        ReconStep("network_recon", {
            "action": "port_scan", "target": domain,
            "ports": "21,22,25,53,80,110,143,443,445,993,995,3306,3389,5432,5900,8080,8443,8888,9090",
            "risk_level": "Low",
        }, f"Port scan {domain}"),
        ReconStep("web_search", {
            "query": f'site:{domain} OR "{domain}" vulnerability OR CVE OR exploit',
            "max_results": 5,
        }, f"Web search for known vulns on {domain}"),
    ])

    if not is_ip:
        steps.append(ReconStep("web_search", {
            "query": f'site:{domain} -www inurl:api OR inurl:admin OR inurl:login OR inurl:dev',
            "max_results": 5,
        }, f"Search interesting endpoints for {domain}"))

    return steps


def recon_chain_to_batch_args(steps: list[ReconStep]) -> dict[str, Any]:
    """Convert recon steps to batch_execute arguments."""
    return {
        "calls": [
            {"tool_name": s.tool, "arguments": s.args}
            for s in steps
        ],
        "risk_level": "Low",
    }


# ── Result Analysis ──────────────────────────────────────────────────

def analyze_results(tool_name: str, args: dict[str, Any],
                    result_data: dict[str, Any]) -> list[str]:
    """Analyze tool output and suggest follow-up actions.

    Returns a list of actionable suggestions for the AI.
    """
    suggestions: list[str] = []
    output = str(result_data.get("output", "") or result_data.get("message", ""))
    output_lower = output.lower()

    if tool_name == "network_recon":
        action = args.get("action", "")
        suggestions.extend(_analyze_network_result(action, output_lower, args))

    elif tool_name == "web_fetch":
        suggestions.extend(_analyze_web_result(output_lower, args))

    elif tool_name == "web_search":
        suggestions.extend(_analyze_search_result(output_lower, args))

    elif tool_name == "http_request":
        suggestions.extend(_analyze_http_result(output_lower, args))

    elif tool_name == "bash_execute":
        suggestions.extend(_analyze_bash_result(output_lower, args))

    elif tool_name == "batch_execute":
        suggestions.extend(_analyze_batch_result(output_lower, args))

    return suggestions


def _analyze_network_result(action: str, output: str,
                            args: dict[str, Any]) -> list[str]:
    s: list[str] = []
    target = args.get("target", "")

    if action == "port_scan":
        if "open" in output:
            if any(p in output for p in ["80/open", "443/open", "8080/open", "8443/open"]):
                s.append(
                    f"Web server detected → web_fetch the homepage, "
                    f"check response headers with http_request (look for Server, "
                    f"X-Powered-By, cookies), search for hidden dirs with bash "
                    f"(dirb/gobuster/feroxbuster if installed)"
                )
            if "22/open" in output:
                s.append(
                    f"SSH open → grab banner with bash_execute('nc -w3 {target} 22'), "
                    f"check for CVEs on the SSH version"
                )
            if any(p in output for p in ["3306/open", "5432/open"]):
                s.append(
                    "Database port open → check if authentication required, "
                    "try default credentials, search for version-specific CVEs"
                )
            if "21/open" in output:
                s.append(
                    f"FTP open → check anonymous login with bash_execute("
                    f"'curl -s ftp://{target}/'), grab banner"
                )
            if "445/open" in output:
                s.append(
                    "SMB open → enumerate shares with smbclient, check for EternalBlue"
                )
        if "open" not in output:
            s.append(
                "No common ports open → try expanded scan (top 1000), "
                "or check if target uses CDN/WAF that blocks scans"
            )

    elif action == "dns_lookup":
        if "cloudflare" in output or "cloudfront" in output:
            s.append(
                "CDN/WAF detected → try to find origin IP via historical DNS, "
                "check SecurityTrails, try direct IP scan"
            )
        if "mx records" in output:
            s.append(
                "MX records found → check for email misconfig, SPF/DKIM/DMARC records"
            )

    elif action == "whois":
        if "registrar" in output:
            s.append(
                "WHOIS data → note registrar, creation date, nameservers. "
                "Search for other domains on same registrant email"
            )

    elif action == "ssl_info":
        if "expired" in output or "self-signed" in output:
            s.append("SSL issue found → potential for MITM, report as finding")
        if "subject" in output:
            s.append(
                "Check SSL cert SANs for additional hostnames/subdomains"
            )

    return s


def _analyze_web_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []
    url = args.get("url", "")

    if "wordpress" in output:
        s.append(
            "WordPress detected → run wpscan (bash), check /wp-json/wp/v2/users, "
            "/xmlrpc.php, /wp-admin/, search for plugin vulns"
        )
    if "joomla" in output:
        s.append("Joomla detected → check /administrator/, search for component vulns")
    if "drupal" in output:
        s.append("Drupal detected → check /CHANGELOG.txt for version, search Drupalgeddon CVEs")
    if "laravel" in output:
        s.append(
            "Laravel detected → check /.env, /telescope, debug mode, "
            "search for CVE-2021-3129 (ignition RCE)"
        )
    if "django" in output:
        s.append("Django detected → check /admin/, debug mode, REST framework endpoints")
    if "next" in output or "react" in output or "vue" in output:
        s.append(
            "JS framework → check /api/, /_next/, source maps, "
            "look for exposed API keys in JS bundles"
        )
    if "api" in output or "swagger" in output or "openapi" in output:
        s.append(
            "API detected → enumerate endpoints, check for auth bypass, "
            "IDOR, mass assignment, rate limiting"
        )
    if "login" in output or "signin" in output:
        s.append(
            "Login form found → check for default creds, brute force potential, "
            "SQL injection on login, password reset flow"
        )
    if "token" in output or "jwt" in output or "bearer" in output:
        s.append(
            "Token/JWT reference → check for JWT vulnerabilities (none algo, "
            "weak secret), token leakage in responses"
        )
    if "upload" in output:
        s.append(
            "File upload functionality → test for unrestricted upload, "
            "extension bypass, webshell upload"
        )
    if "server:" in output or "x-powered-by:" in output:
        s.append(
            "Server header exposed → note the version, search for version-specific CVEs"
        )

    return s


def _analyze_search_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []

    if "cve-" in output:
        s.append(
            "CVE references found → use cve_lookup for details, "
            "then exploit_search for available exploits"
        )
    if "exploit" in output or "poc" in output:
        s.append(
            "Exploit/PoC references found → use web_fetch to read the full article, "
            "try to reproduce"
        )
    if "github" in output and ("vuln" in output or "exploit" in output):
        s.append(
            "GitHub exploit repo found → web_fetch the README, "
            "evaluate if applicable to target"
        )

    return s


def _analyze_http_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []

    if "401" in output or "403" in output:
        s.append(
            "Auth required or forbidden → try bypass techniques: "
            "path traversal, HTTP verb tampering, header injection "
            "(X-Forwarded-For, X-Original-URL)"
        )
    if "500" in output or "error" in output:
        s.append(
            "Server error → potential info disclosure, try fuzzing parameters, "
            "check if error reveals stack trace or paths"
        )
    if "redirect" in output or "302" in output or "301" in output:
        s.append("Redirect → follow the chain, check for open redirect vulnerability")
    if "set-cookie" in output:
        s.append(
            "Cookies set → check for missing HttpOnly/Secure/SameSite flags, "
            "analyze session token entropy"
        )

    return s


def _analyze_bash_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []
    cmd = str(args.get("command", ""))

    if "nmap" in cmd and "open" in output:
        s.append("Services found → enumerate each open service in detail")
    if "gobuster" in cmd or "dirb" in cmd or "feroxbuster" in cmd:
        if "200" in output or "301" in output:
            s.append("Directories found → web_fetch interesting paths, check for sensitive files")
    if "password" in output or "credential" in output:
        s.append("Possible credentials found → validate and document in memory_write")
    if "permission denied" in output or "access denied" in output:
        s.append("Access denied → try privilege escalation techniques")

    return s


def _analyze_batch_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []

    # Aggregate analysis from individual results
    if "open" in output:
        s.append(
            "Recon complete → save all findings with memory_write, "
            "create attack plan with todo_write, move to enumeration phase"
        )
    if "cloudflare" in output or "waf" in output:
        s.append(
            "WAF/CDN detected → adjust techniques: try origin IP discovery, "
            "use targeted payloads that bypass WAF rules"
        )

    return s


def format_suggestions(suggestions: list[str], lang: str = "en") -> str:
    """Format suggestions into a concise context injection string."""
    if not suggestions:
        return ""

    header = (
        "[INTEL] Based on results, suggested next moves:"
        if lang != "id" else
        "[INTEL] Berdasarkan hasil, langkah selanjutnya:"
    )

    lines = [f"• {s}" for s in suggestions[:5]]  # max 5 suggestions
    return f"\n{header}\n" + "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────

def _looks_like_ip(target: str) -> bool:
    try:
        import ipaddress as ipa
        ipa.ip_address(target.strip())
        return True
    except ValueError:
        return False
