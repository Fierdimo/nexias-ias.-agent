"""Archivos/carpetas que el tenant eligió en el Google Picker."""
from __future__ import annotations

from app.db.supabase_client import get_supabase

SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"


def list_sources(tenant_id: str) -> list[dict]:
    supabase = get_supabase()
    if supabase is None:
        return []
    res = (
        supabase.table("data_sources")
        .select("file_id, name, mime_type")
        .eq("tenant_id", tenant_id)
        .order("created_at")
        .execute()
    )
    return res.data or []


def replace_sources(tenant_id: str, files: list[dict]) -> list[dict]:
    """Reemplaza la selección del tenant por la lista elegida en el Picker."""
    supabase = get_supabase()
    if supabase is None:
        return []
    supabase.table("data_sources").delete().eq(
        "tenant_id", tenant_id
    ).execute()
    rows = [
        {
            "tenant_id": tenant_id,
            "file_id": f["id"],
            "name": f.get("name"),
            "mime_type": f.get("mimeType"),
        }
        for f in files
        if f.get("id")
    ]
    if rows:
        supabase.table("data_sources").insert(rows).execute()
    return list_sources(tenant_id)


def first_spreadsheet_id(tenant_id: str) -> str | None:
    for s in list_sources(tenant_id):
        if s.get("mime_type") == SPREADSHEET_MIME:
            return s["file_id"]
    return None
