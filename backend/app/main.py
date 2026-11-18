"""FastAPI entry point: creates the app, adds CORS, and mounts the API routers."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, retrieval, tickets
from app.config import settings

app = FastAPI(title="Ask Onboarding API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(documents.router)
app.include_router(retrieval.router)
app.include_router(chat.router)
app.include_router(tickets.router)
