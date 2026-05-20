"""Orquesta: cargar hoja → perfilar → inferir esquema → persistir."""
from __future__ import annotations

from app.services.data_sources import set_schema
from app.services.google_oauth import get_valid_access_token
from app.services.schema_inferrer import infer_schema
from app.services.schema_profiler import profile_dataframe
from app.services.sheets import SheetAccessError, load_sales_oauth


def analyze_source(
    tenant_id: str, file_id: str, name: str | None = None
) -> dict | None:
    """Analiza una hoja del tenant y guarda el esquema. Devuelve el esquema
    o None si no se pudo (sin Google conectado, hoja inaccesible, etc.)."""
    access_token = get_valid_access_token(tenant_id)
    if not access_token:
        return None
    try:
        df, _ = load_sales_oauth(file_id, access_token)
    except SheetAccessError:
        return None
    profile = profile_dataframe(df)
    schema = infer_schema(profile, sheet_name=name)
    set_schema(tenant_id, file_id, schema)
    return schema
