"""AI endpoints (real, with fallback).

AI behavior: always HTTP 200 with honest `ai_available` flag.
No key / LLM failure -> deterministic fallback so audits never break.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.service import analyze_unknown, explain_finding

router = APIRouter(tags=["ai-reports"])


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    vendor: str = "unknown"


class ExplainRequest(BaseModel):
    rule_code: str = "NET-001"
    title: str = "Rule"
    status: str = "FAIL"
    evidence: str = ""
    remediation: str = ""


@router.post("/api/ai/analyze")
def analyze(payload: AnalyzeRequest):
    """Classify unknown syntax. Caller must get human confirmation (Phase 12)."""
    return analyze_unknown(payload.text, payload.vendor)


@router.post("/api/ai/explain")
def explain(payload: ExplainRequest):
    """Explain one finding in simple language."""
    return explain_finding(
        payload.rule_code, payload.title, payload.status, payload.evidence, payload.remediation
    )
