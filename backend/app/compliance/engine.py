"""Compliance engine: vendor-independent PASS/FAIL evaluation.

Beginner idea: each rule says "look at this field in the normalized model,
I expect this value". The engine compares actual vs expected and records
PASS/FAIL + severity + evidence (the exact config line) + remediation.

No `if vendor == ...` here. Ever. All vendor differences were already
removed by normalization (Phase 9).
"""

from dataclasses import dataclass, field


@dataclass
class RuleResult:
    rule_code: str
    title: str
    status: str  # PASS | FAIL
    severity: str
    category: str
    description: str
    evidence: str
    remediation: str
    field: str = ""
    expected: object = None
    actual: object = None


def _rule_passes(actual, expected, pass_on_none: bool) -> bool:
    """None means 'not mentioned in config'. Strict by default (FAIL),
    except rules that explicitly allow it (e.g. 'no bad service seen' -> PASS)."""
    if actual is None:
        return bool(pass_on_none)
    return actual == expected


def evaluate_rule(rule, normalized) -> RuleResult:
    """Evaluate one rule (DB object or dict) against a NormalizedConfig."""
    if isinstance(rule, dict):
        code = rule["rule_code"]
        title = rule["title"]
        severity = rule.get("severity", "MEDIUM")
        category = rule.get("category", "General")
        description = rule.get("description", "")
        remediation = rule.get("remediation", "")
        field_path = rule["field"]
        expected = rule.get("expected")
        pass_on_none = bool(rule.get("pass_on_none", False))
        rule_id = None
    else:
        code = rule.rule_code
        title = rule.title
        severity = rule.severity
        category = rule.category
        description = rule.description
        remediation = rule.remediation
        field_path = rule.field
        expected = rule.expected
        pass_on_none = False  # DB rows use strict mode; pass_on_none lives in rules_data seeds.
        rule_id = rule.id

    actual = normalized.get_field(field_path)
    # DB-backed rules NET-005/008/009 also tolerate None (same as seed data).
    if not isinstance(rule, dict) and code in {"NET-005", "NET-008", "NET-009"}:
        pass_on_none = True

    passed = _rule_passes(actual, expected, pass_on_none)
    evidence = normalized.evidence.get(field_path, "")
    if not evidence:
        if actual is None:
            evidence = f"No evidence for {field_path} (not configured / not detected)"
        else:
            evidence = f"{field_path} = {actual}"

    result = RuleResult(
        rule_code=code,
        title=title,
        status="PASS" if passed else "FAIL",
        severity=severity,
        category=category,
        description=description,
        evidence=evidence,
        remediation=remediation,
        field=field_path,
        expected=expected,
        actual=actual,
    )
    result.rule_id = rule_id  # type: ignore[attr-defined]
    return result


def evaluate_all(normalized, rules) -> list[RuleResult]:
    """Evaluate every rule. Returns one result per rule, in rule order."""
    return [evaluate_rule(rule, normalized) for rule in rules]


def compliance_percent(results: list[RuleResult]) -> float:
    """0-100 score. Empty rule set = 0.0 (honest, not 100)."""
    if not results:
        return 0.0
    passed = sum(1 for r in results if r.status == "PASS")
    return round(passed / len(results) * 100, 2)
