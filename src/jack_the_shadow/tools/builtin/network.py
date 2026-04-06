"""
Jack The Shadow — Network Reconnaissance Tool

DNS lookup, reverse DNS, WHOIS, port scanning, SSL/TLS analysis,
ping, traceroute, and subnet scanning using only stdlib.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
import subprocess
from typing import TYPE_CHECKING, Any, ClassVar

from jack_the_shadow.i18n import t
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.network")

_DEFAULT_PORTS = "21,22,25,53,80,110,143,443,445,993,995,3306,3389,5432,8080,8443"
_MAX_PORTS = 100
_MAX_SUBNET = 254


class NetworkReconTool(BaseTool):
    name: ClassVar[str] = "network_recon"
    description: ClassVar[str] = (
        "Perform network reconnaissance: DNS lookup, reverse DNS, WHOIS, "
        "port scanning, SSL/TLS analysis, and subdomain enumeration. "
        "Returns structured results."
    )
    risk_aware: ClassVar[bool] = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "dns_lookup",
                        "reverse_dns",
                        "whois",
                        "port_scan",
                        "ssl_check",
                        "ping",
                        "traceroute",
                        "subnet_scan",
                    ],
                    "description": "The reconnaissance action to perform.",
                },
                "target": {
                    "type": "string",
                    "description": "Hostname, IP address, or domain to target.",
                },
                "ports": {
                    "type": "string",
                    "description": (
                        "Port range for port_scan (e.g. '80,443' or '1-1000'). "
                        f"Default: {_DEFAULT_PORTS}"
                    ),
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout per operation in seconds (default: 5).",
                },
            },
            "required": ["action", "target"],
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_ports(ports_str: str) -> list[int]:
    """Parse a comma-separated port list with optional ranges (e.g. '80,443,1-100')."""
    ports: list[int] = []
    for part in ports_str.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            lo_int, hi_int = int(lo), int(hi)
            ports.extend(range(lo_int, min(hi_int, lo_int + _MAX_PORTS) + 1))
        else:
            ports.append(int(part))
        if len(ports) >= _MAX_PORTS:
            break
    return sorted(set(ports[:_MAX_PORTS]))


def _service_name(port: int) -> str:
    """Best-effort service name for a port number."""
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"


def _run_cmd(cmd: list[str], timeout: int) -> str:
    """Run a subprocess command and return stdout+stderr."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = proc.stdout
        if proc.stderr:
            output += "\n" + proc.stderr
        return output.strip()
    except FileNotFoundError:
        return f"Error: '{cmd[0]}' is not installed on this system."
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s."


# ---------------------------------------------------------------------------
# Action implementations
# ---------------------------------------------------------------------------

def _dns_lookup(target: str, timeout: int) -> str:
    lines: list[str] = [f"DNS Lookup: {target}", "=" * 40]

    # A records
    try:
        socket.setdefaulttimeout(timeout)
        info = socket.getaddrinfo(target, None, socket.AF_INET)
        a_records = sorted(set(addr[4][0] for addr in info))
        lines.append(f"A Records:    {', '.join(a_records)}")
    except socket.gaierror:
        lines.append("A Records:    None found")

    # AAAA records
    try:
        info6 = socket.getaddrinfo(target, None, socket.AF_INET6)
        aaaa_records = sorted(set(addr[4][0] for addr in info6))
        lines.append(f"AAAA Records: {', '.join(aaaa_records)}")
    except socket.gaierror:
        lines.append("AAAA Records: None found")

    # MX / NS / TXT via dig (if available)
    for rtype in ("MX", "NS", "TXT"):
        out = _run_cmd(["dig", "+short", rtype, target], timeout)
        if out and not out.startswith("Error:"):
            lines.append(f"{rtype} Records:  {out}")

    return "\n".join(lines)


def _reverse_dns(target: str, timeout: int) -> str:
    try:
        socket.setdefaulttimeout(timeout)
        hostname, _, _ = socket.gethostbyaddr(target)
        return f"Reverse DNS: {target} → {hostname}"
    except (socket.herror, socket.gaierror, OSError) as exc:
        return f"No reverse DNS found for {target} ({exc})"


def _whois(target: str, timeout: int) -> str:
    out = _run_cmd(["whois", target], timeout + 10)
    if out.startswith("Error:"):
        return out
    return f"WHOIS: {target}\n{'=' * 40}\n{out}"


def _port_scan(target: str, ports_str: str, timeout: int) -> str:
    ports = _parse_ports(ports_str)
    lines: list[str] = [
        f"Port Scan: {target} ({len(ports)} ports)",
        "=" * 40,
    ]
    open_ports: list[str] = []
    closed_count = 0

    for port in ports:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            code = sock.connect_ex((target, port))
            if code == 0:
                svc = _service_name(port)
                open_ports.append(f"  {port:>5}/tcp  OPEN   {svc}")
            else:
                closed_count += 1
        except (OSError, socket.timeout):
            closed_count += 1
        finally:
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass

    if open_ports:
        lines.append("\nOpen ports:")
        lines.extend(open_ports)
    else:
        lines.append("\nNo open ports found.")
    lines.append(f"\nClosed/filtered: {closed_count}")
    return "\n".join(lines)


def _ssl_check(target: str, timeout: int) -> str:
    lines: list[str] = [f"SSL/TLS Check: {target}", "=" * 40]
    try:
        context = ssl.create_default_context()
        with socket.create_connection((target, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=target) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return "SSL connection succeeded but no certificate returned."

                # Subject
                subject_parts = []
                for rdn in cert.get("subject", ()):
                    for attr_name, attr_val in rdn:
                        subject_parts.append(f"{attr_name}={attr_val}")
                lines.append(f"Subject:     {', '.join(subject_parts)}")

                # Issuer
                issuer_parts = []
                for rdn in cert.get("issuer", ()):
                    for attr_name, attr_val in rdn:
                        issuer_parts.append(f"{attr_name}={attr_val}")
                lines.append(f"Issuer:      {', '.join(issuer_parts)}")

                lines.append(f"Valid From:  {cert.get('notBefore', 'N/A')}")
                lines.append(f"Valid Until: {cert.get('notAfter', 'N/A')}")
                lines.append(f"Serial:      {cert.get('serialNumber', 'N/A')}")

                # SANs
                sans = [v for t, v in cert.get("subjectAltName", ()) if t == "DNS"]
                if sans:
                    lines.append(f"SANs:        {', '.join(sans)}")

                lines.append(f"TLS Version: {ssock.version()}")
                cipher = ssock.cipher()
                if cipher:
                    lines.append(f"Cipher:      {cipher[0]} ({cipher[2]} bits)")

    except ssl.SSLCertVerificationError as exc:
        lines.append(f"Certificate verification FAILED: {exc}")
    except (ConnectionRefusedError, OSError) as exc:
        lines.append(f"Connection failed: {exc}")

    return "\n".join(lines)


def _ping(target: str, timeout: int) -> str:
    out = _run_cmd(["ping", "-c", "4", "-W", str(timeout), target], timeout + 10)
    return f"Ping: {target}\n{'=' * 40}\n{out}"


def _traceroute(target: str, timeout: int) -> str:
    out = _run_cmd(
        ["traceroute", "-m", "20", "-w", str(timeout), target],
        timeout * 20 + 10,
    )
    return f"Traceroute: {target}\n{'=' * 40}\n{out}"


def _subnet_scan(target: str, timeout: int) -> str:
    # Determine network from target
    try:
        if "/" in target:
            network = ipaddress.ip_network(target, strict=False)
        else:
            ip = ipaddress.ip_address(target)
            network = ipaddress.ip_network(f"{ip}/24", strict=False)
    except ValueError as exc:
        return f"Invalid target for subnet scan: {exc}"

    hosts = list(network.hosts())
    if len(hosts) > _MAX_SUBNET:
        hosts = hosts[:_MAX_SUBNET]

    lines: list[str] = [
        f"Subnet Scan: {network} ({len(hosts)} hosts)",
        "=" * 40,
    ]
    alive: list[str] = []

    for host in hosts:
        host_str = str(host)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(max(timeout / 2, 0.5))
            code = sock.connect_ex((host_str, 80))
            sock.close()
            if code == 0:
                alive.append(f"  {host_str}  (port 80 open)")
                continue
        except OSError:
            pass

        # Fallback: try ICMP via ping (single packet, short timeout)
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host_str],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if proc.returncode == 0:
                alive.append(f"  {host_str}  (ping reply)")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    if alive:
        lines.append(f"\nAlive hosts ({len(alive)}):")
        lines.extend(alive)
    else:
        lines.append("\nNo responsive hosts found.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handle_network_recon(
    executor: "ToolExecutor",
    action: str,
    target: str,
    ports: str = _DEFAULT_PORTS,
    timeout: int = 5,
    risk_level: str = "Medium",
) -> dict[str, str]:
    detail = f"{action} → {target}"
    # Only ask approval for active scanning (port_scan, subnet_scan)
    if not executor.is_safe_call("network_recon", {"action": action}):
        if not executor.request_approval("network_recon", detail, risk_level):
            return result("error", message=t("tool.denied"))

    logger.info("network_recon: action=%s target=%s", action, target)

    try:
        if action == "dns_lookup":
            output = _dns_lookup(target, timeout)
        elif action == "reverse_dns":
            output = _reverse_dns(target, timeout)
        elif action == "whois":
            output = _whois(target, timeout)
        elif action == "port_scan":
            output = _port_scan(target, ports, timeout)
        elif action == "ssl_check":
            output = _ssl_check(target, timeout)
        elif action == "ping":
            output = _ping(target, timeout)
        elif action == "traceroute":
            output = _traceroute(target, timeout)
        elif action == "subnet_scan":
            output = _subnet_scan(target, timeout)
        else:
            return result("error", message=f"Unknown action: {action}")
    except Exception as exc:
        logger.error("network_recon failed: %s", exc)
        return result("error", message=f"Network recon failed: {exc}")

    return result("success", output=truncate(output))
