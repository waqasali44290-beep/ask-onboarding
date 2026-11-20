"""FastAPI entry point: creates the app, adds CORS, and mounts the API routers."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, documents, messages, retrieval, tickets
from app.auth import ensure_demo_users
from app.config import settings
from app.db import SessionLocal, engine

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "db" / "init.sql"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On start: apply the (idempotent) schema, then make sure the demo accounts exist."""
    with engine.begin() as connection:
        connection.exec_driver_sql(SCHEMA_FILE.read_text())
    with SessionLocal() as session:
        ensure_demo_users(session)
    yield


app = FastAPI(title="Ask Onboarding API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(retrieval.router)
app.include_router(chat.router)
app.include_router(messages.router)
app.include_router(tickets.router)
