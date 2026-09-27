"""Import every model here so SQLAlchemy sees all tables.

Why: `Base.metadata.create_all()` only creates tables for models it knows about.
Importing them in one place guarantees they are registered.
"""

from app.models.audit_result import AuditResult
from app.models.audit_run import AuditRun
from app.models.compliance_rule import ComplianceRule
from app.models.configuration import Configuration
from app.models.device import Device
from app.models.unknown_mapping import UnknownMapping
from app.models.user import User

__all__ = [
    "AuditResult",
    "AuditRun",
    "ComplianceRule",
    "Configuration",
    "Device",
    "UnknownMapping",
    "User",
]
