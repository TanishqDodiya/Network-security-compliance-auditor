from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routers
from app.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create SQLite tables on startup (safe: never deletes data).
    init_db()
    yield


app = FastAPI(
    title="AI-Driven Multi-Vendor Network Security Compliance Auditor API",
    description="Hackathon MVP. Deterministic parsing/rules first, AI assists where valuable.",
    version="0.2.0",
    lifespan=lifespan,
)

# Basic CORS so the future React frontend can call the backend during development.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

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


for router in routers:
    app.include_router(router)
