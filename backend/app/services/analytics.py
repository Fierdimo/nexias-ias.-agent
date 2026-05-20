"""Cálculos de negocio FUERA del LLM.

Clave anti-alucinación: los números los calcula pandas, no el modelo.
El LLM solo recibe estos resultados ya computados y los redacta en
lenguaje natural.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd


def build_metrics(df: pd.DataFrame) -> dict:
    """Resumen determinista que se inyecta al prompt del LLM."""
    if df.empty:
        return {"aviso": "No hay datos de ventas disponibles."}

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])

    hoy = df["fecha"].max()
    ult_7 = df[df["fecha"] > hoy - pd.Timedelta(days=7)]
    prev_7 = df[
        (df["fecha"] <= hoy - pd.Timedelta(days=7))
        & (df["fecha"] > hoy - pd.Timedelta(days=14))
    ]

    ingresos_7 = float(ult_7["ingresos"].sum())
    ingresos_prev_7 = float(prev_7["ingresos"].sum())
    var = (
        round((ingresos_7 - ingresos_prev_7) / ingresos_prev_7 * 100, 1)
        if ingresos_prev_7
        else None
    )

    top = (
        df.groupby("producto")["ingresos"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .round(2)
        .to_dict()
    )
    por_categoria = (
        df.groupby("categoria")["ingresos"].sum().round(2).to_dict()
    )

    return {
        "rango_fechas": {
            "desde": df["fecha"].min().date().isoformat(),
            "hasta": hoy.date().isoformat(),
        },
        "ingresos_totales": round(float(df["ingresos"].sum()), 2),
        "ingresos_ultimos_7d": round(ingresos_7, 2),
        "ingresos_7d_previos": round(ingresos_prev_7, 2),
        "variacion_semanal_pct": var,
        "ticket_promedio": round(
            float(df["ingresos"].sum() / df["cantidad"].sum()), 2
        ),
        "top_productos": top,
        "ingresos_por_categoria": por_categoria,
        "generado": dt.datetime.now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# Esquema flexible: métricas dinámicas según los roles asignados a columnas
# ---------------------------------------------------------------------------

def _cols_by_role(schema: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in schema.get("columns", []):
        out.setdefault(c.get("role", "ignore"), []).append(c["name"])
    return out


def build_metrics_dynamic(df: pd.DataFrame, schema: dict) -> dict:
    """Métricas calculadas según el esquema (no hardcodea nombres).

    Cubre cualquier hoja: rango temporal, sumas por rol revenue/quantity,
    top categorías y variación semanal sobre la primera columna revenue
    cuando hay fecha. Cálculos en pandas → anti-alucinación.
    """
    metrics: dict = {
        "row_count": int(len(df)),
        "schema_summary": schema.get("summary"),
        "generado": dt.datetime.now().isoformat(timespec="seconds"),
    }
    if df.empty:
        metrics["aviso"] = "La hoja está vacía."
        return metrics

    df = df.copy()
    by_role = _cols_by_role(schema)
    date_col = by_role.get("date", [None])[0]
    revenue_cols = [c for c in by_role.get("revenue", []) if c in df.columns]
    quantity_cols = [c for c in by_role.get("quantity", []) if c in df.columns]
    category_cols = [c for c in by_role.get("category", []) if c in df.columns]

    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        if not df.empty:
            hoy = df[date_col].max()
            metrics["rango_fechas"] = {
                "desde": df[date_col].min().date().isoformat(),
                "hasta": hoy.date().isoformat(),
            }
            if revenue_cols:
                main_rev = revenue_cols[0]
                ult = df[df[date_col] > hoy - pd.Timedelta(days=7)]
                prev = df[
                    (df[date_col] <= hoy - pd.Timedelta(days=7))
                    & (df[date_col] > hoy - pd.Timedelta(days=14))
                ]
                a = float(pd.to_numeric(ult[main_rev], errors="coerce").sum())
                b = float(pd.to_numeric(prev[main_rev], errors="coerce").sum())
                metrics["ultimos_7d"] = {main_rev: round(a, 2)}
                metrics["7d_previos"] = {main_rev: round(b, 2)}
                metrics["variacion_semanal_pct"] = (
                    round((a - b) / b * 100, 1) if b else None
                )

    for col in revenue_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        metrics.setdefault("totales_revenue", {})[col] = round(float(s.sum()), 2)

    for col in quantity_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        metrics.setdefault("totales_quantity", {})[col] = float(s.sum())

    # Top por categoría: usa la primera columna revenue o quantity disponible.
    metric_col = revenue_cols[0] if revenue_cols else (
        quantity_cols[0] if quantity_cols else None
    )
    if metric_col and category_cols:
        tops = {}
        for cat in category_cols[:2]:
            s = pd.to_numeric(df[metric_col], errors="coerce").fillna(0)
            top = (
                df.assign(_m=s)
                .groupby(cat)["_m"]
                .sum()
                .sort_values(ascending=False)
                .head(5)
                .round(2)
                .to_dict()
            )
            tops[cat] = top
        metrics[f"top_categorias_por_{metric_col}"] = tops

    return metrics
