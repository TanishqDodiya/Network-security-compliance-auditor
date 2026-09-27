"""Cisco parser: extract security-relevant settings from Cisco-style configs.

Beginner idea: a parser reads text lines and fills a structured form.
Example: line `no service telnet` -> form field `telnet_enabled = False`.
It also remembers WHICH line proved each answer (evidence) for the audit report.
Lines it doesn't understand go to `unknown_lines` for the future AI phase.
It never changes the device. Read-only.
"""

import re
from dataclasses import dataclass, field

WEAK_PASSWORDS = {"admin", "admin123", "cisco", "password", "guest", "test", "1234"}


@dataclass
class CiscoParseResult:
    hostname: str | None = None
    telnet_enabled: bool | None = None
    ssh_enabled: bool | None = None
    http_enabled: bool | None = None
    https_enabled: bool | None = None
    logging_enabled: bool | None = None
    security_logging: bool | None = None
    ntp_configured: bool | None = None
    ntp_servers: list[str] = field(default_factory=list)
    snmp_enabled: bool | None = None
    snmp_insecure: bool | None = None
    password_encryption: bool | None = None
    strong_auth: bool | None = None
    weak_creds_found: bool = False
    unnecessary_services: bool | None = None  # True = bad extra services found
    mgmt_restricted: bool | None = None
    evidence: dict[str, str] = field(default_factory=dict)
    unknown_lines: list[str] = field(default_factory=list)


def _remember(result: CiscoParseResult, key: str, line: str) -> None:
    """Keep the first line that proved a field (don't overwrite with later lines)."""
    if key not in result.evidence:
        result.evidence[key] = line.strip()[:200]


def parse_cisco(raw_text: str) -> CiscoParseResult:
    """Parse Cisco config text into structured security data."""
    r = CiscoParseResult()
    # Track vty transport inputs to infer telnet/ssh when `service telnet` is absent.
    vty_inputs: list[str] = []
    in_vty = False
    has_access_list = False
    has_access_class_in = False
    finger_on = pad_on = source_route_on = False
    finger_off = pad_off = source_route_off = False
    seen_secret = seen_plain_password = False

    for raw_line in (raw_text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!") or line.startswith("#") or line == "end":
            continue
        low = line.lower()
        matched = False

        def hit(key: str = "") -> None:
            nonlocal matched
            matched = True
            if key:
                _remember(r, key, line)

        # Hostname: `hostname Router-01`
        m = re.match(r"^hostname\s+(\S+)", line, re.IGNORECASE)
        if m:
            r.hostname = m.group(1)
            hit("hostname")
            continue

        # Telnet service.
        if re.match(r"^no\s+service\s+telnet", line, re.IGNORECASE):
            r.telnet_enabled = False
            hit("telnet_enabled")
            continue
        if re.match(r"^service\s+telnet", line, re.IGNORECASE):
            r.telnet_enabled = True
            hit("telnet_enabled")
            continue

        # SSH.
        if re.match(r"^ip\s+ssh\s+version\s+2", line, re.IGNORECASE):
            r.ssh_enabled = True
            hit("ssh_enabled")
            continue
        if re.match(r"^no\s+ip\s+ssh", line, re.IGNORECASE):
            r.ssh_enabled = False
            hit("ssh_enabled")
            continue

        # VTY block tracking.
        if re.match(r"^line\s+(vty|con|aux)", line, re.IGNORECASE):
            in_vty = "vty" in low
            hit()
            continue
        m = re.match(r"^transport\s+input\s+(.+)", line, re.IGNORECASE)
        if m and in_vty:
            vty_inputs.append(m.group(1).lower())
            hit("vty_transport")
            continue
        if re.match(r"^access-class\s+\S+\s+in", line, re.IGNORECASE):
            has_access_class_in = True
            hit("mgmt_restricted")
            continue
        if re.match(r"^no\s+access-class", line, re.IGNORECASE):
            has_access_class_in = False
            hit("mgmt_restricted")
            continue

        # ACLs.
        if re.match(r"^access-list\s+\d+", line, re.IGNORECASE):
            has_access_list = True
            hit("acl")
            continue
        if re.match(r"^no\s+access-list", line, re.IGNORECASE):
            hit("acl")
            continue

        # HTTP / HTTPS.
        if re.match(r"^no\s+ip\s+http\s+server", line, re.IGNORECASE):
            r.http_enabled = False
            hit("http_enabled")
            continue
        if re.match(r"^ip\s+http\s+server", line, re.IGNORECASE):
            r.http_enabled = True
            hit("http_enabled")
            continue
        if re.match(r"^no\s+ip\s+http\s+secure-server", line, re.IGNORECASE):
            r.https_enabled = False
            hit("https_enabled")
            continue
        if re.match(r"^ip\s+http\s+secure-server", line, re.IGNORECASE):
            r.https_enabled = True
            hit("https_enabled")
            continue

        # Logging.
        if re.match(r"^logging\s+(buffered|host|trap)", line, re.IGNORECASE):
            r.logging_enabled = True
            r.security_logging = True
            hit("logging_enabled")
            continue
        if re.match(r"^no\s+logging", line, re.IGNORECASE):
            r.logging_enabled = False
            r.security_logging = False
            hit("logging_enabled")
            continue

        # NTP.
        m = re.match(r"^ntp\s+server\s+(\S+)", line, re.IGNORECASE)
        if m:
            r.ntp_configured = True
            r.ntp_servers.append(m.group(1))
            hit("ntp_configured")
            continue
        if re.match(r"^no\s+ntp", line, re.IGNORECASE):
            r.ntp_configured = False
            r.ntp_servers = []
            hit("ntp_configured")
            continue
        if re.match(r"^ntp\s+authenticate", line, re.IGNORECASE):
            hit("ntp_auth")
            continue

        # SNMP.
        m = re.match(r"^snmp-server\s+community\s+(\S+)", line, re.IGNORECASE)
        if m:
            community = m.group(1).lower()
            r.snmp_enabled = True
            if community in {"public", "private"}:
                r.snmp_insecure = True
            elif r.snmp_insecure is None:
                r.snmp_insecure = False
            hit("snmp_insecure")
            continue
        if re.match(r"^no\s+snmp-server\s+community", line, re.IGNORECASE):
            hit("snmp_removed")
            continue
        if re.match(r"^snmp-server\s+(group|user|host)\s+", line, re.IGNORECASE):
            if r.snmp_enabled is None:
                r.snmp_enabled = True
            if r.snmp_insecure is None:
                r.snmp_insecure = False  # v3-only so far looks secure
            hit("snmp_v3")
            continue

        # Passwords / authentication.
        if re.match(r"^service\s+password-encryption", line, re.IGNORECASE):
            r.password_encryption = True
            hit("password_encryption")
            continue
        if re.match(r"^no\s+service\s+password-encryption", line, re.IGNORECASE):
            r.password_encryption = False
            hit("password_encryption")
            continue
        if re.match(r"^username\s+\S+.*\bsecret\b", line, re.IGNORECASE) or re.match(
            r"^enable\s+secret\b", line, re.IGNORECASE
        ):
            seen_secret = True
            hit("strong_auth")
            continue
        m = re.match(r"^username\s+(\S+).*?\bpassword\s+(\S+)", line, re.IGNORECASE)
        if m or re.match(r"^enable\s+password\b", line, re.IGNORECASE):
            seen_plain_password = True
            pwd = m.group(2) if m else line.split()[-1]
            if pwd.lower().strip('"\'') in WEAK_PASSWORDS:
                r.weak_creds_found = True
            hit("weak_creds")
            continue
        if re.match(r"^line\s+\S+.*|password\s+\S+", line, re.IGNORECASE) and "password" in low:
            # e.g. `password telnet123` under vty/con lines.
            hit("line_password")
            continue

        # Unnecessary / insecure services.
        if re.match(r"^service\s+finger", line, re.IGNORECASE):
            finger_on = True
            hit("unnecessary_services")
            continue
        if re.match(r"^no\s+service\s+finger", line, re.IGNORECASE):
            finger_off = True
            hit("unnecessary_services")
            continue
        if re.match(r"^service\s+pad", line, re.IGNORECASE):
            pad_on = True
            hit("unnecessary_services")
            continue
        if re.match(r"^no\s+service\s+pad", line, re.IGNORECASE):
            pad_off = True
            hit("unnecessary_services")
            continue
        if re.match(r"^ip\s+source-route", line, re.IGNORECASE):
            source_route_on = True
            hit("unnecessary_services")
            continue
        if re.match(r"^no\s+ip\s+source-route", line, re.IGNORECASE):
            source_route_off = True
            hit("unnecessary_services")
            continue

        # Interface / routing lines: known but not security-relevant for MVP.
        if re.match(
            r"^(interface\s|ip\s+address\s|no\s+shutdown|shutdown|ip\s+route\s|router\s|network\s)",
            line,
            re.IGNORECASE,
        ):
            hit()
            continue

        # Anything else that looks like a command -> unknown (future AI phase).
        if re.match(r"^[a-z][a-z0-9-]*(\s+\S+)+$", line, re.IGNORECASE):
            r.unknown_lines.append(line[:200])
        matched = True  # counted as seen, just unclassified

    # Post-processing: infer from vty transports if service lines were absent.
    transports = " ".join(vty_inputs)
    if r.telnet_enabled is None and transports:
        if "telnet" in transports or "all" in transports:
            r.telnet_enabled = True
            r.evidence.setdefault("telnet_enabled", f"vty transport: {transports[:120]}")
        elif "ssh" in transports:
            r.telnet_enabled = False
            r.evidence.setdefault("telnet_enabled", f"vty transport: {transports[:120]}")
    if r.ssh_enabled is None and transports:
        if "ssh" in transports or "all" in transports:
            r.ssh_enabled = True
            r.evidence.setdefault("ssh_enabled", f"vty transport: {transports[:120]}")
        elif "none" in transports:
            r.ssh_enabled = False

    # Unnecessary services summary.
    if finger_on or pad_on or source_route_on:
        r.unnecessary_services = True
    elif finger_off or pad_off or source_route_off:
        r.unnecessary_services = False

    # Strong auth summary: secret-based and no weak plain passwords.
    if seen_secret and not seen_plain_password and not r.weak_creds_found:
        r.strong_auth = True
    elif seen_plain_password or r.weak_creds_found:
        r.strong_auth = False

    # Management restriction: ACL + access-class on vty.
    if has_access_class_in and has_access_list:
        r.mgmt_restricted = True
    elif not has_access_class_in and not has_access_list:
        # No restriction evidence at all -> leave None unless vty exists.
        if vty_inputs:
            r.mgmt_restricted = False

    # NTP default: if never mentioned, stay None (unknown), not False.
    if r.ntp_configured is None and not r.ntp_servers:
        pass

    return r


class CiscoParser:
    """Thin class wrapper so later phases can use CiscoParser().parse(text)."""

    vendor = "cisco"

    def parse(self, raw_text: str) -> CiscoParseResult:
        return parse_cisco(raw_text)
