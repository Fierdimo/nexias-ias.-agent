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
