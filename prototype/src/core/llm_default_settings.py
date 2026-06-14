"""Standardwerte für LLM-Anbieter und Modellnamen.

Dieses kleine Modul stellt zentrale Defaults bereit, wenn keine explizite
Konfiguration oder kein aktives Modellprofil gesetzt ist.
"""

from prototype.shared.constants import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENAI_MODEL,
    LLM_PROVIDER_OLLAMA,
    LLM_PROVIDER_OPENAI,
)

OLLAMA = LLM_PROVIDER_OLLAMA
OPENAI = LLM_PROVIDER_OPENAI

LLM_PROVIDER_DEFAULT = DEFAULT_LLM_PROVIDER

OPENAI_MODEL_DEFAULT = DEFAULT_OPENAI_MODEL
OLLAMA_MODEL_DEFAULT = DEFAULT_OLLAMA_MODEL
TEMPERATURE_DEFAULT = DEFAULT_LLM_TEMPERATURE
