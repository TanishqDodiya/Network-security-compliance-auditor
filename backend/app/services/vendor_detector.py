"""Vendor detection: guess cisco / juniper / paloalto / unknown from config text.

Beginner idea: each vendor has a distinctive writing style.
- Cisco: lines like `hostname R1`, `interface Gi0/0`, `access-list 10 ...`, `line vty 0 4`
- Juniper: almost every line starts with `set system`, `set interfaces`, `set security`
- Palo Alto: lines like `set deviceconfig ...`, `set rulebase ...`, `set shared ...`

We count how many style clues match each vendor (a score).
Highest score wins. Low/tied scores -> "unknown".
No AI is used here, so it works offline and never breaks the demo.

To add a new vendor later: just add a new entry to VENDOR_PATTERNS.
"""

import re
from dataclasses import dataclass, field

# Each pattern = (compiled regex, human-readable label).
# Weights: distinctive patterns count more (e.g. `set deviceconfig` only exists on Palo Alto).
VENDOR_PATTERNS: dict[str, list[tuple[re.Pattern, str, int]]] = {
    "cisco": [
        (re.compile(r"(?m)^\s*hostname\s+\S+", re.IGNORECASE), "hostname <name>", 1),
        (re.compile(r"(?m)^\s*interface\s+\S+", re.IGNORECASE), "interface <name>", 2),
        (re.compile(r"(?m)^\s*router\s+\S+", re.IGNORECASE), "router <protocol>", 2),
        (re.compile(r"(?m)^\s*access-list\s+\d+", re.IGNORECASE), "access-list <n>", 3),
        (re.compile(r"(?m)^\s*line\s+(vty|con|aux)", re.IGNORECASE), "line vty/con", 3),
        (re.compile(r"(?m)^\s*ip\s+ssh\s+version", re.IGNORECASE), "ip ssh version", 2),
        (re.compile(r"(?m)^\s*snmp-server\s+", re.IGNORECASE), "snmp-server ...", 2),
        (re.compile(r"(?m)^\s*logging\s+(buffered|host|trap)", re.IGNORECASE), "logging ...", 1),
        (re.compile(r"(?m)^\s*(service\s+(telnet|finger|pad|password-encryption)|no\s+service\s+telnet)", re.IGNORECASE), "service ...", 2),
        (re.compile(r"(?m)^\s*(ip\s+http\s+(server|secure-server)|no\s+ip\s+http\s+server)", re.IGNORECASE), "ip http server", 2),
    ],
    "juniper": [
        (re.compile(r"(?m)^\s*set\s+system\s+", re.IGNORECASE), "set system ...", 3),
        (re.compile(r"(?m)^\s*set\s+interfaces\s+", re.IGNORECASE), "set interfaces ...", 3),
        (re.compile(r"(?m)^\s*set\s+security\s+", re.IGNORECASE), "set security ...", 3),
        (re.compile(r"(?m)^\s*set\s+snmp\s+", re.IGNORECASE), "set snmp ...", 2),
        (re.compile(r"(?m)^\s*set\s+protocols\s+", re.IGNORECASE), "set protocols ...", 2),
        (re.compile(r"(?m)^\s*delete\s+system\s+services\s+", re.IGNORECASE), "delete system services", 2),
        (re.compile(r"(?m)^\s*set\s+system\s+services\s+(ssh|telnet|web-management)", re.IGNORECASE), "set system services ...", 2),
    ],
    "paloalto": [
        (re.compile(r"(?m)^\s*set\s+deviceconfig\s+", re.IGNORECASE), "set deviceconfig ...", 4),
        (re.compile(r"(?m)^\s*set\s+rulebase\s+", re.IGNORECASE), "set rulebase ...", 4),
        (re.compile(r"(?m)^\s*set\s+shared\s+", re.IGNORECASE), "set shared ...", 3),
        (re.compile(r"(?m)^\s*set\s+network\s+", re.IGNORECASE), "set network ...", 3),
        (re.compile(r"(?m)^\s*set\s+zone\s+", re.IGNORECASE), "set zone ...", 2),
    ],
}

MIN_SCORE_TO_DETECT = 2  # Below this, we honestly say "unknown".


@dataclass
class VendorResult:
    vendor: str  # cisco | juniper | paloalto | unknown
    confidence: float  # 0.0 - 1.0
    evidence: list[str] = field(default_factory=list)  # matched clue labels + sample lines
    scores: dict[str, int] = field(default_factory=dict)


def detect_vendor(raw_text: str) -> VendorResult:
    """Score the text against each vendor's patterns and pick the winner."""
    text = raw_text or ""
    scores: dict[str, int] = {}
    evidence: dict[str, list[str]] = {}

    for vendor, patterns in VENDOR_PATTERNS.items():
        total = 0
        hits: list[str] = []
        for regex, label, weight in patterns:
            match = regex.search(text)
            if match:
                total += weight
                # Keep the actual matched line as evidence (first 80 chars).
                line = match.group(0).strip().splitlines()[0][:80]
                hits.append(f"{label}  e.g. `{line}`")
        scores[vendor] = total
        evidence[vendor] = hits

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_vendor, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    total_score = sum(scores.values())

    # Tie or too-weak signal -> unknown (honest, hackathon-safe).
    if best_score < MIN_SCORE_TO_DETECT or best_score == second_score:
        return VendorResult(
            vendor="unknown",
            confidence=0.0 if total_score == 0 else round(second_score / max(total_score, 1), 2),
            evidence=[],
            scores=scores,
        )

    confidence = round(best_score / max(total_score, 1), 2)
    return VendorResult(
        vendor=best_vendor,
        confidence=confidence,
        evidence=evidence[best_vendor][:5],
        scores=scores,
    )
