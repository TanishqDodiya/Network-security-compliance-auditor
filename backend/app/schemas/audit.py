"""Schemas for audits and results."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditCreate(BaseModel):
    configuration_id: int = Field(examples=[1])


class AuditRunOut(BaseModel):
    id: int
    device_id: int
    configuration_id: int
    status: str
    compliance_percent: float
    started_at: datetime
    finished_at: datetime

    model_config = {"from_attributes": True}


class AuditResultOut(BaseModel):
    id: int
    audit_run_id: int
    rule_id: int | None
    rule_code: str
    title: str
    status: str
    severity: str
    evidence: str
    remediation: str

    model_config = {"from_attributes": True}
