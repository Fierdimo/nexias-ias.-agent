"""Acceso a la configuración del restaurante (tenant) en Supabase."""
from __future__ import annotations

from app.db.supabase_client import get_supabase


def get_tenant(tenant_id: str) -> dict | None:
    """Devuelve {id, name, sheet_id} o None si no existe / sin Supabase."""
    supabase = get_supabase()
    if supabase is None:
        return None
    res = (
        supabase.table("tenants")
        .select("id, name, sheet_id")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def set_tenant_sheet(tenant_id: str, sheet_id: str | None) -> None:
    """Actualiza la Google Sheet asociada al restaurante."""
    supabase = get_supabase()
    if supabase is None:
        return
    supabase.table("tenants").update({"sheet_id": sheet_id}).eq(
        "id", tenant_id
    ).execute()
