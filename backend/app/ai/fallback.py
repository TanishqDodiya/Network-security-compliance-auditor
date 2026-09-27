"""Deterministic fallback: keyword-based guesses + template text. No network.

Used when no AI key is set OR the LLM call fails. Honest by design:
confidence reflects keyword hits, and callers must show
`ai_available: False` in the UI.
"""

import re

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Authentication": ["password", "passwd", "login", "user", "auth", "credential", "secret", "radius", "tacacs"],
    "Management Security": ["telnet", "ssh", "http", "https", "management", "service", "finger", "pad", "console", "vty", "admin", "admin-mode"],
    "Logging": ["log", "syslog", "audit", "trap", "buffered"],
    "Network Security": ["acl", "access-list", "firewall", "rulebase", "zone", "filter", "policy"],
    "System": ["ntp", "clock", "timezone", "hostname", "dns", "snmp"],
}

FIELD_HINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"telnet", re.IGNORECASE), "management.telnet_enabled"),
    (re.compile(r"\bssh\b", re.IGNORECASE), "management.ssh_enabled"),
    (re.compile(r"https", re.IGNORECASE), "management.https_enabled"),
    (re.compile(r"http", re.IGNORECASE), "management.http_enabled"),
    (re.compile(r"syslog|logging", re.IGNORECASE), "logging.enabled"),
    (re.compile(r"ntp", re.IGNORECASE), "ntp.configured"),
    (re.compile(r"snmp|community", re.IGNORECASE), "snmp.insecure"),
    (re.compile(r"password|credential|login", re.IGNORECASE), "authentication.weak_creds_found"),
]


def classify_unknown(text: str) -> dict:
    """Guess category + normalized field from keywords. Returns confidence 0.3-0.85."""
    low = (text or "").lower()
    scores = {
        cat: sum(1 for kw in kws if kw in low) for cat, kws in CATEGORY_KEYWORDS.items()
    }
    best = max(scores, key=lambda c: scores[c])
    hits = scores[best]
    if hits == 0:
        return {
            "suggested_category": "Other",
            "suggested_field": "",
            "confidence": 0.3,
            "meaning": "Unrecognized configuration line. Needs human review.",
        }
    field = ""
    for regex, hint in FIELD_HINTS:
        if regex.search(text or ""):
            field = hint
            break
    return {
        "suggested_category": best,
        "suggested_field": field,
        "confidence": min(0.5 + hits * 0.1, 0.85),
        "meaning": f"Possible {best.lower()} setting based on keywords in the line.",
    }


def explain_result(rule_code: str, title: str, status: str, evidence: str, remediation: str) -> str:
    """Simple-language explanation template (no LLM needed)."""
    if status == "PASS":
        return (
            f"{rule_code} {title}: passed. "
            f"Evidence: {evidence or 'required setting found'}. No action needed."
        )
    return (
        f"{rule_code} {title}: failed. "
        f"In simple terms: {evidence or 'the required secure setting was not found'}. "
        f"Fix: {remediation or 'apply the recommended secure setting'}."
    )


def summarize_results(total: int, passed: int, failed: int, critical: int, high: int) -> str:
    """One-paragraph audit summary template."""
    if total == 0:
        return "No rules were evaluated."
    pct = round(passed / total * 100, 1)
    headline = f"{passed} of {total} checks passed ({pct}% compliant)."
    if failed == 0:
        return headline + " No failed rules. Configuration looks good at this level."
    urgent = ""
    if critical:
        urgent += f" {critical} critical issue(s) need immediate attention."
    if high:
        urgent += f" {high} high-severity issue(s) should be fixed soon."
    return headline + f" {failed} check(s) failed." + urgent
