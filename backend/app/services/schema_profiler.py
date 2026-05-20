"""Perfilado determinista de un DataFrame: tipos, muestras, conteos.

Es la entrada para que la IA (o la heurística) asigne roles a las
columnas. No usa LLM y es barato; corre cada vez que se infiere o
re-infiere el esquema.
"""
from __future__ import annotations

import pandas as pd


def profile_dataframe(df: pd.DataFrame, max_samples: int = 5) -> dict:
    """Devuelve un dict serializable con metadata de cada columna."""
    columns = []
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        col_type = _detect_type(series, non_null)
        samples = [_safe(v) for v in non_null.head(max_samples).tolist()]
        entry: dict = {
            "name": str(col),
            "type": col_type,
            "non_null": int(non_null.shape[0]),
            "samples": samples,
        }
        if col_type in ("text", "date"):
            entry["distinct"] = int(non_null.nunique()) if len(non_null) else 0
        if col_type == "number":
            entry["min"] = _safe(non_null.min()) if len(non_null) else None
            entry["max"] = _safe(non_null.max()) if len(non_null) else None
        columns.append(entry)
    return {"row_count": int(len(df)), "columns": columns}


def _detect_type(series: pd.Series, non_null: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "text"  # tratado como categórico
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if len(non_null) == 0:
        return "text"
    # Heurística: ¿80%+ se parsean como fecha?
    parsed = pd.to_datetime(non_null, errors="coerce")
    if parsed.notna().sum() / len(non_null) >= 0.8:
        return "date"
    # ¿80%+ se parsean como número (strings tipo "1.234,56" excluidos)?
    numeric = pd.to_numeric(non_null, errors="coerce")
    if numeric.notna().sum() / len(non_null) >= 0.8:
        return "number"
    return "text"


def _safe(v):
    """Convierte valores a tipos serializables JSON."""
    if v is None:
        return None
    if isinstance(v, (int, float, bool, str)):
        return v
    return str(v)
