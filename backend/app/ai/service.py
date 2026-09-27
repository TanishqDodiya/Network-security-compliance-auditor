"""AI service: try the LLM, fall back to deterministic templates on any failure.

Only OpenAI-compatible chat completions are attempted (configurable model).
Any exception -> fallback. Callers always get a usable answer with an
honest `ai_available` flag. Human confirmation is still required before
any mapping is stored (Phase 12).
"""

from __future__ import annotations

import httpx

from app.ai import fallback
from app.ai.provider import load_ai_config

_LLM_TIMEOUT = 15.0


def _try_llm(prompt: str, max_tokens: int = 200) -> str | None:
    """Return LLM text or None on any failure (no key, network, bad response)."""
    cfg = load_ai_config()
    if not cfg.available:
        return None
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg.api_key}"},
            json={
                "model": cfg.model,
                "messages": [
                    {"role": "system", "content": "You are a network security assistant. Be concise and honest."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
            timeout=_LLM_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data["choices"][0]["message"]["content"] or "").strip() or None
    except Exception:
        return None


def analyze_unknown(text: str, vendor: str = "unknown") -> dict:
    """Classify an unknown config line. Always requires human confirmation."""
    guess = fallback.classify_unknown(text)
    cfg = load_ai_config()
    llm = _try_llm(
        f"Vendor: {vendor}\nConfig line: {text}\n"
        "Reply in one short line: what security category and meaning?"
    )
    meaning = llm or guess["meaning"]
    return {
        "vendor": vendor,
        "raw_text": text,
        "suggested_category": guess["suggested_category"],
        "suggested_field": guess["suggested_field"],
        "confidence": guess["confidence"],
        "meaning": meaning,
        "requires_confirmation": True,
        "ai_available": cfg.available and llm is not None,
        "provider": cfg.provider if (cfg.available and llm) else "fallback",
    }


def explain_finding(rule_code: str, title: str, status: str, evidence: str, remediation: str) -> dict:
    """Explain one PASS/FAIL in simple language."""
    template = fallback.explain_result(rule_code, title, status, evidence, remediation)
    cfg = load_ai_config()
    llm = _try_llm(
        f"Explain simply for a beginner admin (2 sentences max). "
        f"Rule {rule_code} {title} status {status}. Evidence: {evidence}. Fix: {remediation}."
    )
    text = llm or template
    return {
        "explanation": text,
        "ai_available": cfg.available and llm is not None,
        "provider": cfg.provider if (cfg.available and llm) else "fallback",
    }


def summarize_audit(results: list[dict]) -> dict:
    """Summarize a list of {status, severity} result dicts."""
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = total - passed
    critical = sum(1 for r in results if r.get("status") == "FAIL" and r.get("severity") == "CRITICAL")
    high = sum(1 for r in results if r.get("status") == "FAIL" and r.get("severity") == "HIGH")
    template = fallback.summarize_results(total, passed, failed, critical, high)
    cfg = load_ai_config()
    llm = _try_llm(f"Summarize in 2 sentences: {passed}/{total} passed, {failed} failed, {critical} critical, {high} high.")
    return {
        "summary": llm or template,
        "ai_available": cfg.available and llm is not None,
        "provider": cfg.provider if (cfg.available and llm) else "fallback",
    }
