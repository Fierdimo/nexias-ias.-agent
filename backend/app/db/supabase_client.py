"""Cliente Supabase (DB + Auth). Singleton perezoso + retry transparente.

`get_supabase()` cachea el cliente. Si no hay credenciales, devuelve None
y los endpoints degradan a modo demo.

`with_retry(fn)` ejecuta `fn()` y reintenta UNA vez si la conexión HTTP/2
de supabase-py se cerró por inactividad (RemoteProtocolError) — bug
conocido al recuperar conexiones idle del pool. Antes del reintento se
invalida el cache para forzar un cliente nuevo.
"""
from functools import lru_cache
from typing import Callable, TypeVar

import httpx

from app.config import get_settings

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - dependencia opcional en dev
    Client = None  # type: ignore
    create_client = None  # type: ignore

T = TypeVar("T")

# Excepciones de red que indican "conexión muerta, reintentar con fresca".
_RETRYABLE = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.ConnectError,
    httpx.ReadTimeout,
)


@lru_cache
def get_supabase():
    settings = get_settings()
    if not settings.has_supabase or create_client is None:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_key)


def with_retry(fn: Callable[[], T]) -> T:
    """Ejecuta fn(); si revienta por conexión muerta, recrea cliente y reintenta."""
    try:
        return fn()
    except _RETRYABLE:
        get_supabase.cache_clear()
        return fn()
