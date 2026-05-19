"""Configuración central. Todo se lee de variables de entorno (.env).

El diseño es modular: si faltan credenciales, los servicios entran en
"modo demo" en lugar de romper el arranque, para poder probar en local.
"""
import re
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "Nexias"
    environment: str = "local"
    cors_origins: str = "*"  # coma-separado en producción

    # --- Supabase (DB + Auth) ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""  # solo backend, nunca al frontend

    @field_validator("supabase_url")
    @classmethod
    def _normalize_supabase_url(cls, v: str) -> str:
        """Acepta que peguen la URL REST por error.

        El SDK espera solo la base (https://<ref>.supabase.co); él añade
        /auth/v1, /rest/v1, etc. Quitamos sufijos de path y barra final
        para que no se rompa con "Invalid path specified in request URL".
        """
        v = v.strip()
        if not v:
            return v
        v = re.sub(r"/(rest|auth|storage|realtime)/v1/?$", "", v)
        return v.rstrip("/")

    # --- Proveedor LLM (modular) ---
    # provider: "kimi" | "openai" | "mock"
    llm_provider: str = "mock"
    llm_api_key: str = ""
    # Kimi/Moonshot es compatible con la API de OpenAI:
    #   internacional: https://api.moonshot.ai/v1
    #   china:         https://api.moonshot.cn/v1
    llm_base_url: str = "https://api.moonshot.ai/v1"
    llm_model: str = "moonshot-v1-32k"
    llm_max_tokens: int = 1024

    # --- Google Sheets (service account, fallback) ---
    # Ruta al JSON de service account; vacío => modo demo con datos de muestra
    google_credentials_path: str = ""
    google_sheet_id: str = ""

    # --- Google OAuth + Picker (scope drive.file, sin verificación CASA) ---
    # OAuth client tipo "Web" (id + secret en el backend para el intercambio).
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_api_key: str = ""  # para el Google Picker
    google_project_number: str = ""  # appId del Picker
    # Clave Fernet para cifrar refresh tokens en reposo. Genera con:
    #   python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
    token_enc_key: str = ""

    # --- Documentos ---
    documents_dir: str = "../data/documents"

    @property
    def has_google_oauth(self) -> bool:
        return bool(
            self.google_oauth_client_id
            and self.google_oauth_client_secret
            and self.token_enc_key
        )

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def has_llm(self) -> bool:
        return self.llm_provider != "mock" and bool(self.llm_api_key)

    @property
    def has_sheets(self) -> bool:
        return bool(self.google_credentials_path and self.google_sheet_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
