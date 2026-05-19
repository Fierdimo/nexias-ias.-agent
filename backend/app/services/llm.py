"""Capa de abstracción del LLM.

El resto del código nunca habla con un proveedor concreto: usa
`get_llm().chat(...)`. Así se puede cambiar Kimi por OpenAI/Claude
sin tocar la lógica de negocio.

Kimi (Moonshot) expone una API compatible con OpenAI, por eso el mismo
cliente `openai` sirve apuntando a otra base_url.
"""
from __future__ import annotations

from typing import Protocol

from app.config import get_settings


class LLMProvider(Protocol):
    def chat(self, system: str, user: str) -> str: ...


class MockProvider:
    """Sin credenciales: responde de forma determinista para probar el flujo."""

    def chat(self, system: str, user: str) -> str:
        return (
            "[MODO DEMO — sin LLM configurado]\n"
            "Recibí tu consulta y los datos calculados por el backend. "
            "Configura LLM_PROVIDER y LLM_API_KEY para respuestas reales.\n\n"
            f"Resumen de datos disponibles:\n{user[:800]}"
        )


class OpenAICompatibleProvider:
    """Sirve para Kimi/Moonshot y para OpenAI (misma interfaz)."""

    def __init__(self, api_key: str, base_url: str, model: str, max_tokens: int):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._max_tokens = max_tokens

    def chat(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=0.2,  # bajo: queremos respuestas fieles a los datos
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


_cached: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _cached
    if _cached is not None:
        return _cached

    settings = get_settings()
    if not settings.has_llm:
        _cached = MockProvider()
    else:
        # "kimi" y "openai" usan el mismo cliente; solo cambia base_url.
        _cached = OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
        )
    return _cached
