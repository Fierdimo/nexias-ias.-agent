"""Acceso a la configuración de la empresa (tenant) en Supabase."""
from __future__ import annotations

from app.db.supabase_client import get_supabase, with_retry


def get_tenant(tenant_id: str) -> dict | None:
    """Devuelve {id, name, sheet_id} o None si no existe / sin Supabase."""
    if get_supabase() is None:
        return None
    res = with_retry(
        lambda: get_supabase()
        .table("tenants")
        .select("id, name, sheet_id")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def set_tenant_sheet(tenant_id: str, sheet_id: str | None) -> None:
    """Actualiza la Google Sheet asociada a la empresa."""
    if get_supabase() is None:
        return
    with_retry(
        lambda: get_supabase()
        .table("tenants")
        .update({"sheet_id": sheet_id})
        .eq("id", tenant_id)
        .execute()
    )
