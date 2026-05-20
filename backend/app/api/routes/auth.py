"""Autenticación: el backend hace de proxy de Supabase Auth.

La app móvil solo habla con FastAPI (no incrusta el SDK de Supabase).
- /auth/signup: crea usuario (confirmado), su empresa y la membresía
  de admin, y devuelve sesión iniciada. Onboarding en una sola llamada.
- /auth/login: valida credenciales y devuelve token + perfil.
- /auth/me: perfil del token actual.

En modo demo (sin Supabase) devuelven una sesión ficticia para que el
flujo de la app funcione igual en local.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.core.security import (
    DEMO_USER,
    CurrentUser,
    get_current_user,
    resolve_membership,
)
from app.db.supabase_client import get_supabase, with_retry
from app.schemas.auth import AuthResponse, LoginRequest, Profile, SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])

_DEMO_AUTH = AuthResponse(
    access_token="demo-token",
    refresh_token=None,
    profile=Profile(
        user_id=DEMO_USER["user_id"],
        email=DEMO_USER["email"],
        tenant_id=DEMO_USER["tenant_id"],
        role=DEMO_USER["role"],
    ),
    is_demo=True,
)


def _session_tokens(result) -> tuple[str, str | None]:
    session = getattr(result, "session", None)
    if session is None or not getattr(session, "access_token", None):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return session.access_token, getattr(session, "refresh_token", None)


@router.post("/signup", response_model=AuthResponse)
def signup(
    req: SignupRequest, settings: Settings = Depends(get_settings)
) -> AuthResponse:
    if not settings.has_supabase:
        return _DEMO_AUTH

    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase no disponible")

    # 1. Crear usuario ya confirmado (sin verificación por email para el MVP)
    try:
        created = supabase.auth.admin.create_user(
            {
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
            }
        )
        user = created.user
    except Exception as exc:  # email duplicado u otro error de gotrue
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se pudo crear el usuario: {exc}",
        )

    # 2. Crear empresa (tenant) y 3. membresía como admin
    try:
        tenant = (
            supabase.table("tenants")
            .insert({"name": req.company_name})
            .execute()
        )
        tenant_id = str(tenant.data[0]["id"])
        supabase.table("memberships").insert(
            {"user_id": user.id, "tenant_id": tenant_id, "role": "admin"}
        ).execute()
    except Exception as exc:
        # Limpieza para no dejar un usuario huérfano si falla el tenant.
        try:
            supabase.auth.admin.delete_user(user.id)
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail=f"No se pudo crear la empresa: {exc}"
        )

    # 4. Iniciar sesión y devolver tokens
    result = supabase.auth.sign_in_with_password(
        {"email": req.email, "password": req.password}
    )
    access_token, refresh_token = _session_tokens(result)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        profile=Profile(
            user_id=user.id,
            email=req.email,
            tenant_id=tenant_id,
            role="admin",
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    req: LoginRequest, settings: Settings = Depends(get_settings)
) -> AuthResponse:
    if not settings.has_supabase:
        return _DEMO_AUTH

    supabase = get_supabase()
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase no disponible")

    try:
        result = with_retry(
            lambda: get_supabase().auth.sign_in_with_password(
                {"email": req.email, "password": req.password}
            )
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    access_token, refresh_token = _session_tokens(result)
    user = result.user

    membership = resolve_membership(supabase, user.id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no pertenece a ninguna empresa",
        )
    tenant_id, role = membership

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        profile=Profile(
            user_id=user.id,
            email=user.email or req.email,
            tenant_id=tenant_id,
            role=role,
        ),
    )


@router.get("/me", response_model=Profile)
def me(user: CurrentUser = Depends(get_current_user)) -> Profile:
    return Profile(
        user_id=user.user_id,
        email=user.email,
        tenant_id=user.tenant_id,
        role=user.role,
    )
