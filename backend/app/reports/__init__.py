"""Expose the report generator from one place."""

from app.reports.generator import build_audit_pdf

__all__ = ["build_audit_pdf"]
