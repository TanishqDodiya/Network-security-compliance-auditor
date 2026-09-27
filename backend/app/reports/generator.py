"""PDF report generator (fpdf2, core fonts only — no extra files needed).

Beginner idea: we build the PDF top to bottom like a document:
title -> device info -> executive summary -> severity table ->
failed rules (with evidence + fix) -> passed rules -> unknown syntax ->
honest footer note. All text comes from stored audit data; nothing new
is invented here.

fpdf2 note: after a full-width multi_cell the cursor stays at the right
margin, so every helper resets x to LMARGIN first.
"""

from __future__ import annotations

from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def _safe(text: object) -> str:
    """Core PDF fonts only support latin-1: replace anything exotic."""
    return str(text or "").encode("latin-1", errors="replace").decode("latin-1")


class AuditPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _mc(pdf: AuditPDF, h: float, text: str) -> None:
    """Cursor-safe multi_cell: always starts at left margin, ends on next line."""
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, h, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _section(pdf: AuditPDF, title: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 9, _safe(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _kv(pdf: AuditPDF, key: str, value: str) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 7, _safe(key))
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 7, _safe(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _result_block(pdf: AuditPDF, r: dict, failed: bool) -> None:
    color = (180, 30, 30) if failed else (25, 120, 50)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*color)
    pdf.cell(0, 7, _safe(f"{r.get('rule_code')} [{r.get('severity')}] {r.get('status')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 10)
    _mc(pdf, 6, str(r.get("title")))
    pdf.set_font("Helvetica", "", 9)
    _mc(pdf, 5.5, f"Evidence: {r.get('evidence')}")
    _mc(pdf, 5.5, f"Remediation: {r.get('remediation')}")
    pdf.ln(2)


def build_audit_pdf(
    *,
    device_name: str,
    vendor: str,
    audit_id: int,
    finished_at: str,
    compliance_percent: float,
    results: list[dict],
    summary: str,
    unknown_lines: list[str],
    mappings: list[dict],
) -> bytes:
    """Return the finished PDF as bytes."""
    pdf = AuditPDF(format="A4")
    pdf.alias_nb_pages()
    try:
        pdf.set_compression(False)  # keeps text searchable for tests/demo
    except Exception:
        pass
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    _mc(pdf, 10, "NETWORK SECURITY COMPLIANCE AUDIT REPORT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 7, _safe(f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(20, 20, 20)
    pdf.ln(2)

    _section(pdf, "1. Device Information")
    _kv(pdf, "Device", device_name)
    _kv(pdf, "Vendor", vendor)
    _kv(pdf, "Audit ID", str(audit_id))
    _kv(pdf, "Audit date", finished_at)
    _kv(pdf, "Overall compliance", f"{compliance_percent}%")

    passed = [r for r in results if r.get("status") == "PASS"]
    failed = [r for r in results if r.get("status") == "FAIL"]

    _section(pdf, "2. Executive Summary")
    pdf.set_font("Helvetica", "", 10)
    _mc(pdf, 6, summary)
    pdf.ln(1)
    _kv(pdf, "Rules checked", str(len(results)))
    _kv(pdf, "Passed", str(len(passed)))
    _kv(pdf, "Failed", str(len(failed)))
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        count = sum(1 for r in failed if r.get("severity") == sev)
        _kv(pdf, f"{sev} issues", str(count))

    _section(pdf, "3. Failed Rules (action required)")
    if not failed:
        pdf.set_font("Helvetica", "", 10)
        _mc(pdf, 6, "No failed rules. Configuration meets all demo checks.")
    for r in failed:
        _result_block(pdf, r, failed=True)

    _section(pdf, "4. Passed Rules")
    if not passed:
        pdf.set_font("Helvetica", "", 10)
        _mc(pdf, 6, "No passed rules.")
    for r in passed:
        _result_block(pdf, r, failed=False)

    _section(pdf, "5. Unknown Syntax / AI-assisted Mappings")
    if unknown_lines:
        pdf.set_font("Helvetica", "", 9)
        _mc(pdf, 5.5, "Unrecognized lines from this config (review candidates):")
        for line in unknown_lines[:20]:
            _mc(pdf, 5.5, f"- {line}")
    else:
        pdf.set_font("Helvetica", "", 10)
        _mc(pdf, 6, "No unrecognized lines in this configuration.")
    if mappings:
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 9)
        _mc(pdf, 5.5, "Human-reviewed mappings (stored layer, not model retraining):")
        for m in mappings[:20]:
            _mc(pdf, 5.5, f"- [{m.get('status')}] {m.get('vendor')}: {m.get('raw_pattern')} -> {m.get('normalized_field')}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    _mc(
        pdf, 5.5,
        "Note: checks use internally created Demo Security Rules for the hackathon MVP. "
        "This report is a configuration-level check, not a replacement for a complete security assessment.",
    )

    out = pdf.output()
    return bytes(out)
