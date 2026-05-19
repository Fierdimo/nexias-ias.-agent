"""Punto de entrada FastAPI.

Local:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Docs:   http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, google, health, tenant
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tenant.router)
app.include_router(google.router)
app.include_router(chat.router)


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}
