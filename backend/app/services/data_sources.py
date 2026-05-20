"""Archivos/carpetas que el tenant eligió en el Google Picker."""
from __future__ import annotations

import datetime as dt

from app.db.supabase_client import get_supabase, with_retry

SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"


def list_sources(tenant_id: str) -> list[dict]:
    if get_supabase() is None:
        return []
    res = with_retry(
        lambda: get_supabase()
        .table("data_sources")
        .select("file_id, name, mime_type, schema_json, schema_updated_at")
        .eq("tenant_id", tenant_id)
        .order("created_at")
        .execute()
    )
    return res.data or []


def get_schema(tenant_id: str, file_id: str) -> dict | None:
    if get_supabase() is None:
        return None
    res = with_retry(
        lambda: get_supabase()
        .table("data_sources")
        .select("schema_json")
        .eq("tenant_id", tenant_id)
        .eq("file_id", file_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0].get("schema_json") if rows else None


def set_schema(tenant_id: str, file_id: str, schema: dict) -> None:
    if get_supabase() is None:
        return
    payload = {
        "schema_json": schema,
        "schema_updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    with_retry(
        lambda: get_supabase()
        .table("data_sources")
        .update(payload)
        .eq("tenant_id", tenant_id)
        .eq("file_id", file_id)
        .execute()
    )


def replace_sources(tenant_id: str, files: list[dict]) -> list[dict]:
    """Reemplaza la selección del tenant por la lista elegida en el Picker."""
    if get_supabase() is None:
        return []
    with_retry(
        lambda: get_supabase()
        .table("data_sources")
        .delete()
        .eq("tenant_id", tenant_id)
        .execute()
    )
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
        with_retry(
            lambda: get_supabase().table("data_sources").insert(rows).execute()
        )
    return list_sources(tenant_id)


def first_spreadsheet_id(tenant_id: str) -> str | None:
    for s in list_sources(tenant_id):
        if s.get("mime_type") == SPREADSHEET_MIME:
            return s["file_id"]
    return None
