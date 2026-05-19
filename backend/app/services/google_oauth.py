"""Google OAuth por tenant (scope drive.file).

El móvil hace el login con Google y obtiene un *server auth code*; lo manda
al backend, que lo intercambia por refresh+access token con el client secret
(tipo "Web"). El refresh token se guarda CIFRADO (Fernet) en
`google_accounts`, para poder leer las hojas elegidas incluso en reportes
sin el usuario presente.
"""
from __future__ import annotations

import datetime as dt

import httpx
from cryptography.fernet import Fernet

from app.config import get_settings
from app.db.supabase_client import get_supabase

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _fernet() -> Fernet:
    return Fernet(get_settings().token_enc_key.encode())


def _enc(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _dec(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def exchange_code(
    code: str, redirect_uri: str | None, code_verifier: str | None
) -> dict:
    """Cambia el auth code por tokens y resuelve el email del usuario."""
    s = get_settings()
    data = {
        "code": code,
        "client_id": s.google_oauth_client_id,
        "client_secret": s.google_oauth_client_secret,
        "grant_type": "authorization_code",
    }
    if redirect_uri:
        data["redirect_uri"] = redirect_uri
    if code_verifier:
        data["code_verifier"] = code_verifier
    with httpx.Client(timeout=15) as c:
        r = c.post(TOKEN_URL, data=data)
        r.raise_for_status()
        tok = r.json()
        email = None
        if tok.get("access_token"):
            ui = c.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {tok['access_token']}"},
            )
            if ui.status_code == 200:
                email = ui.json().get("email")
    if not tok.get("refresh_token"):
        raise RuntimeError(
            "Google no devolvió refresh_token (usa access_type=offline y "
            "prompt=consent en el login)"
        )
    return {
        "refresh_token": tok["refresh_token"],
        "access_token": tok.get("access_token"),
        "expires_in": tok.get("expires_in", 3600),
        "email": email,
    }


def _refresh_access_token(refresh_token: str) -> tuple[str, int]:
    s = get_settings()
    with httpx.Client(timeout=15) as c:
        r = c.post(
            TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": s.google_oauth_client_id,
                "client_secret": s.google_oauth_client_secret,
                "grant_type": "refresh_token",
            },
        )
        r.raise_for_status()
        tok = r.json()
    return tok["access_token"], tok.get("expires_in", 3600)


def save_account(
    tenant_id: str,
    email: str | None,
    refresh_token: str,
    access_token: str | None,
    expires_in: int,
) -> None:
    supabase = get_supabase()
    if supabase is None:
        return
    expiry = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        seconds=int(expires_in)
    )
    supabase.table("google_accounts").upsert(
        {
            "tenant_id": tenant_id,
            "google_email": email,
            "refresh_token_enc": _enc(refresh_token),
            "access_token_enc": _enc(access_token) if access_token else None,
            "access_expiry": expiry.isoformat(),
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    ).execute()


def get_account(tenant_id: str) -> dict | None:
    """Devuelve {google_email} o None si el tenant no conectó Google."""
    supabase = get_supabase()
    if supabase is None:
        return None
    res = (
        supabase.table("google_accounts")
        .select("google_email")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def get_valid_access_token(tenant_id: str) -> str | None:
    """Access token vigente del tenant; refresca y persiste si expiró."""
    supabase = get_supabase()
    if supabase is None:
        return None
    res = (
        supabase.table("google_accounts")
        .select("refresh_token_enc, access_token_enc, access_expiry")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    row = rows[0]
    now = dt.datetime.now(dt.timezone.utc)

    if row.get("access_token_enc") and row.get("access_expiry"):
        expiry = dt.datetime.fromisoformat(row["access_expiry"])
        if expiry > now + dt.timedelta(seconds=60):
            return _dec(row["access_token_enc"])

    access_token, expires_in = _refresh_access_token(
        _dec(row["refresh_token_enc"])
    )
    expiry = now + dt.timedelta(seconds=int(expires_in))
    supabase.table("google_accounts").update(
        {
            "access_token_enc": _enc(access_token),
            "access_expiry": expiry.isoformat(),
            "updated_at": now.isoformat(),
        }
    ).eq("tenant_id", tenant_id).execute()
    return access_token
