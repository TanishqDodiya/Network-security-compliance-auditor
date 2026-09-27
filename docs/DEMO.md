# Hackathon Demo Script (5–7 minutes)

Setup before stage: backend seeded (`python init_db.py && python seed_rules.py`),
backend on :8000, frontend on :5173, open `/dashboard`.

## The story (problem → solution → result)

> “Every vendor writes configs differently, so audits are manual and slow.
> We convert them into one common security model, check rules with evidence,
> let AI explain the unknowns, humans confirm, and out comes a report.”

## Steps

1. **Dashboard** — empty state explains what to do. Note the cards + charts
   (compliance %, PASS/FAIL, severity, vendors, categories).
2. **Upload** — pick `sample_configs/cisco/cisco_noncompliant.conf`.
   Show filename, **Vendor: cisco** (auto-detected), size, lines, time,
   **Ready for Audit**.
3. **[Run Audit]** — lands on the audit page. Point at compliance % (~0%).
4. **Failed rule** — click NET-001 (Telnet): read the **exact evidence line**
   (`service telnet`), why it failed, and the remediation.
5. **Remediation + Explain** — press **Explain** on a failed row; AI gives a
   beginner-friendly explanation (fallback works with no key).
6. **Compliant contrast** — upload `cisco_compliant.conf`, audit → ~100%.
7. **Second vendor** — upload `juniper_noncompliant.conf` → detected
   **juniper** → audit → fails. Same table shape: normalization works.
8. **Unknown syntax** — go to `/unknown-mappings`, analyze
   `set xyz secure-admin-mode enabled` → AI suggests **Management Security**,
   ~82%, **requires confirmation**.
9. **Human confirms** — Save as pending → Confirm with field
   `management.secure_admin_mode` → “Mapping saved successfully.”
10. **Stored reuse** — analyze the same line again → source **stored**,
    no AI call, no confirmation needed. (Learning = stored layer.)
11. **Reports** — `/reports` → Download PDF for the failed audit.
12. **PDF** — show title page, executive summary, severity counts, failed
    rules with evidence/remediation, mappings section, honesty footer.
13. **Rules** — `/rules`: 10 demo rules, labeled Demo Security Rule.
14. **Settings** — backend reachable, AI status (`fallback` with no key).
15. **Close**: “Cisco, Juniper, Palo Alto today; new vendors = one parser
    adapter. Deterministic where possible, AI where it helps.”

## Backup lines (if asked)

- “Do you support all vendors?” → “MVP: three. Architecture fits more.”
- “Did you train a model?” → “No — stored human-confirmed mappings.”
- “Does it guarantee security?” → “No — config-level demo checks.”
- AI key fails? → fallback already running; nothing breaks.
- No audits? → `sample_configs/` has compliant + non-compliant per vendor.
