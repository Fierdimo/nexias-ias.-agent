from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    """Estado del servicio y qué integraciones están activas vs. en demo."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "integrations": {
            "supabase": settings.has_supabase,
            "llm": settings.has_llm,
            "llm_provider": settings.llm_provider,
            "google_sheets": settings.has_sheets,
        },
    }
