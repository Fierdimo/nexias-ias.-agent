"""Asigna roles a las columnas para que el chat pueda calcular métricas.

Roles definidos:
- date     : columna temporal principal (única)
- revenue  : monto monetario para sumar
- quantity : conteo / cantidad para sumar
- category : dimensión para agrupar
- id       : identificador (se ignora en métricas)
- ignore   : irrelevante

Estrategia:
1. Heurística por palabras clave + tipo (siempre se ejecuta, barata y
   determinista).
2. Si hay LLM real, se le pide refinar/validar devolviendo JSON estricto.
   Si parsea, sustituye la heurística; si no, se queda la heurística.

Sale una sola vez por hoja (se persiste el resultado). Anti-alucinación:
ningún número sale del LLM; solo asignaciones de columna → rol.
"""
from __future__ import annotations

import datetime as dt
import json
import re

from app.services.llm import MockProvider, get_llm

DATE_HINTS = (
    "fecha", "date", "dia", "día", "month", "mes", "year", "año", "timestamp",
    "creado", "created", "updated", "actualizado",
)
REVENUE_HINTS = (
    "total", "importe", "monto", "ingreso", "revenue", "amount", "precio",
    "venta", "sales", "cost", "costo", "subtotal", "neto", "bruto", "gross",
)
QUANTITY_HINTS = (
    "cantidad", "qty", "quantity", "unidades", "units", "count", "num",
    "stock", "inventario",
)
ID_HINTS = ("id", "uuid", "codigo", "código", "sku", "ref", "referencia")


def heuristic_roles(profile: dict) -> dict:
    """Asignación rápida por nombre+tipo. Garantiza un esquema utilizable."""
    columns = []
    date_assigned = False
    revenue_assigned_to: str | None = None
    quantity_assigned_to: str | None = None
    for col in profile["columns"]:
        role = _heuristic_role(
            col, date_assigned, revenue_assigned_to is not None,
            quantity_assigned_to is not None,
        )
        if role == "date":
            date_assigned = True
        if role == "revenue":
            revenue_assigned_to = col["name"]
        if role == "quantity":
            quantity_assigned_to = col["name"]
        columns.append({"name": col["name"], "role": role})
    return {
        "columns": columns,
        "summary": "Esquema asignado por reglas (sin IA).",
        "source": "heuristic",
    }


def _heuristic_role(col: dict, date_taken, revenue_taken, qty_taken) -> str:
    name = col["name"].lower()
    type_ = col["type"]
    if not date_taken and (
        type_ == "date" or any(h in name for h in DATE_HINTS)
    ):
        return "date"
    if any(h == name or name.endswith("_" + h) for h in ID_HINTS):
        return "id"
    if type_ == "number":
        if not revenue_taken and any(h in name for h in REVENUE_HINTS):
            return "revenue"
        if not qty_taken and any(h in name for h in QUANTITY_HINTS):
            return "quantity"
        # Por defecto, una numérica desconocida cuenta como cantidad
        if not qty_taken:
            return "quantity"
        return "ignore"
    if type_ == "text":
        # Texto con cardinalidad baja-media => categoría agrupable
        distinct = col.get("distinct", 0) or 0
        if 1 < distinct <= 200:
            return "category"
        return "ignore"
    return "ignore"


_SYSTEM = (
    "Eres un analista de datos. Recibes un PERFIL de columnas de una hoja "
    "y debes asignar a cada columna un rol entre: date, revenue, quantity, "
    "category, id, ignore. Devuelve SOLO JSON con esta forma exacta:\n"
    '{"columns":[{"name":"...","role":"..."}], "summary":"frase corta '
    'describiendo qué representa la hoja en español"}\n'
    "Reglas: a lo sumo UNA columna 'date' (la temporal principal); "
    "al menos una 'revenue' si hay alguna numérica de dinero; texto con "
    "valores repetidos => 'category'. No expliques nada fuera del JSON."
)


def infer_with_llm(profile: dict, sheet_name: str | None) -> dict | None:
    """Intenta refinar la heurística con el LLM. None si no es posible."""
    llm = get_llm()
    if isinstance(llm, MockProvider):
        return None
    user = json.dumps(
        {"sheet_name": sheet_name, "profile": profile},
        ensure_ascii=False,
    )
    try:
        raw = llm.chat(_SYSTEM, user)
    except Exception:
        return None
    parsed = _extract_json(raw)
    if not parsed or "columns" not in parsed:
        return None
    valid_roles = {"date", "revenue", "quantity", "category", "id", "ignore"}
    cleaned = []
    for c in parsed["columns"]:
        name = c.get("name")
        role = c.get("role")
        if not name or role not in valid_roles:
            continue
        cleaned.append({"name": str(name), "role": role})
    if not cleaned:
        return None
    return {
        "columns": cleaned,
        "summary": str(parsed.get("summary", "")).strip()
                   or "Esquema interpretado por IA.",
        "source": "ai",
    }


def _extract_json(text: str) -> dict | None:
    """Acepta texto con bloques de código o ruido alrededor del JSON."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fence.group(1) if fence else text
    m = re.search(r"\{.*\}", candidate, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def infer_schema(profile: dict, sheet_name: str | None = None) -> dict:
    """Combina heurística + LLM (si está disponible). Persiste-friendly."""
    heur = heuristic_roles(profile)
    ai = infer_with_llm(profile, sheet_name)
    final = ai or heur
    final["version"] = 1
    final["row_count"] = profile.get("row_count")
    final["columns_profile"] = profile["columns"]  # útil para auditoría/UI
    final["analyzed_at"] = dt.datetime.now(dt.timezone.utc).isoformat(
        timespec="seconds"
    )
    return final
