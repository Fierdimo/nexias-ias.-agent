"""Endpoint principal de consultas en lenguaje natural.

Flujo (RAG-lite + herramientas externas):
  1. Cargar ventas del tenant (Google Sheets / muestra).
  2. Calcular métricas con pandas  ← números reales, no inventados.
  3. Pasar pregunta + métricas al LLM para que las redacte.
  4. Registrar auditoría (quién preguntó qué) en Supabase.
"""
import json

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.db.supabase_client import get_supabase
from app.schemas.chat import ChatRequest, ChatResponse
from app.config import get_settings
from app.services.analytics import build_metrics, build_metrics_dynamic
from app.services.data_sources import first_spreadsheet_id, get_schema
from app.services.google_oauth import get_valid_access_token
from app.services.sheet_analyzer import analyze_source
from app.services.llm import get_llm
from app.services.sheets import (
    SheetAccessError,
    load_sales,
    load_sales_oauth,
    service_account_email,
)
from app.services.tenants import get_tenant

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = (
    "Eres un asistente de analítica de negocio para empresas. Respondes en español, "
    "claro y breve. REGLA CRÍTICA: usa EXCLUSIVAMENTE los números del bloque "
    "DATOS. Si la respuesta no está en los datos, dilo explícitamente; nunca "
    "inventes cifras ni tendencias."
)


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    # Prioridad de fuente de datos de la empresa:
    #   1) hoja elegida en el Picker (OAuth del usuario, sin fricción)
    #   2) hoja vía service account (tenants.sheet_id, fallback)
    #   3) dataset de muestra
    settings = get_settings()
    schema: dict | None = None
    try:
        oauth_sheet = (
            first_spreadsheet_id(user.tenant_id)
            if settings.has_google_oauth
            else None
        )
        if oauth_sheet:
            access_token = get_valid_access_token(user.tenant_id)
            if not access_token:
                raise SheetAccessError(
                    "Tu conexión con Google expiró. Vuelve a conectarla en "
                    "Configuración."
                )
            df, is_demo = load_sales_oauth(oauth_sheet, access_token)
            schema = get_schema(user.tenant_id, oauth_sheet)
            if not schema:
                # Hoja sin analizar todavía: la inferimos al vuelo.
                schema = analyze_source(user.tenant_id, oauth_sheet)
        else:
            tenant = get_tenant(user.tenant_id)
            sheet_id = tenant.get("sheet_id") if tenant else None
            df, is_demo = load_sales(sheet_id=sheet_id)
    except SheetAccessError as exc:
        email = service_account_email()
        hint = f" Compártela con: {email}" if email else ""
        return ChatResponse(
            answer=f"⚠️ {exc}{hint}",
            tenant_id=user.tenant_id,
            is_demo=False,
            metrics={},
        )

    # Compatibilidad: si la hoja trae columna tenant_id, aislar también.
    if "tenant_id" in df.columns:
        df = df[df["tenant_id"].astype(str) == user.tenant_id]

    # Si tenemos esquema (camino OAuth o legacy con esquema persistido),
    # usamos métricas dinámicas por roles; si no, el cálculo legacy
    # asume columnas fijas (compatibilidad).
    metrics = (
        build_metrics_dynamic(df, schema) if schema else build_metrics(df)
    )

    user_prompt = (
        f"Pregunta del usuario:\n{req.message}\n\n"
        f"DATOS (calculados por el sistema, son la única fuente de verdad):\n"
        f"{json.dumps(metrics, ensure_ascii=False, indent=2)}"
    )
    answer = get_llm().chat(SYSTEM_PROMPT, user_prompt)

    _audit(user, req.message)

    return ChatResponse(
        answer=answer,
        tenant_id=user.tenant_id,
        is_demo=is_demo,
        metrics=metrics,
    )


def _audit(user: CurrentUser, message: str) -> None:
    """Registro de auditoría. Tabla: query_log(tenant_id, user_id, question)."""
    supabase = get_supabase()
    if supabase is None:
        return
    try:
        supabase.table("query_log").insert(
            {
                "tenant_id": user.tenant_id,
                "user_id": user.user_id,
                "question": message,
            }
        ).execute()
    except Exception:
        # La auditoría no debe tumbar la respuesta al usuario.
        pass
