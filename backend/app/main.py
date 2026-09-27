from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routers
from app.database.session import SessionLocal, init_db
import os


def cors_origins() -> list[str]:
    """Local dev defaults + extra origins from CORS_ORIGINS env (comma-separated).

    Same-origin production deploys (frontend + /api on one domain) need no
    CORS entry; set CORS_ORIGINS only if the frontend lives on another domain.
    """
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    extra = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    return origins + [o for o in extra if o not in origins]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create SQLite tables on startup (safe: never deletes data).
    init_db()
    # Auto-seed demo rules on fresh databases so deploys work with no extra step.
    try:
        from app.compliance.seed import ensure_demo_rules

        db = SessionLocal()
        try:
            created, total = ensure_demo_rules(db)
            if created:
                print(f"Auto-seeded {created} demo rules (total {total}).")
        finally:
            db.close()
    except Exception as exc:  # audits fall back to built-in rules, so never block boot
        print(f"Warning: rule auto-seed skipped ({exc}).")
    yield


app = FastAPI(
    title="AI-Driven Multi-Vendor Network Security Compliance Auditor API",
    description="Hackathon MVP. Deterministic parsing/rules first, AI assists where valuable.",
    version="0.2.0",
    lifespan=lifespan,
)

# Basic CORS for local development; extend via CORS_ORIGINS env in production.
origins = cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "AI-Driven Multi-Vendor Network Security Compliance Auditor API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/health")
def api_health_check():
    # Same payload under /api/* so it works behind rewrites/proxies
    # that only forward /api to the backend, and as a platform healthcheck.
    return {"status": "healthy"}


for router in routers:
    app.include_router(router)
