"""Zentraler Runner für Pipeline-Versionen innerhalb der Web- und Operations-Apps.

Das Modul wählt Konfiguration, Wissensbasis und API-Funktion je Version und
normalisiert Ergebnisse auf ein UI-stabiles Rückgabeformat.
"""

import importlib
import sys
import time
import types
from functools import lru_cache
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

CURRENT_FILE = Path(__file__).resolve()
LOCAL_PROTOTYPE_DIR = next(parent for parent in CURRENT_FILE.parents if parent.name == "prototype")
LOCAL_PROJECT_ROOT = LOCAL_PROTOTYPE_DIR.parent

for path in [LOCAL_PROJECT_ROOT, LOCAL_PROTOTYPE_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prototype.shared.bootstrap import ensure_project_import_paths

ensure_project_import_paths(__file__)

from prototype.shared.constants import ENCODING_UTF8, EXT_MD, FILENAME_README
from prototype.shared.model_profiles import active_model_metadata
from prototype.shared.paths import knowledge_base_path_for_version, municipality_config_path_for_version, V5_OUTPUT_DIR
from src.v5.core.constants import FILENAME_AUDIT_LOG_JSONL

# Zentrale Versionsmatrix für die UI: Neue Pipeline-Versionen sollten hier
# ergänzt werden, damit Importpfade und Vector-Store-Anforderungen an einer
# Stelle nachvollziehbar bleiben.
VERSION_SPECS = {
    "V1": {
        "api_module": "src.v1.api.v1_api",
        "api_function": "run_v1_pipeline",
        "uses_vector_store": False,
    },
    "V2": {
        "api_module": "src.v2.api.v2_api",
        "api_function": "run_v2_pipeline",
        "uses_vector_store": True,
    },
    "V3": {
        "api_module": "src.v3.api.v3_api",
        "api_function": "run_v3_pipeline",
        "uses_vector_store": True,
    },
    "V4": {
        "api_module": "src.v4.api.v4_api",
        "api_function": "run_v4_pipeline",
        "uses_vector_store": True,
    },
    "V5": {
        "api_module": "src.v5.api.v5_api",
        "api_function": "run_v5_pipeline_with_audit",
        "uses_vector_store": True,
    },
}


def normalize_version(version: str) -> str:
    return version.strip().upper()


def version_key(version: str) -> str:
    return version.lower().replace(".", "_")


def version_spec_for(version: str) -> dict[str, Any]:
    normalized_version = normalize_version(version)
    spec = VERSION_SPECS.get(normalized_version)

    if spec is None:
        raise ValueError(f"Unbekannte Version: {version}")

    return spec


def import_version_module(version: str, module_name: str) -> types.ModuleType:
    return importlib.import_module(f"src.{version_key(version)}.{module_name}")


def path_mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def knowledge_base_fingerprint(path: Path) -> float:
    if not path.exists():
        return 0.0

    mtimes = [
        file_path.stat().st_mtime
        for file_path in path.rglob(EXT_MD)
        if file_path.name.lower() != FILENAME_README
    ]

    return max(mtimes) if mtimes else path.stat().st_mtime


@lru_cache(maxsize=4)
def get_config_cached(config_path: str, modified_time: float) -> dict[str, Any]:
    path = Path(config_path)
    return yaml.safe_load(path.read_text(encoding=ENCODING_UTF8)) or {}


@st.cache_resource
def get_vector_store_cached(
        version: str,
        knowledge_base_path: str,
        fingerprint: float,
        embedding_provider: str,
        embedding_model: str,
):
    """
    Lädt Wissensbasis, Chunking und Retrieval dynamisch für eine Pipeline-Version.

    Die Cache-Signatur enthält Wissensbasis-Fingerprint und Embedding-Metadaten,
    damit Streamlit den Vector Store neu baut, wenn sich Quellen oder
    Embedding-Konfiguration ändern.
    """
    knowledge_loader = import_version_module(version, "knowledge_loader")
    chunking = import_version_module(version, "chunking.structure_chunking")
    retrieval = import_version_module(version, "retrieval")

    documents = knowledge_loader.load_knowledge_base(Path(knowledge_base_path))
    chunks = chunking.create_chunks(documents)

    return retrieval.build_vector_store(chunks)


def empty_webapp_result(version: str, inquiry_text: str) -> dict[str, Any]:
    model_metadata = active_model_metadata()

    return {
        "case_id": None,
        "version": version,
        "timestamp": None,
        "text": inquiry_text,
        "ground_truth_team": None,
        "predicted_team": None,
        "predicted_department": None,
        "predicted_department_name": None,
        "matched_subteam": None,
        "matched_subteam_name": None,
        "matched_subteam_confidence": None,
        "matched_team": None,
        "matched_team_name": None,
        "matched_team_confidence": None,
        "top3": [],
        "top1_correct": None,
        "top3_correct": None,
        "confidence": None,
        "calibrated_confidence": None,
        "reason": None,
        "target_team": None,
        "target_department": None,
        "target_department_name": None,
        "target_email": None,
        "routing_status": None,
        "draft_answer": "",
        "retrieved_sources": [],
        "retrieved_chunks": [],
        "retrieved_chunk_ids": [],
        "used_sources": [],
        "used_source_ids": [],
        "used_source_details": [],
        "invalid_source_ids": [],
        "used_chunk_ids": [],
        "has_retrieved_sources": False,
        "has_used_sources": False,
        "answer_completeness_llm_provider": None,
        "answer_completeness_llm_model": None,
        "answer_completeness_temperature": None,
        "answer_completeness_score": None,
        "answer_completeness_label": None,
        "answer_completeness_reason": None,
        "covered_aspects": [],
        "missing_aspects": [],
        "uncertain_aspects": [],
        "requires_human_completion": None,
        "response_mode": None,
        "workflow_status": None,
        "risk_score": None,
        "risk_reasons": [],
        "policy_allows_generation": None,
        "escalation_required": None,
        "human_review_required": None,
        "human_review_reasons": [],
        "injection_detected": None,
        "injection_patterns": [],
        "injection_reasoning": None,
        "no_answer_triggered": None,
        "guardrail_triggered": None,
        "guardrail_flags": [],
        "self_evaluation_passed": None,
        "self_evaluation_issues": [],
        "retrieval_expanded": None,
        "retrieval_reasons": [],
        "retrieval_k": None,
        "reflection_triggered": None,
        "reflections": [],
        "processing_time_seconds": None,
        "processing_time_ms": None,
        "step_timings": {},
        "status": "ok",
        "error": None,
        **model_metadata,
    }


def pipeline_function_for(version: str):
    spec = version_spec_for(version)
    module = importlib.import_module(spec["api_module"])

    return getattr(module, spec["api_function"])


def pipeline_kwargs_for(version: str, inquiry_text: str) -> dict[str, Any]:
    """
    Baut die Argumente für den dynamisch geladenen Pipeline-Aufruf.

    Konfiguration und Vector Store werden hier versionsabhängig aufgelöst. Für
    v5 wird zusätzlich der Audit-Pfad gesetzt, weil die Web- und Operations-Apps
    dort denselben datensparsamen Audit-Mechanismus wie Batch-Läufe nutzen.
    """
    normalized_version = normalize_version(version)
    spec = version_spec_for(normalized_version)
    config_path = municipality_config_path_for_version(normalized_version)

    config = get_config_cached(
        str(config_path),
        path_mtime(config_path),
    )

    kwargs = {
        "inquiry_text": inquiry_text,
        "config": config,
    }

    if spec["uses_vector_store"]:
        knowledge_base_path = knowledge_base_path_for_version(normalized_version)
        model_metadata = active_model_metadata()
        kwargs["vector_store"] = get_vector_store_cached(
            normalized_version,
            str(knowledge_base_path),
            knowledge_base_fingerprint(knowledge_base_path),
            model_metadata.get("retrieval_embedding_provider", ""),
            model_metadata.get("retrieval_embedding_model", ""),
        )

    if normalized_version == "V5":
        V5_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        kwargs["audit_log_path"] = V5_OUTPUT_DIR / FILENAME_AUDIT_LOG_JSONL
    
    return kwargs


def normalize_pipeline_result(
        version: str,
        inquiry_text: str,
        pipeline_result: dict[str, Any],
        elapsed_seconds: float
) -> dict[str, Any]:
    normalized_version = normalize_version(version)
    result = empty_webapp_result(normalized_version, inquiry_text)
    result.update(pipeline_result or {})

    result["version"] = normalized_version
    result["status"] = "ok"
    result["error"] = None

    if result.get("processing_time_seconds") is None:
        result["processing_time_seconds"] = round(elapsed_seconds, 4)

    result["processing_time_ms"] = round(
        result["processing_time_seconds"] * 1000,
        2,
    )

    if result.get("step_timings") is None:
        result["step_timings"] = {}

    return result


def build_error_result(
        version: str,
        inquiry_text: str,
        exc: Exception,
        elapsed_seconds: float
) -> dict[str, Any]:
    result = empty_webapp_result(version, inquiry_text)

    result["status"] = "error"
    result["error"] = f"{type(exc).__name__}: {exc}"
    result["draft_answer"] = (
        "Bei der Verarbeitung ist ein Fehler aufgetreten. "
        "Details stehen in den Rohdaten."
    )
    result["processing_time_seconds"] = round(elapsed_seconds, 4)
    result["processing_time_ms"] = round(elapsed_seconds * 1000, 2)

    return result


def run_version(version: str, inquiry_text: str) -> dict[str, Any]:
    normalized_version = normalize_version(version)
    started_at = time.perf_counter()

    try:
        pipeline_result = pipeline_function_for(normalized_version)(
            **pipeline_kwargs_for(normalized_version, inquiry_text)
        )
        elapsed_seconds = time.perf_counter() - started_at

        return normalize_pipeline_result(
            version=normalized_version,
            inquiry_text=inquiry_text,
            pipeline_result=pipeline_result,
            elapsed_seconds=elapsed_seconds,
        )

    except Exception as exc:
        elapsed_seconds = time.perf_counter() - started_at

        return build_error_result(
            version=normalized_version,
            inquiry_text=inquiry_text,
            exc=exc,
            elapsed_seconds=elapsed_seconds,
        )
