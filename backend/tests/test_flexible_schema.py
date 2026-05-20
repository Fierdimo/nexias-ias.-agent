"""Esquema flexible (Fase 1.5): perfilado, heurística y métricas dinámicas."""
import pandas as pd

from app.services.analytics import build_metrics_dynamic
from app.services.schema_inferrer import heuristic_roles, infer_schema
from app.services.schema_profiler import profile_dataframe


def _df():
    # Hoja "tipo restaurante" pero con nombres de columna alternos para
    # forzar a la heurística a inferir por keywords + tipos.
    return pd.DataFrame(
        {
            "Fecha venta": pd.date_range("2026-05-01", periods=10, freq="D"),
            "Producto": ["A", "B", "A", "C", "B", "A", "C", "B", "A", "C"],
            "Region": ["MX", "MX", "AR", "MX", "AR", "MX", "AR", "MX", "AR", "MX"],
            "Cantidad": [2, 1, 3, 5, 2, 4, 1, 6, 2, 3],
            "Total facturado": [20.0, 15.0, 30.0, 50.0, 18.0, 40.0, 12.0, 60.0, 22.0, 28.0],
        }
    )


def test_profile_detects_types():
    p = profile_dataframe(_df())
    types = {c["name"]: c["type"] for c in p["columns"]}
    assert types["Fecha venta"] == "date"
    assert types["Producto"] == "text"
    assert types["Cantidad"] == "number"
    assert types["Total facturado"] == "number"
    assert p["row_count"] == 10


def test_heuristic_assigns_expected_roles():
    schema = heuristic_roles(profile_dataframe(_df()))
    roles = {c["name"]: c["role"] for c in schema["columns"]}
    assert roles["Fecha venta"] == "date"
    # "Total facturado" debe ir a revenue por la keyword 'total'.
    assert roles["Total facturado"] == "revenue"
    assert roles["Cantidad"] == "quantity"
    # Categorías de texto agrupables.
    assert roles["Producto"] == "category"
    assert roles["Region"] == "category"
    # En modo demo (LLM mock) la heurística es la fuente.
    assert schema["source"] == "heuristic"


def test_dynamic_metrics_use_roles():
    schema = infer_schema(profile_dataframe(_df()), sheet_name="ventas")
    m = build_metrics_dynamic(_df(), schema)
    assert m["row_count"] == 10
    assert "rango_fechas" in m
    # Total de "Total facturado" debe ser la suma real (no inventada).
    assert m["totales_revenue"]["Total facturado"] == 295.0
    # Top por categoría sobre la columna revenue principal.
    assert "top_categorias_por_Total facturado" in m
