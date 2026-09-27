"""Palo Alto parser: extract security settings from `set deviceconfig/...` style.

Same output shape as Cisco/Juniper parsers so Phase 9 normalization stays
vendor-independent. Evidence + unknown_lines included. Read-only.
"""

import re
from dataclasses import dataclass, field

WEAK_PASSWORDS = {"admin", "admin123", "cisco", "password", "guest", "test", "1234"}


@dataclass
class PaloAltoParseResult:
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
    unnecessary_services: bool | None = None
    mgmt_restricted: bool | None = None
    evidence: dict[str, str] = field(default_factory=dict)
    unknown_lines: list[str] = field(default_factory=list)


def _remember(result: PaloAltoParseResult, key: str, line: str) -> None:
    if key not in result.evidence:
        result.evidence[key] = line.strip()[:200]


def parse_paloalto(raw_text: str) -> PaloAltoParseResult:
    """Parse Palo Alto set-style config text into structured security data."""
    r = PaloAltoParseResult()
    seen_hash = seen_plain = False
    complexity_on = complexity_off = False
    allow_all_open = False
    allow_limited = deny_present = False

    for raw_line in (raw_text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue

        def hit(key: str = "") -> None:
            if key:
                _remember(r, key, line)

        # Hostname.
        m = re.match(r"^set\s+deviceconfig\s+system\s+hostname\s+(\S+)", line, re.IGNORECASE)
        if m:
            r.hostname = m.group(1)
            hit("hostname")
            continue

        # NTP: address appears as `ntp-server-address <ip>`.
        m = re.search(r"ntp-server-address\s+(\S+)", line, re.IGNORECASE)
        if m and line.lower().startswith("set"):
            r.ntp_configured = True
            r.ntp_servers.append(m.group(1))
            hit("ntp_configured")
            continue
        if re.match(r"^(delete|deactivate)\s+deviceconfig\s+system\s+ntp-servers\b", line, re.IGNORECASE):
            r.ntp_configured = False
            r.ntp_servers = []
            hit("ntp_configured")
            continue

        # Telnet: `set deviceconfig system telnet enabled yes/no`, delete = disabled.
        m = re.match(r"^set\s+deviceconfig\s+system\s+telnet\s+enabled\s+(yes|no)", line, re.IGNORECASE)
        if m:
            r.telnet_enabled = m.group(1).lower() == "yes"
            hit("telnet_enabled")
            continue
        if re.match(r"^set\s+network\s+telnet\s+enabled\s+yes", line, re.IGNORECASE):
            r.telnet_enabled = True
            hit("telnet_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+deviceconfig\s+system\s+telnet\b", line, re.IGNORECASE):
            r.telnet_enabled = False
            hit("telnet_enabled")
            continue

        # SSH: `set deviceconfig system ssh enabled yes/no` or bare `... ssh ...`.
        m = re.match(r"^set\s+deviceconfig\s+system\s+ssh\b(.*)", line, re.IGNORECASE)
        if m:
            rest = m.group(1).lower()
            r.ssh_enabled = False if "no" in rest.split() or "disabled" in rest else True
            if "enabled no" in rest:
                r.ssh_enabled = False
            hit("ssh_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+deviceconfig\s+system\s+ssh\b", line, re.IGNORECASE):
            r.ssh_enabled = False
            hit("ssh_enabled")
            continue

        # HTTP / HTTPS web-server flags.
        m = re.match(r"^set\s+deviceconfig\s+system\s+web-server\s+http-enabled\s+(yes|no)", line, re.IGNORECASE)
        if m:
            r.http_enabled = m.group(1).lower() == "yes"
            hit("http_enabled")
            continue
        m = re.match(r"^set\s+deviceconfig\s+system\s+web-server\s+https-enabled\s+(yes|no)", line, re.IGNORECASE)
        if m:
            r.https_enabled = m.group(1).lower() == "yes"
            hit("https_enabled")
            continue

        # Logging.
        if re.match(r"^set\s+deviceconfig\s+system\s+log-settings\b", line, re.IGNORECASE):
            r.logging_enabled = True
            r.security_logging = True
            hit("logging_enabled")
            continue
        if re.match(r"^(delete|deactivate)\s+deviceconfig\s+system\s+log-settings\b", line, re.IGNORECASE):
            r.logging_enabled = False
            r.security_logging = False
            hit("logging_enabled")
            continue

        # SNMP.
        m = re.match(r"^set\s+deviceconfig\s+system\s+snmp-setting\s+community\s+(\S+)", line, re.IGNORECASE)
        if m:
            community = m.group(1).lower().strip('"\'')
            r.snmp_enabled = True
            if community in {"public", "private"}:
                r.snmp_insecure = True
            elif r.snmp_insecure is None:
                r.snmp_insecure = False
            hit("snmp_insecure")
            continue
        if re.match(r"^set\s+deviceconfig\s+system\s+snmp-setting\s+v3\b", line, re.IGNORECASE):
            if r.snmp_enabled is None:
                r.snmp_enabled = True
            if r.snmp_insecure is None:
                r.snmp_insecure = False
            hit("snmp_v3")
            continue
        if re.match(r"^(delete|deactivate)\s+deviceconfig\s+system\s+snmp-setting\s+community\b", line, re.IGNORECASE):
            hit("snmp_removed")
            continue

        # Admin auth: password-hash (strong) vs plain password (weak).
        if re.match(r"^set\s+shared\s+admin\s+\S+\s+password-hash\b", line, re.IGNORECASE):
            seen_hash = True
            r.password_encryption = True
            hit("strong_auth")
            continue
        m = re.match(r"^set\s+shared\s+admin\s+\S+\s+password\s+(\S+)", line, re.IGNORECASE)
        if m:
            seen_plain = True
            if m.group(1).lower().strip('"\'') in WEAK_PASSWORDS:
                r.weak_creds_found = True
            hit("weak_creds")
            continue

        # Password complexity.
        m = re.match(r"^set\s+deviceconfig\s+system\s+password-complexity\s+enabled\s+(yes|no)", line, re.IGNORECASE)
        if m:
            if m.group(1).lower() == "yes":
                complexity_on = True
            else:
                complexity_off = True
            hit("password_complexity")
            continue

        # Rulebase: allow-all open vs limited mgmt + deny.
        if re.match(r"^set\s+rulebase\s+security\s+rules\s+\S+", line, re.IGNORECASE):
            low = line.lower()
            if "allow-all" in low and "source any" in low:
                allow_all_open = True
            if "allow-mgmt-only" in low or ("source 10." in low and "allow" in low):
                allow_limited = True
            if "action deny" in low:
                deny_present = True
            hit("rulebase")
            continue

        # Known non-security lines (don't mark unknown).
        if re.match(
            r"^(set\s+(deviceconfig\s+(system\s+(dns-setting|setting\s)|setting\s)|network\s+profiles\s|deviceconfig\s+setting\s)|delete\s+deviceconfig\s+system\s+telnet\s*$)",
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

    # Summaries.
    if seen_hash and not seen_plain and not r.weak_creds_found:
        r.strong_auth = True
    elif seen_plain or r.weak_creds_found:
        r.strong_auth = False
    if complexity_on and not complexity_off:
        if r.strong_auth is None:
            r.strong_auth = True
    elif complexity_off and not complexity_on and r.strong_auth is None:
        r.strong_auth = False

    if r.telnet_enabled or r.http_enabled:
        r.unnecessary_services = True
    elif r.telnet_enabled is False and r.http_enabled is False:
        r.unnecessary_services = False

    if allow_all_open:
        r.mgmt_restricted = False
    elif allow_limited and deny_present:
        r.mgmt_restricted = True

    return r


class PaloAltoParser:
    """Thin class wrapper so later phases can use PaloAltoParser().parse(text)."""

    vendor = "paloalto"

    def parse(self, raw_text: str) -> PaloAltoParseResult:
        return parse_paloalto(raw_text)
