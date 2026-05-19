"""Lectura de datos de ventas desde Google Sheets, una hoja por restaurante.

Estructura de hoja esperada (primera fila = encabezados):
    fecha | producto | categoria | cantidad | ingresos

Modelo multi-tenant: cada tenant guarda su `sheet_id` en la tabla
`tenants`. Un único service account de Google puede leer todas las hojas
que estén compartidas con su email.

Sin credenciales o sin sheet configurada => dataset de muestra (demo).
"""
from __future__ import annotations

import datetime as dt
import json
import random
import re

import pandas as pd

from app.config import get_settings

_SAMPLE_CACHE: pd.DataFrame | None = None


class SheetAccessError(Exception):
    """No se pudo leer la hoja del tenant (no compartida, ID inválido…)."""


def extract_sheet_id(raw: str) -> str:
    """Acepta el ID pelado o una URL completa de Google Sheets."""
    raw = raw.strip()
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", raw)
    return m.group(1) if m else raw


def service_account_email() -> str | None:
    """Email del service account (para indicar con quién compartir la hoja)."""
    settings = get_settings()
    if not settings.google_credentials_path:
        return None
    try:
        with open(settings.google_credentials_path) as fh:
            return json.load(fh).get("client_email")
    except Exception:
        return None


def _sample_sales() -> pd.DataFrame:
    global _SAMPLE_CACHE
    if _SAMPLE_CACHE is not None:
        return _SAMPLE_CACHE
    rng = random.Random(42)
    productos = [
        ("Hamburguesa Clásica", "Platos"),
        ("Pizza Margarita", "Platos"),
        ("Ensalada César", "Platos"),
        ("Limonada", "Bebidas"),
        ("Cerveza Artesanal", "Bebidas"),
        ("Brownie", "Postres"),
    ]
    today = dt.date.today()
    rows = []
    for d in range(30):  # últimos 30 días
        fecha = today - dt.timedelta(days=d)
        for nombre, cat in productos:
            cantidad = rng.randint(2, 25)
            precio = {"Platos": 12.0, "Bebidas": 4.5, "Postres": 6.0}[cat]
            rows.append(
                {
                    "fecha": fecha.isoformat(),
                    "producto": nombre,
                    "categoria": cat,
                    "cantidad": cantidad,
                    "ingresos": round(cantidad * precio, 2),
                }
            )
    _SAMPLE_CACHE = pd.DataFrame(rows)
    return _SAMPLE_CACHE


def load_sales(sheet_id: str | None = None) -> tuple[pd.DataFrame, bool]:
    """Devuelve (dataframe, es_demo).

    Usa la hoja del tenant (`sheet_id`); si no hay credenciales o no hay
    hoja configurada, cae al dataset de muestra (es_demo=True).
    """
    settings = get_settings()
    effective = sheet_id or settings.google_sheet_id or None

    if not settings.google_credentials_path or not effective:
        return _sample_sales(), True

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    try:
        creds = Credentials.from_service_account_file(
            settings.google_credentials_path, scopes=scopes
        )
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(extract_sheet_id(effective)).sheet1
        df = pd.DataFrame(sheet.get_all_records())
    except Exception as exc:
        raise SheetAccessError(
            "No pude leer la hoja del restaurante. Verifica el ID y que "
            f"esté compartida con el service account. Detalle: {exc}"
        )

    return _normalize(df), False


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Tipos defensivos sobre el esperado fecha|...|cantidad|ingresos."""
    if df.empty:
        return df
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(
            df["fecha"], errors="coerce"
        ).dt.date.astype(str)
    for col in ("cantidad", "ingresos"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def load_sales_oauth(
    spreadsheet_id: str, access_token: str
) -> tuple[pd.DataFrame, bool]:
    """Lee una hoja con el OAuth del usuario (archivo elegido en el Picker)."""
    import gspread
    from google.oauth2.credentials import Credentials

    try:
        creds = Credentials(token=access_token)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(extract_sheet_id(spreadsheet_id)).sheet1
        df = pd.DataFrame(sheet.get_all_records())
    except Exception as exc:
        raise SheetAccessError(
            f"No pude leer la hoja seleccionada de Google. Detalle: {exc}"
        )
    return _normalize(df), False
