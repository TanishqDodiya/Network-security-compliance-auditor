"""Schemas for compliance rules (demo rules, Phase 10 seeds real ones)."""

from pydantic import BaseModel, Field


class RuleCreate(BaseModel):
    rule_code: str = Field(min_length=1, max_length=16, examples=["NET-001"])
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default="General", max_length=64)
    severity: str = Field(default="MEDIUM", max_length=16)
    framework: list[str] = Field(default=["Demo Security Rule"])
    field: str = Field(min_length=1, max_length=128, examples=["management.telnet_enabled"])
    expected: bool | str | int | float | list | dict | None = False
    description: str = ""
    remediation: str = ""


class RuleOut(RuleCreate):
    id: int

    model_config = {"from_attributes": True}
