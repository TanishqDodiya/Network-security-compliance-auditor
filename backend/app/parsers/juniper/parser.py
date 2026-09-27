"""Juniper parser: extract security settings from `set`/`delete` style configs.

Same output shape as the Cisco parser so Phase 9 (normalization) can treat
all vendors identically. Evidence + unknown_lines included. Read-only.
"""

import re
from dataclasses import dataclass, field

WEAK_PASSWORDS = {"admin", "admin123", "cisco", "password", "guest", "test", "1234"}


@dataclass
class JuniperParseResult:
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
    password_encryption: bool | None = None  # Juniper stores encrypted-password; True if seen
    strong_auth: bool | None = None
    weak_creds_found: bool = False
    unnecessary_services: bool | None = None
    mgmt_restricted: bool | None = None
    evidence: dict[str, str] = field(default_factory=dict)
    unknown_lines: list[str] = field(default_factory=list)


def _remember(result: JuniperParseResult, key: str, line: str) -> None:
    if key not in result.evidence:
        result.evidence[key] = line.strip()[:200]


def parse_juniper(raw_text: str) -> JuniperParseResult:
    """Parse Juniper set-style config text into structured security data."""
    r = JuniperParseResult()
    seen_encrypted = seen_plain = False
    finger_on = False
    mgmt_all_open = False
    mgmt_limited = False

    for raw_line in (raw_text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        low = line.lower()

        def hit(key: str = "") -> None:
            if key:
                _remember(r, key, line)

        # Hostname: `set system host-name X`
        m = re.match(r"^set\s+system\s+host-name\s+(\S+)", line, re.IGNORECASE)
        if m:
            r.hostname = m.group(1)
            hit("hostname")
            continue

        # Telnet: `set system services telnet` / `delete ... telnet`
        if re.match(r"^(set|activate)\s+system\s+services\s+telnet\b", line, re.IGNORECASE):
            r.telnet_enabled = True
            hit("telnet_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+system\s+services\s+telnet\b", line, re.IGNORECASE):
            r.telnet_enabled = False
            hit("telnet_enabled")
            continue

        # SSH.
        if re.match(r"^(set|activate)\s+system\s+services\s+ssh\b", line, re.IGNORECASE):
            r.ssh_enabled = True
            hit("ssh_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+system\s+services\s+ssh\b", line, re.IGNORECASE):
            r.ssh_enabled = False
            hit("ssh_enabled")
            continue

        # Web management http/https. Check https FIRST (it contains "http").
        if re.match(r"^(set|activate)\s+system\s+services\s+web-management\s+https\b", line, re.IGNORECASE):
            r.https_enabled = True
            hit("https_enabled")
            continue
        if re.match(r"^(set|activate)\s+system\s+services\s+web-management\s+http\b", line, re.IGNORECASE):
            r.http_enabled = True
            hit("http_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+system\s+services\s+web-management\s+https\b", line, re.IGNORECASE):
            r.https_enabled = False
            hit("https_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+system\s+services\s+web-management\s+http\b", line, re.IGNORECASE):
            r.http_enabled = False
            hit("http_enabled")
            continue

        # Syslog / logging.
        if re.match(r"^(set|activate)\s+system\s+syslog\b", line, re.IGNORECASE):
            r.logging_enabled = True
            r.security_logging = True
            hit("logging_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+system\s+syslog\b", line, re.IGNORECASE):
            r.logging_enabled = False
            r.security_logging = False
            hit("logging_enabled")
            continue

        # NTP.
        m = re.match(r"^set\s+system\s+ntp\s+server\s+(\S+)", line, re.IGNORECASE)
        if m:
            r.ntp_configured = True
            r.ntp_servers.append(m.group(1))
            hit("ntp_configured")
            continue
        if re.match(r"^(delete|deactivate)\s+system\s+ntp\b", line, re.IGNORECASE):
            r.ntp_configured = False
            r.ntp_servers = []
            hit("ntp_configured")
            continue

        # SNMP communities (insecure) vs v3 (secure).
        m = re.match(r"^set\s+snmp\s+community\s+(\S+)", line, re.IGNORECASE)
        if m:
            community = m.group(1).lower().strip('"\'')
            r.snmp_enabled = True
            if community in {"public", "private"}:
                r.snmp_insecure = True
            elif r.snmp_insecure is None:
                r.snmp_insecure = False
            hit("snmp_insecure")
            continue
        if re.match(r"^(delete|deactivate)\s+snmp\s+community", line, re.IGNORECASE):
            hit("snmp_removed")
            continue
        if re.match(r"^set\s+snmp\s+v3\b", line, re.IGNORECASE):
            if r.snmp_enabled is None:
                r.snmp_enabled = True
            if r.snmp_insecure is None:
                r.snmp_insecure = False
            hit("snmp_v3")
            continue

        # Authentication: encrypted vs plain-text passwords.
        if re.search(r"encrypted-password", line, re.IGNORECASE):
            seen_encrypted = True
            r.password_encryption = True
            hit("strong_auth")
            continue
        m = re.search(r"plain-text-password\s+(\S+)", line, re.IGNORECASE)
        if m:
            seen_plain = True
            pwd = m.group(1).lower().strip('"\'')
            if pwd in WEAK_PASSWORDS:
                r.weak_creds_found = True
            hit("weak_creds")
            continue

        # Finger (unnecessary service).
        if re.match(r"^(set|activate)\s+system\s+services\s+finger\b", line, re.IGNORECASE):
            finger_on = True
            hit("unnecessary_services")
            continue
        if re.match(r"^(delete|deactivate)\s+system\s+services\s+finger\b", line, re.IGNORECASE):
            hit("unnecessary_services")
            continue

        # Management restriction via security-zone host-inbound-traffic.
        if re.search(r"host-inbound-traffic\s+system-services\s+all\b", line, re.IGNORECASE):
            mgmt_all_open = True
            hit("mgmt_restricted")
            continue
        if re.search(r"host-inbound-traffic\s+system-services\s+(ssh|https)", line, re.IGNORECASE):
            mgmt_limited = True
            hit("mgmt_restricted")
            continue

        # Known but non-security Juniper lines for MVP (don't mark unknown).
        if re.match(
            r"^(set\s+(interfaces|protocols|policy-options|routing-options|firewall|system\s+(login\s+(idle-timeout|class)|password\s)|services\s)|delete\s+(interfaces|protocols)\s)",
            line,
            re.IGNORECASE,
        ):
            continue

        # Anything else set-style -> unknown (future AI phase).
        if re.match(r"^(set|delete|activate|deactivate)\s+\S+", line, re.IGNORECASE):
            r.unknown_lines.append(line[:200])
            continue
        if re.match(r"^[a-z][a-z0-9-]*(\s+\S+)+$", line, re.IGNORECASE):
            r.unknown_lines.append(line[:200])

    if finger_on:
        r.unnecessary_services = True
    elif "unnecessary_services" in r.evidence and not finger_on:
        r.unnecessary_services = False

    if seen_encrypted and not seen_plain and not r.weak_creds_found:
        r.strong_auth = True
    elif seen_plain or r.weak_creds_found:
        r.strong_auth = False

    if mgmt_all_open:
        r.mgmt_restricted = False
    elif mgmt_limited:
        r.mgmt_restricted = True

    return r


class JuniperParser:
    """Thin class wrapper so later phases can use JuniperParser().parse(text)."""

    vendor = "juniper"

    def parse(self, raw_text: str) -> JuniperParseResult:
        return parse_juniper(raw_text)
