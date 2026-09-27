"""Dispatcher: vendor text -> vendor parser -> NormalizedConfig.

Adding a new vendor later means: write its parser, add one branch here.
Compliance code never changes.
"""

from app.normalization.model import NormalizedConfig
from app.parsers.cisco import CiscoParser
from app.parsers.juniper import JuniperParser
from app.parsers.paloalto import PaloAltoParser


def _evidence_aliases(evidence: dict[str, str]) -> dict[str, str]:
    """Map parser evidence keys to normalized dotted paths."""
    alias = {
        "telnet_enabled": "management.telnet_enabled",
        "ssh_enabled": "management.ssh_enabled",
        "http_enabled": "management.http_enabled",
        "https_enabled": "management.https_enabled",
        "mgmt_restricted": "management.mgmt_restricted",
        "unnecessary_services": "management.unnecessary_services",
        "logging_enabled": "logging.enabled",
        "security_logging": "logging.security_logging",
        "strong_auth": "authentication.strong_authentication",
        "weak_creds": "authentication.weak_creds_found",
        "password_encryption": "authentication.password_encryption",
        "snmp_insecure": "snmp.insecure",
        "snmp_v3": "snmp.enabled",
        "snmp_removed": "snmp.insecure",
        "ntp_configured": "ntp.configured",
    }
    return {alias.get(k, k): v for k, v in evidence.items()}


def normalize_parsed(vendor: str, parsed) -> NormalizedConfig:
    """Convert any parser's result object into the common model."""
    vendor = (vendor or "unknown").lower()
    return NormalizedConfig(
        device={"hostname": parsed.hostname, "vendor": vendor},
        management={
            "telnet_enabled": parsed.telnet_enabled,
            "ssh_enabled": parsed.ssh_enabled,
            "http_enabled": parsed.http_enabled,
            "https_enabled": parsed.https_enabled,
            "mgmt_restricted": parsed.mgmt_restricted,
            "unnecessary_services": parsed.unnecessary_services,
        },
        logging={"enabled": parsed.logging_enabled, "security_logging": parsed.security_logging},
        authentication={
            "strong_authentication": parsed.strong_auth,
            "weak_creds_found": bool(parsed.weak_creds_found),
            "password_encryption": parsed.password_encryption,
        },
        snmp={"enabled": parsed.snmp_enabled, "insecure": parsed.snmp_insecure},
        ntp={"configured": parsed.ntp_configured, "servers": list(parsed.ntp_servers)},
        evidence=_evidence_aliases(dict(parsed.evidence)),
        unknown_lines=list(parsed.unknown_lines),
    )


def normalize_text(vendor: str, raw_text: str) -> NormalizedConfig:
    """Parse raw text with the right vendor parser, then normalize."""
    vendor = (vendor or "unknown").lower()
    if vendor == "cisco":
        parsed = CiscoParser().parse(raw_text)
    elif vendor == "juniper":
        parsed = JuniperParser().parse(raw_text)
    elif vendor == "paloalto":
        parsed = PaloAltoParser().parse(raw_text)
    else:
        # Unknown vendor: honest empty model, keep lines for future AI review.
        lines = [ln.strip()[:200] for ln in (raw_text or "").splitlines() if ln.strip()]
        return NormalizedConfig(
            device={"hostname": None, "vendor": "unknown"},
            unknown_lines=lines[:100],
        )
    return normalize_parsed(vendor, parsed)
