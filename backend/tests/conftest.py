"""Hace los tests herméticos: fuerzan MODO DEMO sin importar el .env local.

Los smoke tests verifican el camino sin credenciales (datos de muestra,
LLM mock, usuario demo). Estas env vars tienen prioridad sobre backend/.env
en pydantic-settings, así que el test no depende de tu configuración real
ni hace llamadas de red al LLM/Supabase.
"""
import os

# Debe ejecutarse antes de que se importe la app (conftest carga primero).
os.environ.update(
    {
        "SUPABASE_URL": "",
        "SUPABASE_ANON_KEY": "",
        "SUPABASE_SERVICE_KEY": "",
        "LLM_PROVIDER": "mock",
        "LLM_API_KEY": "",
        "GOOGLE_CREDENTIALS_PATH": "",
        "GOOGLE_SHEET_ID": "",
    }
)
