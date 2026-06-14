"""API-Orchestrierung der Pipeline v5.

Das Modul verbindet Injection Detection, Klassifikation, Routing, adaptives
Retrieval, Antwortgenerierung, Guardrails, Vollständigkeitsbewertung,
Risikologik, Workflow-Ableitung und Audit-Wrapper zu einem reproduzierbaren
Pipeline-Ergebnis.
"""

import re
import time
from pathlib import Path

import unicodedata
from datetime import datetime
from typing import Any

from prototype.shared.api_logging import (
    log_pipeline_complete,
    log_pipeline_event,
    log_pipeline_start,
    log_step_result,
    safe_case_id,
)
from prototype.shared.logging_config import get_logger
from prototype.shared.model_profiles import LLM_STEP_ANSWER_COMPLETENESS, active_llm_step_metadata, active_model_metadata
from src.v5.classifier import classify
from src.v5.logging_audit import log_decision
from src.v5.router import route
from src.v5.answer import generate_answer, append_official_closing
from src.v5.injection_detection import detect_prompt_injection
from src.v5.no_answer import should_trigger_no_answer
from src.v5.guardrails import validate_answer
from src.v5.response_policy import get_response_policy
from src.v5.risk_aware_answer import generate_policy_answer
from src.v5.workflow import determine_workflow_status
from src.v5.adaptive_retrieval import retrieve_adaptively
from src.v5.self_evaluation import build_quality_diagnostic
from src.v5.reflection import generate_reflection
from src.v5.confidence_calibration import calibrate_confidence
from src.v5.answer_completeness import evaluate_answer_completeness
from src.v5.evaluation import evaluate_comprehensive_risk
from src.v5.core.response_messages import (
    REASON_SECURITY_BLOCK,
)
from src.v5.core.constants import (
    K_ALLOW_GENERATION,
    K_ANSWER,
    K_CALIBRATED_CONFIDENCE,
    K_CASE_ID,
    K_CATEGORY,
    K_CHUNK_ID,
    K_COMPLETENESS_LABEL,
    K_COMPLETENESS_REASON,
    K_COMPLETENESS_SCORE,
    K_CONFIDENCE,
    K_COVERED_ASPECTS,
    K_DEPARTMENT,
    K_DESCRIPTION,
    K_DETECTED,
    K_DISPLAY_NAME,
    K_DISTANCE,
    K_DRAFT_ANSWER,
    K_ESCALATION_REQUIRED,
    K_FILENAME,
    K_FLAGS,
    K_GROUND_TRUTH_TEAM,
    K_GUARDRAIL_FLAGS,
    K_GUARDRAIL_TRIGGERED,
    K_HAS_RETRIEVED_SOURCES,
    K_HAS_USED_SOURCES,
    K_HUMAN_REQUIRED,
    K_HUMAN_REVIEW_REASONS,
    K_HUMAN_REVIEW_REQUIRED,
    K_INJECTION_DETECTED,
    K_INJECTION_PATTERNS,
    K_INJECTION_REASONING,
    K_INVALID_SOURCE_IDS,
    K_ISSUES,
    K_MATCHED_PATTERNS,
    K_MATCHED_SUBTEAM,
    K_MATCHED_SUBTEAM_CONFIDENCE,
    K_MATCHED_SUBTEAM_NAME,
    K_MATCHED_TEAM,
    K_MATCHED_TEAM_CONFIDENCE,
    K_MATCHED_TEAM_NAME,
    K_MISSING_ASPECTS,
    K_NAME,
    K_NO_ANSWER_TRIGGERED,
    K_PASSED,
    K_POLICY_ALLOWS_GENERATION,
    K_PREDICTED_DEPARTMENT,
    K_PREDICTED_DEPARTMENT_NAME,
    K_PREDICTED_TEAM,
    K_PROCESSING_TIME,
    K_REASON,
    K_REASONING,
    K_REASONS,
    K_REQUIRED,
    K_RESPONSE_MODE,
    K_RETRIEVAL_EXPANDED,
    K_RETRIEVAL_K,
    K_RETRIEVAL_REASONS,
    K_RETRIEVED_CHUNK_IDS,
    K_RETRIEVED_CHUNKS,
    K_RETRIEVED_SOURCES,
    K_REFLECTIONS,
    K_REFLECTION_TRIGGERED,
    K_RISK_REASONS,
    K_RISK_SCORE,
    K_ROUTING_STATUS,
    K_SCORE,
    K_SECTION_TITLE,
    K_SELF_EVAL_ISSUES,
    K_SELF_EVAL_PASSED,
    K_SERVICES,
    K_SOURCES,
    K_SOURCE,
    K_SOURCE_ID,
    K_STEP_TIMINGS,
    K_TARGET_DEPARTMENT,
    K_TARGET_DEPARTMENT_NAME,
    K_TARGET_EMAIL,
    K_TARGET_TEAM,
    K_TEXT,
    K_TIMESTAMP,
    K_TITLE,
    K_TOP1_CORRECT,
    K_TOP3,
    K_TOP3_CORRECT,
    K_TOP_TEAM,
    K_UNCERTAIN_ASPECTS,
    K_USED_CHUNK_IDS,
    K_USED_CHUNKS,
    K_USED_SOURCE_DETAILS,
    K_USED_SOURCE_IDS,
    K_USED_SOURCES,
    K_VERSION,
    K_WORKFLOW_STATUS,
    MODE_BLOCKED,
    MODE_NO_ANSWER,
    PIPELINE_VERSION_V5,
    T_CLASSIFICATION,
    T_COMPLETENESS,
    T_EVALUATION,
    T_GENERATION,
    T_INJECTION,
    T_RETRIEVAL,
    T_ROUTING,
    V_MANUAL_REVIEW,
    V_UNKNOWN,
)

from src.v5.municipality_structure import (
    collect_department_keywords,
    collect_department_services,
    department_knowledge_categories,
    find_division,
    find_team,
    get_department,
    get_department_display_name,
)


logger = get_logger(__name__)


def _answer_completeness_metadata(answer_completeness: dict[str, Any]) -> dict[str, str]:
    metadata = active_llm_step_metadata(LLM_STEP_ANSWER_COMPLETENESS)
    return {
        "answer_completeness_llm_provider": str(
            answer_completeness.get("answer_completeness_llm_provider", metadata.get("llm_provider", ""))
        ),
        "answer_completeness_llm_model": str(
            answer_completeness.get("answer_completeness_llm_model", metadata.get("llm_model", ""))
        ),
        "answer_completeness_temperature": str(
            answer_completeness.get("answer_completeness_temperature", metadata.get("temperature", ""))
        ),
    }


def _build_used_source_details(used_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Erstellt kompakte Quellenmetadaten für Sachbearbeitung und Evaluation.
    """
    details = []
    seen = set()

    for chunk in used_chunks:
        if not isinstance(chunk, dict):
            continue

        key = (
            chunk.get(K_SOURCE_ID),
            chunk.get(K_CHUNK_ID),
            chunk.get(K_SOURCE),
        )

        if key in seen:
            continue

        seen.add(key)
        details.append({
            K_SOURCE_ID: chunk.get(K_SOURCE_ID),
            K_SOURCE: chunk.get(K_SOURCE),
            K_CATEGORY: chunk.get(K_CATEGORY),
            K_TITLE: chunk.get(K_TITLE),
            K_SECTION_TITLE: chunk.get(K_SECTION_TITLE),
            K_FILENAME: chunk.get(K_FILENAME),
            K_CHUNK_ID: chunk.get(K_CHUNK_ID),
        })

    return details


def select_answer_chunks_for_target_team(
        retrieved_chunks: list[dict[str, Any]],
        target_team: str | None,
        config: dict[str, Any] | None = None,
        matched_division: str | None = None,
) -> list[dict[str, Any]]:
    if target_team in [None, "", V_UNKNOWN]:
        team_chunks = retrieved_chunks
    else:
        allowed_categories = set()
        if matched_division:
            allowed_categories.add(str(matched_division))

        if config is not None:
            department = get_department(config, target_team)
            if department:
                allowed_categories.update(department_knowledge_categories(department))

        if not allowed_categories:
            allowed_categories.add(str(target_team))

        team_chunks = [
            chunk
            for chunk in retrieved_chunks
            if isinstance(chunk, dict) and chunk.get(K_CATEGORY) in allowed_categories
        ]

    return prioritize_answer_chunks(team_chunks)


def prioritize_answer_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sortiert Retrieval-Treffer für die Antwortgenerierung nach fachlicher Nutzbarkeit.
    Beispiel- und Zweckabschnitte sind für Routing hilfreich, sollen aber fachliche
    Antwortentwürfe nicht dominieren.
    """
    if not chunks:
        return chunks

    def section_priority(chunk: dict[str, Any]) -> int:
        section = str(chunk.get(K_SECTION_TITLE) or "").lower()
        section_ascii = unicodedata.normalize("NFKD", section).encode("ascii", "ignore").decode("ascii")

        if "beispielhafte" in section and "rgeranliegen" in section:
            return 30

        if "zweck des dokuments" in section:
            return 25

        if "hinweise fur rag" in section_ascii:
            return 20

        if "hilfreiche angaben" in section or "unterlagen" in section:
            return 0

        if "formelle antragstellung" in section or "onlinezugang" in section:
            return 1

        if "antwortlogik" in section_ascii:
            return 2

        if "zustandigkeit" in section_ascii or "bearbeitungsablauf" in section:
            return 3

        if section == "dokument":
            return 4

        return 10

    return sorted(
        chunks,
        key=lambda chunk: (
            section_priority(chunk),
            float(chunk.get(K_DISTANCE, 9999)),
        )
    )


def normalize_for_query_match(value: Any) -> str:
    text = str(value or "").lower()
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def extract_question_focus(inquiry_text: str, max_parts: int = 3) -> list[str]:
    """
    Extrahiert explizite Fragen oder handlungsleitende Sätze für eine fokussierte
    Retrieval-Query. Lange Bürgertexte enthalten oft Kontext, der die Vektorsuche
    unnötig verwässert.
    """
    text = " ".join(str(inquiry_text or "").replace("\r", "\n").split())
    if not text:
        return []

    parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", text)
        if part.strip()
    ]
    explicit_questions = [part for part in parts if part.rstrip().endswith("?")]

    if explicit_questions:
        return explicit_questions[:max_parts]

    focus_parts = []
    question_words = {
        "welche",
        "was",
        "wie",
        "wo",
        "wann",
        "wer",
    }
    information_need_markers = [
        "benötige",
        "benotige",
        "brauche",
        "erforderlich",
        "unterlagen",
    ]
    secondary_markers = [
        "beantragen",
        "anmelden",
        "melden",
    ]

    for part in parts:
        normalized = normalize_for_query_match(part)
        words = set(re.findall(r"[a-z0-9]+", normalized))
        if words.intersection(question_words) or any(marker in normalized for marker in information_need_markers):
            focus_parts.append(part)

        if len(focus_parts) >= max_parts:
            break

    if focus_parts:
        return focus_parts

    for part in parts:
        normalized = normalize_for_query_match(part)
        if any(marker in normalized for marker in secondary_markers):
            focus_parts.append(part)

        if len(focus_parts) >= max_parts:
            break

    return focus_parts


def build_focused_retrieval_query(
        inquiry_text: str,
        config: dict[str, Any],
        target_team: str | None,
) -> str:
    """
    Baut eine stabilere Retrieval-Query für lange Bürgeranliegen.

    Der Originaltext bleibt für Klassifikation, Antwortgenerierung und Audit erhalten.
    Nur die Suche wird um die fachlich wahrscheinlichsten Servicebegriffe und expliziten
    Bürgerfragen fokussiert.
    """
    inquiry = str(inquiry_text or "").strip()

    if not target_team or target_team == V_UNKNOWN:
        return inquiry

    department = get_department(config, target_team) or {}
    terms = collect_department_services(department) + collect_department_keywords(department)
    normalized_inquiry = normalize_for_query_match(inquiry)
    matched_terms = []

    for term in terms:
        normalized_term = normalize_for_query_match(term)
        if normalized_term and normalized_term in normalized_inquiry and term not in matched_terms:
            matched_terms.append(str(term))

    focus_parts = extract_question_focus(inquiry)

    query_parts = [
        f"Zielfachbereich: {target_team}",
    ]

    if matched_terms:
        query_parts.append("Passende Leistungen und Suchbegriffe: " + ", ".join(matched_terms[:8]))

    if focus_parts:
        query_parts.append("Explizite Bürgerfragen: " + " ".join(focus_parts))

    query_parts.append("Originalanliegen: " + inquiry)

    return "\n".join(query_parts)


def get_answer_role_for_team(
        config: dict[str, Any],
        target_team: str | None,
        matched_subteam: str | None = None,
        matched_team: str | None = None,
) -> str:
    if not target_team or target_team == V_UNKNOWN:
        return ""

    department_config = get_department(config, target_team) or {}
    role = department_config.get("answer_role") or department_config.get("role_description")

    role_text = str(role).strip() if role else ""

    department_name = department_config.get(K_NAME) or target_team
    department_group = department_config.get("department_group_name") or "zuständiges Dezernat"
    description = department_config.get(K_DESCRIPTION) or ""

    if not role_text:
        role_text = (
            f"Du antwortest als sachbearbeitende Person im Fachbereich {department_name} "
            f"({department_group}). {description} Bleibe bei dieser Zuständigkeit und "
            "verweise bei fachfremden Punkten auf eine Prüfung durch den zuständigen Fachbereich."
        ).strip()

    division_config = find_division(department_config, matched_subteam) or {}

    if division_config:
        division_role = division_config.get("answer_role")
        division_name = division_config.get(K_NAME) or matched_subteam
        division_description = division_config.get(K_DESCRIPTION) or ""
        if division_role:
            role_text = f"{role_text}\n{str(division_role).strip()}".strip()
        else:
            role_text = (
                f"{role_text}\n"
                f"Innerhalb dieses Fachbereichs ist besonders der Bereich {division_name} relevant. "
                f"{division_description}"
            ).strip()

        team_config = find_team(department_config, matched_subteam, matched_team) or {}
        if team_config:
            team_role = team_config.get("answer_role")
            team_name = team_config.get(K_NAME) or matched_team
            team_description = team_config.get(K_DESCRIPTION) or ""
            team_services = ", ".join(
                str(service)
                for service in (team_config.get(K_SERVICES) or [])[:6]
            )

            if team_role:
                role_text = f"{role_text}\n{str(team_role).strip()}".strip()
            else:
                role_text = (
                    f"{role_text}\n"
                    f"Innerhalb dieses Bereichs ist besonders das Team {team_name} relevant. "
                    f"{team_description}"
                ).strip()

            if team_services and not team_role:
                role_text = f"{role_text} Typische Leistungen dieses Teams: {team_services}."

    return role_text


def get_official_closing_notice(config: dict[str, Any] | None) -> str:
    """
    Liest den optionalen allgemeinen Schlusshinweis aus der Kommunal-Konfiguration.

    Kommunale Links und Antragshinweise bleiben damit in YAML statt im Code.
    Fehlt der Eintrag, wird kein zusätzlicher Hinweis angehängt.
    """
    answer_templates = (config or {}).get("answer_templates") or {}
    return str(answer_templates.get("official_closing_notice") or "").strip()


def _append_official_closing_if_allowed(
    generated: dict[str, Any],
    response_policy: dict[str, Any],
    routing: dict[str, Any],
    classification: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Fügt der generierten Antwort eine offizielle Schlussformel hinzu, falls dies gemäß der
    vorgegebenen Antwortpolitik erlaubt ist.

    Diese Funktion prüft anhand der Parameter `response_policy` und `generated`, ob eine
    offizielle Schlussformel angehängt werden darf. Ist dies erlaubt, wird die Schlussformel
    mit einem optionalen Fachbereichs- bzw. Teamnamen aus `routing` ergänzt und an die
    Antwort angehängt. Der allgemeine Antragshinweis wird aus der Konfiguration gelesen.

    :param generated: Enthält die generierten Daten, einschließlich der aktuellen Antwort
        unter dem Schlüssel `K_ANSWER`.
    :param response_policy: Enthält die Richtlinien zur Generierung von Antworten, wobei
        der Schlüssel `K_ALLOW_GENERATION` die Erlaubnis signalisiert.
    :param routing: Liefert Routing-Informationen, wie z. B. den Anzeigenamen oder das Zielteam,
        um einen Teamnamen für die Schlussformel hinzuzufügen.
    :return: Gibt ein modifiziertes `dict` zurück, welches die generierte Antwort mit einer
        optionalen Schlussformel enthält; bleibt unverändert, wenn keine Schlussformel
        angehängt wurde.
    """
    if not response_policy.get(K_ALLOW_GENERATION) or not generated.get(K_ANSWER):
        return generated

    team_name = routing.get(K_DISPLAY_NAME) or routing.get(K_TARGET_TEAM)
    classification = classification or {}
    subteam_name = classification.get(K_MATCHED_TEAM_NAME)
    if not subteam_name or subteam_name == V_UNKNOWN:
        subteam_name = classification.get(K_MATCHED_SUBTEAM_NAME)

    generated = dict(generated)
    generated[K_ANSWER] = append_official_closing(
        generated[K_ANSWER],
        team_name=team_name,
        subteam_name=subteam_name,
        application_notice=get_official_closing_notice(config)
    )

    return generated


def _build_injection_blocked_result(
        inquiry_text: str,
        injection_result: dict[str, Any],
        step_timings: dict[str, float],
        start_time: float,
        row_metadata: dict[str, Any] = None
) -> dict[str, Any]:
    """
    Erstellt ein Ergebnis-Dictionary für Anfragen, bei denen eine Injectionsicherheitsmaßnahme
    ausgelöst wurde. Dieses Ergebnis enthält detaillierte Informationen zur Klassifizierung,
    den verwendeten Quellen, Antwortgenerierung, Risikobewertung, Komplettheitsbewertung und
    weiteren relevanten Metadaten.

    :param inquiry_text: Der Text der ursprünglichen Anfrage, der verarbeitet wurde.
    :param injection_result: Ein Dictionary mit Informationen zu erkannten Injections und
        deren Begründungen.
    :param step_timings: Ein Dictionary mit Timings der einzelnen Verarbeitungsschritte. Die
        Keys entsprechen spezifischen Schritten der Pipeline, und die Werte sind Zeitangaben
        in Sekunden.
    :param start_time: Der Zeitstempel (Unix-Zeit) des Beginns der Anfrageverarbeitung.
    :param row_metadata: Metadaten zur aktuellen Zeile im Verarbeitungsprozess, falls vorhanden.
        Kann Informationen wie `K_CASE_ID` oder `K_GROUND_TRUTH_TEAM` enthalten.
    :return: Ein Dictionary, das alle relevanten Informationen zur Anfrageverarbeitung,
        Sicherheitsmaßnahmen, Klassifikationsergebnissen, Quellen- und Routeninformationen sowie
        Evaluations- und Risikometriken enthält.
    """
    response_mode = MODE_BLOCKED
    response_policy = get_response_policy(response_mode)
    generated = generate_policy_answer(response_mode)

    classification = {
        K_TOP_TEAM: V_UNKNOWN,
        K_TOP3: [],
        K_CONFIDENCE: 0.0,
        K_MATCHED_SUBTEAM: None,
        K_MATCHED_SUBTEAM_NAME: None,
        K_MATCHED_SUBTEAM_CONFIDENCE: None,
        K_MATCHED_TEAM: None,
        K_MATCHED_TEAM_NAME: None,
        K_MATCHED_TEAM_CONFIDENCE: None,
        K_REASON: REASON_SECURITY_BLOCK.format(
            reason=injection_result.get(K_REASONING, "")
        )
    }

    retrieved_chunks = []
    used_sources = []
    used_chunks = []
    retrieved_sources = []
    no_answer_triggered = False
    guardrail_result = {K_FLAGS: []}

    answer_completeness = evaluate_answer_completeness(
        inquiry_text=inquiry_text,
        draft_answer=generated.get(K_ANSWER, ""),
        used_chunks=used_chunks,
        used_sources=used_sources,
        result_context={
            K_INJECTION_DETECTED: True,
            K_INJECTION_REASONING: injection_result.get(K_REASONING, ""),
            K_RESPONSE_MODE: response_mode,
            K_NO_ANSWER_TRIGGERED: no_answer_triggered
        }
    )

    risk_result = evaluate_comprehensive_risk(
        inquiry_text,
        classification,
        injection_result,
        guardrail_result,
        no_answer_triggered,
        answer_completeness=answer_completeness
    )

    self_evaluation_result = build_quality_diagnostic(
        guardrail_result,
        retrieved_sources,
        used_sources,
        response_mode
    )

    workflow_status = determine_workflow_status(response_mode, response_policy)
    pipeline_total_time = round(time.perf_counter() - start_time, 4)

    for timing_key in [
        T_CLASSIFICATION,
        T_ROUTING,
        T_RETRIEVAL,
        T_GENERATION,
        T_EVALUATION,
        T_COMPLETENESS
    ]:
        step_timings.setdefault(timing_key, 0.0)

    result = {
        K_CASE_ID: row_metadata.get(K_CASE_ID) if row_metadata is not None else None,
        K_TEXT: inquiry_text,
        K_GROUND_TRUTH_TEAM: row_metadata.get(K_GROUND_TRUTH_TEAM) if row_metadata is not None else None,

        K_PREDICTED_TEAM: classification[K_TOP_TEAM],
        K_PREDICTED_DEPARTMENT: classification[K_TOP_TEAM],
        K_PREDICTED_DEPARTMENT_NAME: get_department_display_name({}, classification[K_TOP_TEAM]) or classification[K_TOP_TEAM],
        K_TOP3: classification[K_TOP3],
        K_CONFIDENCE: classification[K_CONFIDENCE],
        K_CALIBRATED_CONFIDENCE: 0.0,
        K_MATCHED_SUBTEAM: classification.get(K_MATCHED_SUBTEAM),
        K_MATCHED_SUBTEAM_NAME: classification.get(K_MATCHED_SUBTEAM_NAME),
        K_MATCHED_SUBTEAM_CONFIDENCE: classification.get(K_MATCHED_SUBTEAM_CONFIDENCE),
        K_MATCHED_TEAM: classification.get(K_MATCHED_TEAM),
        K_MATCHED_TEAM_NAME: classification.get(K_MATCHED_TEAM_NAME),
        K_MATCHED_TEAM_CONFIDENCE: classification.get(K_MATCHED_TEAM_CONFIDENCE),
        K_REASON: classification[K_REASON],

        K_TARGET_TEAM: V_UNKNOWN,
        K_TARGET_DEPARTMENT: V_UNKNOWN,
        K_TARGET_DEPARTMENT_NAME: V_UNKNOWN,
        K_TARGET_EMAIL: None,
        K_ROUTING_STATUS: V_MANUAL_REVIEW,

        K_RETRIEVED_SOURCES: retrieved_sources,
        K_RETRIEVED_CHUNKS: retrieved_chunks,
        K_RETRIEVED_CHUNK_IDS: [],
        K_USED_SOURCES: used_sources,
        K_USED_SOURCE_IDS: generated.get(K_USED_SOURCE_IDS, []),
        K_USED_SOURCE_DETAILS: [],
        K_INVALID_SOURCE_IDS: generated.get(K_INVALID_SOURCE_IDS, []),
        K_USED_CHUNK_IDS: [],
        K_HAS_RETRIEVED_SOURCES: False,
        K_HAS_USED_SOURCES: False,

        K_RETRIEVAL_EXPANDED: False,
        K_RETRIEVAL_REASONS: [],
        K_RETRIEVAL_K: 0,

        K_DRAFT_ANSWER: generated[K_ANSWER],

        **_answer_completeness_metadata(answer_completeness),
        K_COMPLETENESS_SCORE: answer_completeness.get(K_COMPLETENESS_SCORE),
        K_COMPLETENESS_LABEL: answer_completeness.get(K_COMPLETENESS_LABEL),
        K_COMPLETENESS_REASON: answer_completeness.get(K_COMPLETENESS_REASON),
        K_COVERED_ASPECTS: answer_completeness.get(K_COVERED_ASPECTS, []),
        K_MISSING_ASPECTS: answer_completeness.get(K_MISSING_ASPECTS, []),
        K_UNCERTAIN_ASPECTS: answer_completeness.get(K_UNCERTAIN_ASPECTS, []),
        K_HUMAN_REQUIRED: answer_completeness.get(K_HUMAN_REQUIRED),

        K_INJECTION_DETECTED: injection_result[K_DETECTED],
        K_INJECTION_REASONING: injection_result.get(K_REASONING, ""),
        K_INJECTION_PATTERNS: injection_result[K_MATCHED_PATTERNS],

        K_NO_ANSWER_TRIGGERED: no_answer_triggered,

        K_GUARDRAIL_TRIGGERED: False,
        K_GUARDRAIL_FLAGS: guardrail_result[K_FLAGS],

        K_RISK_SCORE: risk_result[K_SCORE],
        K_RISK_REASONS: risk_result[K_REASONS],

        K_RESPONSE_MODE: response_mode,
        K_POLICY_ALLOWS_GENERATION: response_policy[K_ALLOW_GENERATION],
        K_ESCALATION_REQUIRED: response_policy[K_ESCALATION_REQUIRED],

        K_HUMAN_REVIEW_REQUIRED: True,
        K_HUMAN_REVIEW_REASONS: risk_result[K_REASONS],

        K_WORKFLOW_STATUS: workflow_status,

        K_SELF_EVAL_PASSED: self_evaluation_result[K_PASSED],
        K_SELF_EVAL_ISSUES: self_evaluation_result[K_ISSUES],

        K_REFLECTION_TRIGGERED: False,
        K_REFLECTIONS: [],

        K_STEP_TIMINGS: step_timings,
        K_PROCESSING_TIME: pipeline_total_time,
        K_VERSION: PIPELINE_VERSION_V5,
        K_TIMESTAMP: datetime.now().isoformat(),
        **active_model_metadata(),
    }

    if row_metadata is not None and K_GROUND_TRUTH_TEAM in row_metadata:
        result[K_TOP1_CORRECT] = False
        result[K_TOP3_CORRECT] = False

    return result


def run_v5_pipeline(
    inquiry_text: str,
    config: dict[str, Any],
    vector_store: Any,
    row_metadata: dict[str, Any] = None
) -> dict[str, Any]:
    """
    Führt die V5-Pipeline für die Verarbeitung und Beantwortung einer Anfrage aus. Die Pipeline umfasst
    mehrere Schritte, darunter Injection-Erkennung, Klassifikation, Routing, Retrieval, Generierung und Evaluation.
    Ziel ist es, eine qualitativ hochwertige Antwort zu erstellen, die durch Guardrails und Evaluationslogik abgesichert ist.

    :param inquiry_text: Der Text der Anfrage, die verarbeitet werden soll.
    :param config: Die Pipeline-Konfiguration, die Einstellungen für Klassifikation, Routing und Generierung enthält.
    :param vector_store: Ein externer Speicher für Vektordaten, der für Retrievals verwendet wird.
    :param row_metadata: Optionale Metadaten zur Anfrage, einschließlich case_id und anderer Informationen.
    :return: Ein `dict[str, Any]`, das das Ergebnis der Pipeline mit der generierten Antwort und zusätzlichen Metadaten zurückgibt.
    """
    step_timings = {}
    case_id = safe_case_id(row_metadata, K_CASE_ID)

    log_pipeline_start(logger, version=PIPELINE_VERSION_V5, case_id=case_id)
    
    # 1. Injection Detection
    t0 = time.perf_counter()
    injection_result = detect_prompt_injection(inquiry_text)

    t1 = time.perf_counter()
    step_timings[T_INJECTION] = round(t1 - t0, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        step=T_INJECTION,
        duration=step_timings[T_INJECTION],
        injection_detected=injection_result[K_DETECTED],
        confidence=injection_result.get(K_CONFIDENCE),
        matched_patterns_count=len(injection_result[K_MATCHED_PATTERNS]),
    )

    if injection_result[K_DETECTED]:
        blocked_result = _build_injection_blocked_result(
            inquiry_text=inquiry_text,
            injection_result=injection_result,
            step_timings=step_timings,
            start_time=t0,
            row_metadata=row_metadata
        )
        log_pipeline_event(
            logger,
            version=PIPELINE_VERSION_V5,
            case_id=case_id,
            event="security_block",
            step=T_INJECTION,
            injection_detected=True,
            response_mode=blocked_result[K_RESPONSE_MODE],
            risk_score=blocked_result[K_RISK_SCORE],
            terminated_early=True,
            termination_reason="prompt_injection",
        )
        log_pipeline_complete(
            logger,
            version=PIPELINE_VERSION_V5,
            case_id=case_id,
            duration=blocked_result[K_PROCESSING_TIME],
            predicted_team=blocked_result[K_PREDICTED_TEAM],
            target_team=blocked_result[K_TARGET_TEAM],
            routing_status=blocked_result[K_ROUTING_STATUS],
            injection_detected=True,
            no_answer_triggered=blocked_result[K_NO_ANSWER_TRIGGERED],
            response_mode=blocked_result[K_RESPONSE_MODE],
            risk_score=blocked_result[K_RISK_SCORE],
            human_review_required=blocked_result[K_HUMAN_REVIEW_REQUIRED],
            workflow_status=blocked_result[K_WORKFLOW_STATUS],
            terminated_early=True,
            termination_reason="prompt_injection",
            retrieval_expanded=False,
        )
        return blocked_result

    # 2. Klassifikation
    classification = classify(inquiry_text, config)

    t2 = time.perf_counter()
    step_timings[T_CLASSIFICATION] = round(t2 - t1, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        step=T_CLASSIFICATION,
        duration=step_timings[T_CLASSIFICATION],
        predicted_team=classification[K_TOP_TEAM],
        confidence=classification[K_CONFIDENCE],
        top3_count=len(classification[K_TOP3]),
    )

    # 3. Routing
    routing = route(classification, config)
    t3 = time.perf_counter()
    step_timings[T_ROUTING] = round(t3 - t2, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        step=T_ROUTING,
        duration=step_timings[T_ROUTING],
        target_team=routing[K_TARGET_TEAM],
        routing_status=routing[K_ROUTING_STATUS],
    )

    # 4. Retrieval
    retrieval_query = build_focused_retrieval_query(
        inquiry_text=inquiry_text,
        config=config,
        target_team=routing.get(K_TARGET_TEAM),
    )
    retrieval_result = retrieve_adaptively(
        vector_store,
        retrieval_query,
        classification,
        initial_k=6,
        expanded_k=10
    )
    retrieved_chunks = retrieval_result[K_RETRIEVED_CHUNKS]
    retrieved_sources = list({chunk[K_SOURCE] for chunk in retrieved_chunks})
    answer_chunks = select_answer_chunks_for_target_team(
        retrieved_chunks,
        routing.get(K_TARGET_TEAM),
        config=config,
        matched_division=classification.get(K_MATCHED_SUBTEAM),
    )
    team_answer_role = get_answer_role_for_team(
        config,
        routing.get(K_TARGET_TEAM),
        classification.get(K_MATCHED_SUBTEAM),
        classification.get(K_MATCHED_TEAM),
    )

    no_answer_triggered = should_trigger_no_answer(answer_chunks, classification)
    t4 = time.perf_counter()
    step_timings[T_RETRIEVAL] = round(t4 - t3, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        step=T_RETRIEVAL,
        duration=step_timings[T_RETRIEVAL],
        retrieved_chunks=len(retrieved_chunks),
        retrieved_sources_count=len(retrieved_sources),
        retrieval_k=retrieval_result[K_RETRIEVAL_K],
        retrieval_expanded=retrieval_result[K_RETRIEVAL_EXPANDED],
        retrieval_reasons_count=len(retrieval_result[K_RETRIEVAL_REASONS]),
        no_answer_triggered=no_answer_triggered,
    )

    # 5. Answer Generation
    if no_answer_triggered:
        response_mode = MODE_NO_ANSWER
        response_policy = get_response_policy(response_mode)
        policy_res = generate_policy_answer(response_mode)
        if isinstance(policy_res, str):
            generated = {K_ANSWER: policy_res, K_SOURCES: []}
        else:
            generated = policy_res
    else:
        initial_generated = generate_answer(
            inquiry_text,
            answer_chunks,
            team_role=team_answer_role,
        )
        
        # Guardrails und Risiko für initiale Antwort (gehört hier zur Generierungsschleife)
        initial_used_sources = initial_generated[K_SOURCES]
        initial_guardrail_result = validate_answer(
            initial_generated[K_ANSWER], 
            initial_used_sources,
            invalid_source_ids=initial_generated.get(K_INVALID_SOURCE_IDS, [])
        )
        eval_initial = evaluate_comprehensive_risk(
            inquiry_text, classification, injection_result, 
            initial_guardrail_result, no_answer_triggered
        )
        
        response_mode = eval_initial[K_RESPONSE_MODE]
        response_policy = get_response_policy(response_mode)
        
        policy_answer_res = generate_policy_answer(response_mode)
        if policy_answer_res is not None:
            if isinstance(policy_answer_res, str):
                generated = {K_ANSWER: policy_answer_res, K_SOURCES: []}
            else:
                generated = policy_answer_res
        else:
            generated = initial_generated

    # Finale Quellen-Extraktion gehört ebenfalls zur Answer Generation
    used_sources = generated.get(K_SOURCES, [])
    used_chunks = generated.get(K_USED_CHUNKS, [])


    if not isinstance(used_sources, list):
        used_sources = []

    if not isinstance(used_chunks, list):
        used_chunks = []


    t5 = time.perf_counter()
    step_timings[T_GENERATION] = round(t5 - t4, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        step=T_GENERATION,
        duration=step_timings[T_GENERATION],
        used_sources_count=len(used_sources),
        used_chunks_count=len(used_chunks),
        response_mode=response_mode,
        policy_allows_generation=response_policy[K_ALLOW_GENERATION],
    )

    # 6. Evaluation & Self-Evaluation Loop
    guardrail_result = validate_answer(
        generated[K_ANSWER],
        used_sources,
        invalid_source_ids=generated.get(K_INVALID_SOURCE_IDS, [])
    )

    self_evaluation_result = build_quality_diagnostic(
        guardrail_result,
        retrieved_sources,
        used_sources,
        response_mode
    )

    # Adaptive Retrieval Loop: Falls Self-Evaluation fehlschlägt, wird Expansion versucht
    if not self_evaluation_result[K_PASSED] and not injection_result[K_DETECTED] and not no_answer_triggered:
        retrieval_result_v2 = retrieve_adaptively(
            vector_store,
            retrieval_query,
            classification,
            self_evaluation_result=self_evaluation_result,
            initial_chunks=retrieved_chunks,
            initial_k=6,
            expanded_k=10
        )
        
        if retrieval_result_v2[K_RETRIEVAL_EXPANDED]:
            log_pipeline_event(
                logger,
                version=PIPELINE_VERSION_V5,
                case_id=case_id,
                event="adaptive_retrieval_expanded",
                step=T_RETRIEVAL,
                retrieval_expanded=True,
                retrieval_k=retrieval_result_v2[K_RETRIEVAL_K],
                retrieval_reasons_count=len(retrieval_result_v2[K_RETRIEVAL_REASONS]),
                retrieved_chunks=len(retrieval_result_v2[K_RETRIEVED_CHUNKS]),
            )
            retrieval_result = retrieval_result_v2
            retrieved_chunks = retrieval_result[K_RETRIEVED_CHUNKS]
            retrieved_sources = list({chunk[K_SOURCE] for chunk in retrieved_chunks})
            answer_chunks = select_answer_chunks_for_target_team(
                retrieved_chunks,
                routing.get(K_TARGET_TEAM),
                config=config,
                matched_division=classification.get(K_MATCHED_SUBTEAM),
            )
            
            # Neue Antwort generieren mit erweiterten Chunks
            generated = generate_answer(
                inquiry_text,
                answer_chunks,
                team_role=team_answer_role,
            )
            used_sources = generated.get(K_SOURCES, [])
            used_chunks = generated.get(K_USED_CHUNKS, [])

            guardrail_result = validate_answer(
                generated[K_ANSWER],
                used_sources,
                generated.get(K_INVALID_SOURCE_IDS, []),
            )
            
            # Re-Evaluation der neuen Antwort
            self_evaluation_result = build_quality_diagnostic(
                guardrail_result,
                retrieved_sources,
                used_sources,
                response_mode
            )

    guardrail_result = validate_answer(
        generated[K_ANSWER],
        used_sources,
        generated.get(K_INVALID_SOURCE_IDS, []),
    )
    t6 = time.perf_counter()
    
    # Vollständigkeitsprüfung (wird für die finale Risiko-Bewertung benötigt)
    answer_completeness = evaluate_answer_completeness(
        inquiry_text=inquiry_text,
        draft_answer=generated.get(K_ANSWER, ""),
        used_chunks=used_chunks,
        used_sources=used_sources,
        result_context={
            K_INJECTION_DETECTED: injection_result.get(K_DETECTED, False),
            K_INJECTION_REASONING: injection_result.get(K_REASONING, ""),
            K_RESPONSE_MODE: response_mode,
            K_NO_ANSWER_TRIGGERED: no_answer_triggered
        }
    )
    t7 = time.perf_counter()
    step_timings[T_COMPLETENESS] = round(t7 - t6, 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        step=T_COMPLETENESS,
        duration=step_timings[T_COMPLETENESS],
        completeness_score=answer_completeness.get(K_COMPLETENESS_SCORE),
        completeness_label=answer_completeness.get(K_COMPLETENESS_LABEL),
        missing_aspects_count=len(answer_completeness.get(K_MISSING_ASPECTS, [])),
        requires_human_completion=answer_completeness.get(K_HUMAN_REQUIRED),
    )

    # Zentrale Risiko- und Oversight-Bewertung
    evaluation_result = evaluate_comprehensive_risk(
        inquiry_text, classification, injection_result, 
        guardrail_result, no_answer_triggered,
        answer_completeness=answer_completeness
    )
    
    risk_result = evaluation_result
    response_mode = evaluation_result[K_RESPONSE_MODE]
    response_policy = get_response_policy(response_mode)

    # Korrektur: Falls der Response-Mode nach der Completeness-Prüfung strenger wurde,
    # muss ggf. die Antwort durch eine Policy-Antwort ersetzt werden.
    policy_answer_res_final = generate_policy_answer(response_mode)
    if policy_answer_res_final is not None:
        if isinstance(policy_answer_res_final, str):
            generated = {K_ANSWER: policy_answer_res_final, K_SOURCES: []}
        else:
            generated = policy_answer_res_final

        # Quellen und Chunks für die Policy-Antwort zurücksetzen
        used_sources = generated.get(K_SOURCES, [])
        used_chunks = generated.get(K_USED_CHUNKS, [])

        guardrail_result = validate_answer(
            generated[K_ANSWER],
            used_sources,
            generated.get(K_INVALID_SOURCE_IDS, []),
        )

        # Nach Policy-Antwort Self-Evaluation erneut durchführen
        self_evaluation_result = build_quality_diagnostic(
            guardrail_result,
            retrieved_sources,
            used_sources,
            response_mode
        )

        answer_completeness = evaluate_answer_completeness(
            inquiry_text=inquiry_text,
            draft_answer=generated.get(K_ANSWER, ""),
            used_chunks=used_chunks,
            used_sources=used_sources,
            result_context={
                K_INJECTION_DETECTED: injection_result.get(K_DETECTED, False),
                K_INJECTION_REASONING: injection_result.get(K_REASONING, ""),
                K_RESPONSE_MODE: response_mode,
                K_NO_ANSWER_TRIGGERED: no_answer_triggered
            }
        )
    
    # Oversight-Ergebnis aus der zentralen Evaluation nutzen
    oversight_result = evaluation_result

    human_review_required = response_policy[K_HUMAN_REVIEW_REQUIRED] or oversight_result[K_REQUIRED]
    workflow_status = determine_workflow_status(response_mode, response_policy)

    calibrated_confidence = calibrate_confidence(
        classification[K_CONFIDENCE],
        retrieval_result[K_RETRIEVAL_EXPANDED],
        self_evaluation_result,
        response_mode,
        used_sources,
        answer_completeness=answer_completeness,
        risk_score=risk_result[K_SCORE],
    )

    reflections = generate_reflection(
        classification,
        retrieval_result[K_RETRIEVAL_REASONS],
        self_evaluation_result,
        calibrated_confidence
    )
    t8 = time.perf_counter()
    
    # Evaluation Zeit zusammenfassen
    step_timings[T_EVALUATION] = round((t6 - t5) + (t8 - t7), 4)
    log_step_result(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        step=T_EVALUATION,
        duration=step_timings[T_EVALUATION],
        guardrail_triggered=len(guardrail_result[K_FLAGS]) > 0,
        guardrail_flags_count=len(guardrail_result[K_FLAGS]),
        risk_score=risk_result[K_SCORE],
        risk_reasons_count=len(risk_result[K_REASONS]),
        response_mode=response_mode,
        human_review_required=human_review_required,
        workflow_status=workflow_status,
        self_evaluation_passed=self_evaluation_result[K_PASSED],
        self_evaluation_issues_count=len(self_evaluation_result[K_ISSUES]),
        reflection_triggered=len(reflections) > 0,
        calibrated_confidence=calibrated_confidence,
    )
    
    # Gesamtzeit für Deckungsgleichheit
    pipeline_total_time = round(t8 - t0, 4)

    # 8. Ergebnis zusammenbauen.
    # Die fachlichen Prüfungen laufen auf dem Antwortkörper.
    # Signatur und Transparenzhinweis werden erst für die finale Ausgabe angehängt.
    final_generated = _append_official_closing_if_allowed(
        generated,
        response_policy,
        routing,
        classification,
        config
    )
    model_metadata = active_model_metadata()

    result = {
        K_CASE_ID: row_metadata.get(K_CASE_ID) if row_metadata is not None else None,
        K_TEXT: inquiry_text,
        K_GROUND_TRUTH_TEAM: row_metadata.get(K_GROUND_TRUTH_TEAM) if row_metadata is not None else None,

        K_PREDICTED_TEAM: classification[K_TOP_TEAM],
        K_PREDICTED_DEPARTMENT: classification[K_TOP_TEAM],
        K_PREDICTED_DEPARTMENT_NAME: get_department_display_name(config, classification[K_TOP_TEAM]) or classification[K_TOP_TEAM],
        K_TOP3: classification[K_TOP3],
        K_CONFIDENCE: classification[K_CONFIDENCE],
        K_CALIBRATED_CONFIDENCE: calibrated_confidence,
        K_MATCHED_SUBTEAM: classification.get(K_MATCHED_SUBTEAM),
        K_MATCHED_SUBTEAM_NAME: classification.get(K_MATCHED_SUBTEAM_NAME),
        K_MATCHED_SUBTEAM_CONFIDENCE: classification.get(K_MATCHED_SUBTEAM_CONFIDENCE),
        K_MATCHED_TEAM: classification.get(K_MATCHED_TEAM),
        K_MATCHED_TEAM_NAME: classification.get(K_MATCHED_TEAM_NAME),
        K_MATCHED_TEAM_CONFIDENCE: classification.get(K_MATCHED_TEAM_CONFIDENCE),
        K_REASON: classification[K_REASON],

        K_TARGET_TEAM: routing[K_TARGET_TEAM],
        K_TARGET_DEPARTMENT: routing[K_TARGET_TEAM],
        K_TARGET_DEPARTMENT_NAME: get_department_display_name(config, routing[K_TARGET_TEAM]) or routing[K_TARGET_TEAM],
        K_TARGET_EMAIL: routing[K_TARGET_EMAIL],
        K_ROUTING_STATUS: routing[K_ROUTING_STATUS],

        K_RETRIEVED_SOURCES: retrieved_sources,
        K_RETRIEVED_CHUNKS: retrieved_chunks,
        K_RETRIEVED_CHUNK_IDS: [chunk[K_CHUNK_ID] for chunk in retrieved_chunks],
        K_USED_SOURCES: used_sources,
        K_USED_SOURCE_IDS: final_generated.get(K_USED_SOURCE_IDS, []),
        K_USED_SOURCE_DETAILS: _build_used_source_details(used_chunks),
        K_INVALID_SOURCE_IDS: final_generated.get(K_INVALID_SOURCE_IDS, []),
        K_USED_CHUNK_IDS: [chunk[K_CHUNK_ID] for chunk in used_chunks],
        K_HAS_RETRIEVED_SOURCES: len(retrieved_chunks) > 0,
        K_HAS_USED_SOURCES: len(used_chunks) > 0,

        K_RETRIEVAL_EXPANDED: retrieval_result[K_RETRIEVAL_EXPANDED],
        K_RETRIEVAL_REASONS: retrieval_result[K_RETRIEVAL_REASONS],
        K_RETRIEVAL_K: retrieval_result[K_RETRIEVAL_K],

        K_DRAFT_ANSWER: final_generated[K_ANSWER],

        **_answer_completeness_metadata(answer_completeness),
        K_COMPLETENESS_SCORE: answer_completeness.get(K_COMPLETENESS_SCORE),
        K_COMPLETENESS_LABEL: answer_completeness.get(K_COMPLETENESS_LABEL),
        K_COMPLETENESS_REASON: answer_completeness.get(K_COMPLETENESS_REASON),
        K_COVERED_ASPECTS: answer_completeness.get(K_COVERED_ASPECTS, []),
        K_MISSING_ASPECTS: answer_completeness.get(K_MISSING_ASPECTS, []),
        K_UNCERTAIN_ASPECTS: answer_completeness.get(K_UNCERTAIN_ASPECTS, []),
        K_HUMAN_REQUIRED: answer_completeness.get(K_HUMAN_REQUIRED),

        K_INJECTION_DETECTED: injection_result[K_DETECTED],
        K_INJECTION_REASONING: injection_result.get(K_REASONING, ""),
        K_INJECTION_PATTERNS: injection_result[K_MATCHED_PATTERNS],

        K_NO_ANSWER_TRIGGERED: no_answer_triggered,

        K_GUARDRAIL_TRIGGERED: len(guardrail_result[K_FLAGS]) > 0,
        K_GUARDRAIL_FLAGS: guardrail_result[K_FLAGS],

        K_RISK_SCORE: risk_result[K_SCORE],
        K_RISK_REASONS: risk_result[K_REASONS],

        K_RESPONSE_MODE: response_mode,
        K_POLICY_ALLOWS_GENERATION: response_policy[K_ALLOW_GENERATION],
        K_ESCALATION_REQUIRED: response_policy[K_ESCALATION_REQUIRED],

        K_HUMAN_REVIEW_REQUIRED: human_review_required,
        K_HUMAN_REVIEW_REASONS: oversight_result[K_REASONS],

        K_WORKFLOW_STATUS: workflow_status,

        K_SELF_EVAL_PASSED: self_evaluation_result[K_PASSED],
        K_SELF_EVAL_ISSUES: self_evaluation_result[K_ISSUES],

        K_REFLECTION_TRIGGERED: len(reflections) > 0,
        K_REFLECTIONS: reflections,

        K_STEP_TIMINGS: step_timings,
        K_PROCESSING_TIME: pipeline_total_time,
        K_VERSION: PIPELINE_VERSION_V5,
        K_TIMESTAMP: datetime.now().isoformat(),
        **model_metadata,
    }

    if row_metadata is not None and K_GROUND_TRUTH_TEAM in row_metadata:
        result[K_TOP1_CORRECT] = classification[K_TOP_TEAM] == row_metadata[K_GROUND_TRUTH_TEAM]
        result[K_TOP3_CORRECT] = row_metadata[K_GROUND_TRUTH_TEAM] in classification[K_TOP3]

    log_pipeline_complete(
        logger,
        version=PIPELINE_VERSION_V5,
        case_id=case_id,
        duration=pipeline_total_time,
        predicted_team=classification[K_TOP_TEAM],
        target_team=routing[K_TARGET_TEAM],
        routing_status=routing[K_ROUTING_STATUS],
        injection_detected=injection_result[K_DETECTED],
        no_answer_triggered=no_answer_triggered,
        risk_score=risk_result[K_SCORE],
        response_mode=response_mode,
        human_review_required=human_review_required,
        workflow_status=workflow_status,
        completeness_score=answer_completeness.get(K_COMPLETENESS_SCORE),
        retrieval_expanded=retrieval_result[K_RETRIEVAL_EXPANDED],
    )

    return result


def run_v5_pipeline_with_audit(
        inquiry_text: str,
        config: dict[str, Any],
        vector_store: Any,
        row_metadata: dict[str, Any] | None = None,
        audit_log_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Führt die v5-Pipeline aus und schreibt optional einen datensparsamen Audit-Eintrag.

    Der Wrapper hält den reinen Pipeline-Aufruf frei von Dateischreibeffekten,
    erlaubt aber Web- und Operations-Flows, dieselbe Audit-Logik wie Batch-Runs
    zu verwenden.
    """
    result = run_v5_pipeline(
        inquiry_text=inquiry_text,
        config=config,
        vector_store=vector_store,
        row_metadata=row_metadata,
    )

    if audit_log_path is not None:
        log_decision(str(audit_log_path), result)

    return result
