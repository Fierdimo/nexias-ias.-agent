"""Cliente Supabase (DB + Auth). Singleton perezoso.

Si no hay credenciales, `get_supabase()` devuelve None y los endpoints
que dependan de él deben degradar a modo demo.
"""
from functools import lru_cache

from app.config import get_settings

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - dependencia opcional en dev
    Client = None  # type: ignore
    create_client = None  # type: ignore


@lru_cache
def get_supabase():
    settings = get_settings()
    if not settings.has_supabase or create_client is None:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_key)
