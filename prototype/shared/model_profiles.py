"""Lädt und aktiviert Modellprofile für LLM- und Embedding-Schritte.

Das Modul übersetzt YAML-Profile in Laufzeit-Metadaten und Umgebungsvariablen,
damit Experimente reproduzierbare Modellkombinationen verwenden können.
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml

from prototype.shared.constants import (
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_OPENAI_EMBEDDING_MODEL,
    ENC_UTF8,
    ENV_ACTIVE_MODEL_PROFILE,
    ENV_EMBEDDING_PROVIDER,
    ENV_LLM_PROVIDER,
    ENV_LOCAL_EMBEDDING_MODEL,
    ENV_MODEL_PROFILE_ID,
    ENV_MODEL_PROFILE_LABEL,
    ENV_OLLAMA_MODEL,
    ENV_OPENAI_EMBEDDING_MODEL,
    ENV_OPENAI_MODEL,
    ENV_TEMPERATURE,
    LLM_PROVIDER_OPENAI,
    MODEL_ALL_MINILM_L6_V2,
    PROVIDER_LOCAL,
    PROVIDER_OPENAI,
)
from prototype.shared.paths import MODEL_PROFILES_PATH


LLM_STEP_INJECTION_DETECTION = "injection_detection"
LLM_STEP_CLASSIFICATION = "classification"
LLM_STEP_ANSWER_GENERATION = "answer_generation"
LLM_STEP_ANSWER_COMPLETENESS = "answer_completeness"
EMBEDDING_STEP_RETRIEVAL = "retrieval"

KNOWN_LLM_STEPS = {
    LLM_STEP_INJECTION_DETECTION,
    LLM_STEP_CLASSIFICATION,
    LLM_STEP_ANSWER_GENERATION,
    LLM_STEP_ANSWER_COMPLETENESS,
}

KNOWN_EMBEDDING_STEPS = {
    EMBEDDING_STEP_RETRIEVAL,
}

PROFILE_ENV_KEYS = [
    ENV_ACTIVE_MODEL_PROFILE,
    ENV_MODEL_PROFILE_ID,
    ENV_MODEL_PROFILE_LABEL,
    ENV_LLM_PROVIDER,
    ENV_OLLAMA_MODEL,
    ENV_OPENAI_MODEL,
    ENV_EMBEDDING_PROVIDER,
    ENV_OPENAI_EMBEDDING_MODEL,
    ENV_LOCAL_EMBEDDING_MODEL,
    ENV_TEMPERATURE,
]


@dataclass(frozen=True)
class LLMProfileStep:
    provider: str
    model: str
    temperature: str = DEFAULT_LLM_TEMPERATURE

    def metadata(self, step_name: str) -> dict[str, str]:
        return {
            f"{step_name}_llm_provider": self.provider,
            f"{step_name}_llm_model": self.model,
            f"{step_name}_temperature": self.temperature,
        }


@dataclass(frozen=True)
class EmbeddingProfileStep:
    provider: str
    model: str

    def metadata(self, step_name: str) -> dict[str, str]:
        return {
            f"{step_name}_embedding_provider": self.provider,
            f"{step_name}_embedding_model": self.model,
        }


@dataclass(frozen=True)
class ModelProfile:
    profile_id: str
    label: str
    llm_provider: str
    llm_model: str
    temperature: str = DEFAULT_LLM_TEMPERATURE
    llm_steps: dict[str, LLMProfileStep] | None = None
    embedding_steps: dict[str, EmbeddingProfileStep] | None = None
    notes: str = ""

    def llm_step(self, step_name: str) -> LLMProfileStep:
        if self.llm_steps and step_name in self.llm_steps:
            return self.llm_steps[step_name]

        return LLMProfileStep(
            provider=self.llm_provider,
            model=self.llm_model,
            temperature=self.temperature,
        )

    def embedding_step(self, step_name: str) -> EmbeddingProfileStep:
        if self.embedding_steps and step_name in self.embedding_steps:
            return self.embedding_steps[step_name]

        available = ", ".join(sorted(KNOWN_EMBEDDING_STEPS))
        raise ValueError(
            f"Model-Profil {self.profile_id!r} enthält keinen Embedding-Schritt {step_name!r}. "
            f"Erlaubt und erforderlich: {available}"
        )

    def metadata(self) -> dict[str, str]:
        metadata = {
            "model_profile_id": self.profile_id,
            "model_profile_label": self.label,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "temperature": self.temperature,
        }

        for step_name in sorted(KNOWN_LLM_STEPS):
            metadata.update(self.llm_step(step_name).metadata(step_name))

        for step_name in sorted(KNOWN_EMBEDDING_STEPS):
            metadata.update(self.embedding_step(step_name).metadata(step_name))

        return metadata

def _profile_from_dict(profile_id: str, data: dict) -> ModelProfile:
    llm_provider = str(data.get("llm_provider") or LLM_PROVIDER_OPENAI).strip().lower()
    llm_model = str(data.get("llm_model") or "").strip()
    embedding_steps = _embedding_steps_from_dict(profile_id, data.get("embedding_steps") or {})

    if not llm_model:
        raise ValueError(f"Model-Profil {profile_id!r} enthält kein llm_model.")
    if EMBEDDING_STEP_RETRIEVAL not in embedding_steps:
        raise ValueError(
            f"Model-Profil {profile_id!r} muss embedding_steps.{EMBEDDING_STEP_RETRIEVAL} enthalten."
        )

    return ModelProfile(
        profile_id=profile_id,
        label=str(data.get("label") or profile_id).strip(),
        llm_provider=llm_provider,
        llm_model=llm_model,
        temperature=str(data.get("temperature", DEFAULT_LLM_TEMPERATURE)).strip(),
        llm_steps=_llm_steps_from_dict(profile_id, data.get("llm_steps") or {}),
        embedding_steps=embedding_steps,
        notes=str(data.get("notes") or "").strip(),
    )


def _llm_steps_from_dict(profile_id: str, raw_steps: dict) -> dict[str, LLMProfileStep]:
    if not isinstance(raw_steps, dict):
        raise ValueError(f"Model-Profil {profile_id!r}: llm_steps muss ein Mapping sein.")

    steps = {}
    for step_name, step_data in raw_steps.items():
        step_name = str(step_name).strip()
        if step_name not in KNOWN_LLM_STEPS:
            available = ", ".join(sorted(KNOWN_LLM_STEPS))
            raise ValueError(
                f"Model-Profil {profile_id!r}: unbekannter LLM-Schritt {step_name!r}. "
                f"Erlaubt: {available}"
            )

        if not isinstance(step_data, dict):
            raise ValueError(
                f"Model-Profil {profile_id!r}: LLM-Schritt {step_name!r} muss ein Mapping sein."
            )

        provider = str(step_data.get("provider") or "").strip().lower()
        model = str(step_data.get("model") or "").strip()
        temperature = str(step_data.get("temperature", DEFAULT_LLM_TEMPERATURE)).strip()

        if not provider or not model:
            raise ValueError(
                f"Model-Profil {profile_id!r}: LLM-Schritt {step_name!r} braucht provider und model."
            )

        steps[step_name] = LLMProfileStep(
            provider=provider,
            model=model,
            temperature=temperature,
        )

    return steps


def _embedding_steps_from_dict(profile_id: str, raw_steps: dict) -> dict[str, EmbeddingProfileStep]:
    if not isinstance(raw_steps, dict):
        raise ValueError(f"Model-Profil {profile_id!r}: embedding_steps muss ein Mapping sein.")

    steps = {}
    for step_name, step_data in raw_steps.items():
        step_name = str(step_name).strip()
        if step_name not in KNOWN_EMBEDDING_STEPS:
            available = ", ".join(sorted(KNOWN_EMBEDDING_STEPS))
            raise ValueError(
                f"Model-Profil {profile_id!r}: unbekannter Embedding-Schritt {step_name!r}. "
                f"Erlaubt: {available}"
            )

        if not isinstance(step_data, dict):
            raise ValueError(
                f"Model-Profil {profile_id!r}: Embedding-Schritt {step_name!r} muss ein Mapping sein."
            )

        provider = str(step_data.get("provider") or "").strip().lower()
        model = str(step_data.get("model") or "").strip()

        if not provider or not model:
            raise ValueError(
                f"Model-Profil {profile_id!r}: Embedding-Schritt {step_name!r} braucht provider und model."
            )

        steps[step_name] = EmbeddingProfileStep(
            provider=provider,
            model=model,
        )

    return steps



def load_model_profiles(path: Path = MODEL_PROFILES_PATH) -> dict[str, ModelProfile]:
    config = yaml.safe_load(path.read_text(encoding=ENC_UTF8)) or {}
    raw_profiles = config.get("profiles") or {}

    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ValueError(f"Keine Model-Profile in {path} gefunden.")

    return {
        str(profile_id): _profile_from_dict(str(profile_id), data or {})
        for profile_id, data in raw_profiles.items()
    }



def get_model_profile(profile_id: str, path: Path = MODEL_PROFILES_PATH) -> ModelProfile:
    profiles = load_model_profiles(path)

    if profile_id not in profiles:
        available = ", ".join(sorted(profiles))
        raise KeyError(f"Unbekanntes Model-Profil {profile_id!r}. Verfügbar: {available}")

    return profiles[profile_id]



def get_active_model_profile_id() -> str:
    return os.getenv(ENV_ACTIVE_MODEL_PROFILE, "").strip()



def get_active_model_profile() -> ModelProfile | None:
    profile_id = get_active_model_profile_id()
    if not profile_id:
        return None

    return get_model_profile(profile_id)



def apply_model_profile(profile: ModelProfile) -> None:
    os.environ[ENV_ACTIVE_MODEL_PROFILE] = profile.profile_id
    os.environ[ENV_MODEL_PROFILE_ID] = profile.profile_id
    os.environ[ENV_MODEL_PROFILE_LABEL] = profile.label
    os.environ[ENV_LLM_PROVIDER] = profile.llm_provider

    if profile.llm_provider == LLM_PROVIDER_OPENAI:
        os.environ[ENV_OPENAI_MODEL] = profile.llm_model
    else:
        os.environ[ENV_OLLAMA_MODEL] = profile.llm_model

    os.environ[ENV_TEMPERATURE] = profile.temperature

    retrieval_step = profile.embedding_step(EMBEDDING_STEP_RETRIEVAL)
    os.environ[ENV_EMBEDDING_PROVIDER] = retrieval_step.provider
    if retrieval_step.provider == PROVIDER_OPENAI:
        os.environ[ENV_OPENAI_EMBEDDING_MODEL] = retrieval_step.model
    else:
        os.environ[ENV_LOCAL_EMBEDDING_MODEL] = retrieval_step.model



def apply_active_model_profile() -> ModelProfile | None:
    profile = get_active_model_profile()
    if profile is None:
        return None

    apply_model_profile(profile)
    return profile



def active_llm_step_metadata(step_name: str) -> dict[str, str]:
    profile = get_active_model_profile()
    if profile is not None:
        step = profile.llm_step(step_name)
        return {
            "llm_provider": step.provider,
            "llm_model": step.model,
            "temperature": step.temperature,
        }

    model_metadata = active_model_metadata()

    return {
        "llm_provider": model_metadata.get("llm_provider", ""),
        "llm_model": model_metadata.get("llm_model", ""),
        "temperature": model_metadata.get("temperature", DEFAULT_LLM_TEMPERATURE),
    }


def active_embedding_step_metadata(step_name: str) -> dict[str, str]:
    profile = get_active_model_profile()
    if profile is not None:
        step = profile.embedding_step(step_name)
        return {
            "embedding_provider": step.provider,
            "embedding_model": step.model,
        }

    model_metadata = active_model_metadata()
    return {
        "embedding_provider": model_metadata.get("embedding_provider", PROVIDER_LOCAL),
        "embedding_model": model_metadata.get("embedding_model", MODEL_ALL_MINILM_L6_V2),
    }


@contextmanager
def model_profile_environment(profile: ModelProfile) -> Iterator[None]:
    previous_values = {
        key: os.environ.get(key)
        for key in PROFILE_ENV_KEYS
    }

    apply_model_profile(profile)

    try:
        yield
    finally:
        for key, value in previous_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def active_model_metadata() -> dict[str, str]:
    profile = get_active_model_profile()
    if profile is not None:
        return profile.metadata()

    llm_provider = os.getenv(ENV_LLM_PROVIDER, "").strip().lower()
    llm_model = (
        os.getenv(ENV_OPENAI_MODEL, "")
        if llm_provider == LLM_PROVIDER_OPENAI
        else os.getenv(ENV_OLLAMA_MODEL, "")
    ).strip()
    embedding_provider = os.getenv(ENV_EMBEDDING_PROVIDER, PROVIDER_LOCAL).strip().lower()
    embedding_model = (
        os.getenv(ENV_OPENAI_EMBEDDING_MODEL, DEFAULT_OPENAI_EMBEDDING_MODEL)
        if embedding_provider == PROVIDER_OPENAI
        else os.getenv(ENV_LOCAL_EMBEDDING_MODEL, MODEL_ALL_MINILM_L6_V2)
    ).strip()

    metadata = {
        "model_profile_id": os.getenv(ENV_MODEL_PROFILE_ID, "").strip(),
        "model_profile_label": os.getenv(ENV_MODEL_PROFILE_LABEL, "").strip(),
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "embedding_provider": embedding_provider,
        "embedding_model": embedding_model,
        "temperature": os.getenv(ENV_TEMPERATURE, DEFAULT_LLM_TEMPERATURE).strip(),
    }

    for step_name in sorted(KNOWN_LLM_STEPS):
        metadata.update(LLMProfileStep(
            provider=llm_provider,
            model=llm_model,
            temperature=metadata["temperature"],
        ).metadata(step_name))

    for step_name in sorted(KNOWN_EMBEDDING_STEPS):
        metadata.update(EmbeddingProfileStep(
            provider=embedding_provider,
            model=embedding_model,
        ).metadata(step_name))

    return metadata
