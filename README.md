# AI-Driven Multi-Vendor Network Security Compliance Auditor

Hackathon MVP: upload network-device configs (Cisco, Juniper, Palo Alto),
detect the vendor, parse security settings into one common model, check
10 demo compliance rules, explain findings with AI assistance, let humans
confirm unknown syntax, and download a PDF report.

> Honest scope: the MVP supports **Cisco, Juniper and Palo Alto** configs.
> The architecture supports more vendors via new parser adapters.
> AI **assists** interpretation/explanations; deterministic parsing and rules
> do the real work and the demo runs fully **without any API key**.

## Problem Statement

Organizations use devices from multiple vendors, each with different config
syntax. Manual compliance auditing is slow and error-prone, and findings
often lack evidence (“why did this fail?”) and fixes (“what do I do?”).

## Solution

A web platform that converts vendor configs into a **common security
representation**, evaluates **vendor-independent rules**, and produces
actionable PASS/FAIL results with severity, evidence, remediation, AI
explanations, human-confirmed mappings for unknown syntax, and PDF reports.

## Architecture

```text
Upload (.txt/.conf/.cfg, validated, never executed)
  -> Vendor Detection (pattern scoring, no AI)
  -> Vendor Parser (Cisco | Juniper | Palo Alto adapter)
  -> Normalization (one NormalizedConfig model)
  -> Compliance Engine (10 demo rules, PASS/FAIL + severity)
  -> AI assist (unknown-syntax suggestion, explanations, summary; fallback if no key)
  -> Human confirmation (stored mappings reused before AI)
  -> Dashboard + PDF report
```

Key principle: `VendorParser -> Normalized Model -> Compliance Engine`.
No `if vendor == ...` inside compliance rules.

## Tech Stack

- Frontend: React 19, Vite, JavaScript, Tailwind CSS v4, Recharts, react-router-dom
- Backend: Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, Pydantic, python-multipart, python-dotenv, fpdf2, httpx
- Database: SQLite (`auditor.db`), SQLAlchemy ORM, no migrations for MVP (`create_all`)
- AI: `AI_PROVIDER`/`AI_API_KEY` env config, OpenAI-compatible call with deterministic fallback
- Tests: pytest (42 tests), live rehearsal script pattern

## Project Structure

```text
network-security-auditor/
├── frontend/src/
│   ├── components/ (Layout, Badge, StatCard)
│   ├── pages/ (Dashboard, Upload, Devices, Audits, Rules, Mappings, Reports, Settings)
│   ├── services/api.js, hooks/useFetch.js, utils/format.js
│   └── App.jsx (router), main.jsx
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI + CORS + routers)
│   │   ├── api/ (devices, configurations, detect, normalize, audits, rules, mappings, reports, extras)
│   │   ├── models/ (users, devices, configurations, audit_runs, compliance_rules, audit_results, unknown_mappings)
│   │   ├── schemas/ (Pydantic request/response shapes)
│   │   ├── services/ (vendor_detector, mapping_review)
│   │   ├── parsers/cisco|juniper|paloalto/
│   │   ├── normalization/ (NormalizedConfig + dispatcher)
│   │   ├── compliance/ (engine + DEMO_RULES NET-001..010)
│   │   ├── ai/ (provider, fallback, service)
│   │   ├── reports/ (fpdf2 generator)
│   │   └── database/ (engine, SessionLocal, Base, get_db, init_db)
│   ├── tests/ (12 test files, 42 tests)
│   ├── init_db.py, seed_rules.py, requirements.txt
│   └── auditor.db (created locally, gitignored)
├── sample_configs/cisco|juniper|paloalto/ (compliant + non-compliant each)
├── rules/ (reserved for future rule files; rules currently in app/compliance/rules_data.py + DB)
├── docs/DEMO.md (hackathon demo script)
├── .env.example / .env (never commit .env)
└── README.md
```

## Installation

Prerequisites: Python 3.10+, Node 18+, Git.

Backend (Windows PowerShell; macOS/Linux uses `source venv/bin/activate`):

```powershell
cd network-security-auditor\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
python seed_rules.py
```

Frontend:

```bash
cd network-security-auditor/frontend
npm install
```

## Environment Variables

```bash
cp .env.example .env   # PowerShell: Copy-Item .env.example .env
```

| Variable | Meaning | Default |
|---|---|---|
| `APP_NAME` | Display name | auditor title |
| `APP_ENV` | `development` / `production` | `development` |
| `DATABASE_URL` | SQLAlchemy URL | `sqlite:///./auditor.db` |
| `AI_PROVIDER` | `none` or `openai` | `none` (fallback mode) |
| `AI_API_KEY` | LLM key, **never commit** | empty |
| `AI_MODEL` | OpenAI model | `gpt-4o-mini` |
| `VITE_API_URL` | Backend URL for frontend (`frontend/.env`) | `http://127.0.0.1:8000` |

## How to Run Backend

```bash
cd network-security-auditor/backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000/ · Health: `/health`
- Swagger: http://127.0.0.1:8000/docs · ReDoc: `/redoc`
- Tests: `python -m pytest tests/ -v` (42 passed)

## How to Run Frontend

```bash
cd network-security-auditor/frontend
npm run dev     # http://localhost:5173/dashboard
npm run build   # production build check
```

## How Configuration Parsing Works

Each vendor parser reads lines with regexes and fills the same fields
(`telnet/ssh/http/https, logging, ntp+servers, snmp, auth, mgmt restriction`)
plus `evidence[field] = exact line` and `unknown_lines`. Example:
`no service telnet` → `telnet_enabled=False`. Unknown lines are kept for the
AI/human flow. Uploads are validated (type/size/binary/lines), sanitized,
stored as text, never executed.

## How Normalization Works

`normalize_text(vendor, text)` picks the vendor parser, then maps its result
into `NormalizedConfig` (`device/management/logging/authentication/snmp/ntp`
+ evidence + unknown lines). Dotted paths like `management.telnet_enabled`
work identically for every vendor. Unknown vendor → honest empty model.
Preview: `POST /api/normalize`.

## How Compliance Rules Work

Rules (NET-001…NET-010, `Demo Security Rule` label) say
“field X must equal Y”. The engine compares normalized actual vs expected,
records PASS/FAIL + severity + evidence + remediation, and scores
`passed/total*100`. `None` (not mentioned) FAILs strictly, except
NET-005/008/009 where “nothing bad seen” passes. `POST /api/audits`
normalizes → evaluates → stores results. Seed: `python seed_rules.py`.

## How AI Works

`app/ai/`: provider config → try OpenAI chat completions (15 s timeout) →
any failure falls back to keyword classification + template explanations.
`POST /api/ai/analyze` (unknown syntax, always `requires_confirmation`),
`POST /api/ai/explain` (simple-language finding), summaries for reports.
Without a key everything still works; responses carry `ai_available`.

## Human-in-the-Loop Workflow

Unknown line → `POST /api/mappings/resolve` checks stored mappings first
(confirmed = reuse, no AI; pending = show queue) → else AI suggestion →
human Confirms (with normalized field) / Rejects / picks category via
`PATCH /api/mappings/{id}` → stored under unique `(vendor, raw_pattern)`.
Stored layer, not model retraining. UI: `/unknown-mappings`.

## Database Structure

`users | devices | configurations (raw text, vendor, status) | audit_runs
(percent, status) | compliance_rules (rule_code unique) |
audit_results (per-rule PASS/FAIL + evidence snapshot) |
unknown_mappings (vendor+raw_pattern unique, status, confirmed_by)`.

## API Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/`, `/health`, `/docs`, `/redoc` | meta |
| POST/GET | `/api/devices`, `GET /api/devices/{id}` | 409 on duplicate |
| POST | `/api/configurations/upload` | multipart, 400/413 validation |
| GET | `/api/configurations` | list |
| POST | `/api/detect` | vendor + evidence |
| POST | `/api/normalize` | common model preview |
| POST/GET | `/api/audits`, `GET /api/audits/{id}` | runs compliance |
| GET | `/api/results/{audit_id}` | PASS/FAIL rows |
| GET/POST | `/api/rules` | demo rules |
| GET/POST/PATCH | `/api/mappings`, `/mappings/resolve` | human loop |
| POST | `/api/ai/analyze`, `/api/ai/explain` | always 200 + flag |
| GET | `/api/reports/{audit_id}` | PDF download, 404/500 handled |

## Demo Instructions

See `docs/DEMO.md` — full 18-step script (dashboard → Cisco upload →
audit → failed rule + evidence + remediation → unknown syntax → AI
suggest → human confirm → stored reuse → PDF). 5-minute rehearsal
validated all-pass on a clean DB.

## Future Scope

More vendors (one parser adapter each), rule packs (real CIS mappings),
auth/RBAC, Alembic migrations, Postgres, background audit jobs, config
diffing, scheduled re-audits, more LLM providers.

## Limitations

- Demo rules are internally created, not verified CIS/NIST controls.
- Parsers cover security-relevant subsets, not full vendor CLIs.
- AI suggestions need human confirmation; fallback is keyword-based.
- SQLite + `create_all`, no auth on APIs (hackathon MVP).
- No frontend unit tests (build + smoke tested).

## Deploy (frontend + backend, same domain)

`deploy.json` routes `/api/*` to the backend service and everything else to
the frontend (Vite build output). The frontend uses same-origin relative
`/api` calls by default, so no `VITE_API_URL` is needed in production.

Backend service:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- Tables are created and demo rules auto-seeded on first boot (re-runs are no-ops).
- `/api/health` works as a platform healthcheck.
- Set `CORS_ORIGINS` only if the frontend is served from another domain.
- SQLite stores data on local disk: attach a persistent volume or data resets
  on redeploy. Use Postgres + `DATABASE_URL` for anything beyond the hackathon.
