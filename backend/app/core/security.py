"""Autenticación basada en Supabase Auth + aislamiento multi-tenant.

Flujo:
- El frontend hace login con Supabase Auth y obtiene un access_token (JWT).
- Lo manda en `Authorization: Bearer <token>`.
- Aquí validamos el token contra Supabase y resolvemos el tenant
  (empresa) y el rol del usuario desde la tabla `memberships`.

En modo demo (sin Supabase) se acepta un usuario ficticio para poder
probar el chat en local sin infraestructura.
"""
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.db.supabase_client import get_supabase, with_retry

DEMO_USER = {
    "user_id": "demo-user",
    "email": "demo@local",
    "tenant_id": "demo-company",
    "role": "admin",
}


@dataclass
class CurrentUser:
    user_id: str
    email: str
    tenant_id: str
    role: str  # admin | gerente | analista


def resolve_membership(supabase, user_id: str) -> tuple[str, str] | None:
    """Devuelve (tenant_id, role) del usuario o None si no pertenece a ninguno.

    Tabla esperada: memberships(user_id uuid, tenant_id uuid, role text).
    Reutilizado por get_current_user y por los endpoints de /auth.
    """
    res = with_retry(
        lambda: get_supabase()
        .table("memberships")
        .select("tenant_id, role")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    return str(rows[0]["tenant_id"]), rows[0]["role"]


def resolve_user_from_token(
    token: str | None, settings: Settings
) -> CurrentUser:
    """Valida un token Supabase y resuelve tenant+rol.

    Reutilizable por la dependencia normal (header) y por el Picker, que
    debe autenticar vía query param (un WebView GET no pone headers).
    """
    # --- Modo demo: sin Supabase configurado ---
    if not settings.has_supabase:
        return CurrentUser(**DEMO_USER)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token",
        )

    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase no disponible")

    try:
        result = with_retry(lambda: get_supabase().auth.get_user(token))
        auth_user = result.user
    except Exception:
        auth_user = None
    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    membership = resolve_membership(supabase, auth_user.id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no pertenece a ninguna empresa",
        )
    tenant_id, role = membership
    return CurrentUser(
        user_id=auth_user.id,
        email=auth_user.email or "",
        tenant_id=tenant_id,
        role=role,
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    return resolve_user_from_token(token, settings)
