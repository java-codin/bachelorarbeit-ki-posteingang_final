"""Risikobewertung und Evaluationslogik der Pipeline v5.

Das Modul bewertet Sicherheits-, Quellen-, Workflow- und Qualitätsaspekte und
verdichtet Fallresultate zu Metriken für die wissenschaftliche Auswertung.
"""

from typing import Any, Optional
import pandas as pd
from src.v5.core.constants import (
    K_TOP_TEAM, K_CONFIDENCE, K_DETECTED, K_FLAGS, K_SCORE, K_REASONS,
    K_HUMAN_REQUIRED, V_UNKNOWN, REASON_UNKNOWN_TEAM, REASON_LOW_CONFIDENCE,
    REASON_PROMPT_INJECTION, REASON_NO_ANSWER_TRIGGERED, REASON_GUARDRAIL_FLAGS,
    REASON_INCOMPLETE_ANSWER, MODE_BLOCKED, MODE_ESCALATION, MODE_NO_ANSWER,
    MODE_REVIEW, MODE_NORMAL, K_REQUIRED, K_RESPONSE_MODE,
    CLASSIFICATION_REVIEW_THRESHOLD, RISK_WEIGHT_HIGH_RISK_KEYWORD, RISK_WEIGHT_UNKNOWN_TEAM,
    RISK_WEIGHT_LOW_CONFIDENCE, RISK_WEIGHT_PROMPT_INJECTION, RISK_WEIGHT_NO_ANSWER, RISK_WEIGHT_GUARDRAIL_FLAGS,
    RISK_WEIGHT_INCOMPLETE_ANSWER, RISK_ESCALATION_THRESHOLD, RISK_REVIEW_THRESHOLD
)
from src.v5.core.response_messages import HIGH_RISK_KEYWORDS, ISSUE_HIGH_RISK_KEYWORD

from src.v5.core.constants import (
    K_TOP1_CORRECT,
    K_TOP3_CORRECT,
    K_PREDICTED_TEAM,
    K_HUMAN_REVIEW_REQUIRED,
    K_WORKFLOW_STATUS,
    K_RISK_SCORE,
    K_HAS_RETRIEVED_SOURCES,
    K_HAS_USED_SOURCES,
    K_COMPLETENESS_SCORE,
    STATUS_ESCALATED,
    STATUS_BLOCKED,
    STATUS_AUTO,
    M_TOP1_ACCURACY,
    M_TOP3_ACCURACY,
    M_UNKNOWN_RATE,
    M_HUMAN_REVIEW_RATE,
    M_ESCALATION_RATE,
    M_BLOCKED_RATE,
    M_AUTO_DRAFT_RATE,
    M_AVG_RISK_SCORE,
    M_RETRIEVED_SOURCE_COVERAGE,
    M_USED_SOURCE_COVERAGE,
    M_AVG_COMPLETENESS_SCORE,
    M_TOTAL_CASES,
)

def evaluate_comprehensive_risk(
        inquiry_text: str,
        classification: dict[str, Any],
        injection_result: dict[str, Any],
        guardrail_result: dict[str, Any],
        no_answer_triggered: bool,
        answer_completeness: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Analysiert eine Kundenanfrage und bewertet das Risiko basierend auf mehreren Faktoren.
    Zu den analysierten Risikofaktoren gehören Schlüsselwörter mit hohem Risiko, Klassifikationsunsicherheiten,
    potenzielle Sicherheitsprobleme wie Injection-Vorfälle, Fallback-Ereignisse (z. B. keine Antwort möglich),
    Guardrail-Verstöße und Unvollständigkeiten in den generierten Antworten.

    Das Ergebnis umfasst eine Risikobewertung, die Gründe für das Risiko und einen abgeleiteten
    Antwortmodus basierend auf der Risikolage.

    :param inquiry_text: Der Text der Kundenanfrage, der analysiert werden soll.
    :param classification: Ein Wörterbuch mit Informationen zur Klassifikation, einschließlich Zuordnung
        zu einem Team und Konfidenzniveau.
    :param injection_result: Ein Wörterbuch, das anzeigt, ob ein Injection-Vorfall entdeckt wurde,
        sowie zugehörige Details.
    :param guardrail_result: Ein Wörterbuch mit Flags und Indikatoren zu Verstößen gegen festgelegte Guardrails.
    :param no_answer_triggered: Ein boolescher Wert, der angibt, ob für die Anfrage keine Antwort generiert werden konnte.
    :param answer_completeness: Ein optionales Wörterbuch, das Informationen zur Vollständigkeit der generierten
        Antwort enthält, wie etwa, ob eine menschliche Überprüfung erforderlich ist.
    :return: Ein Wörterbuch mit folgenden Schlüsseln:
        - `K_SCORE`: Die numerische Risikobewertung basierend auf den analysierten Faktoren.
        - `K_REASONS`: Eine Liste mit String-basierten Erklärungen für die festgestellten Risiken.
        - `K_RESPONSE_MODE`: Der abgeleitete Antwortmodus, wie z. B. normal, Eskalation, Überprüfung oder Blockierung.
        - `K_REQUIRED`: Ein boolescher Wert, der angibt, ob weitere Maßnahmen oder menschliche Überprüfungen erforderlich sind.
    """
    score = 0
    reasons = []

    # 1. Keyword-Prüfung (High Risk)
    text_lower = inquiry_text.lower()
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text_lower:
            score += RISK_WEIGHT_HIGH_RISK_KEYWORD
            reasons.append(ISSUE_HIGH_RISK_KEYWORD.format(keyword=keyword))

    # 2. Klassifikations-Risiken
    if classification[K_TOP_TEAM] == V_UNKNOWN:
        score += RISK_WEIGHT_UNKNOWN_TEAM
        reasons.append(REASON_UNKNOWN_TEAM)

    if classification[K_CONFIDENCE] < CLASSIFICATION_REVIEW_THRESHOLD:
        score += RISK_WEIGHT_LOW_CONFIDENCE
        reasons.append(REASON_LOW_CONFIDENCE)

    # 3. Sicherheits-Risiken (Injection)
    if injection_result[K_DETECTED]:
        score += RISK_WEIGHT_PROMPT_INJECTION
        reasons.append(REASON_PROMPT_INJECTION)

    # 4. Fallback-Risiken (No Answer)
    if no_answer_triggered:
        score += RISK_WEIGHT_NO_ANSWER
        reasons.append(REASON_NO_ANSWER_TRIGGERED)

    # 5. Guardrail-Risiken
    if guardrail_result[K_FLAGS]:
        score += RISK_WEIGHT_GUARDRAIL_FLAGS
        reasons.append(REASON_GUARDRAIL_FLAGS)

    # 6. Vollständigkeits-Risiken
    if answer_completeness and answer_completeness.get(K_HUMAN_REQUIRED):
        score += RISK_WEIGHT_INCOMPLETE_ANSWER
        reasons.append(REASON_INCOMPLETE_ANSWER)

    # 7. Response-Mode Ableitung
    response_mode = MODE_NORMAL
    if injection_result[K_DETECTED]:
        response_mode = MODE_BLOCKED
    elif score >= RISK_ESCALATION_THRESHOLD:
        response_mode = MODE_ESCALATION
    elif no_answer_triggered:
        response_mode = MODE_NO_ANSWER
    elif score >= RISK_REVIEW_THRESHOLD or len(reasons) > 0:
        response_mode = MODE_REVIEW

    return {
        K_SCORE: score,
        K_REASONS: reasons,
        K_RESPONSE_MODE: response_mode,
        K_REQUIRED: len(reasons) > 0
    }


def evaluate(results: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Evaluiert die gegebenen Ergebnisse und berechnet diverse Kennzahlen.

    Diese Funktion extrahiert Metriken aus einer Liste von Ergebnissen in Form von
    `dict`-Objekten, erstellt eine `DataFrame`-Repräsentation und berechnet
    zusammenfassende Statistiken, z. B. Genauigkeitsraten, Überprüfungsraten,
    Blockierungsraten, Risikobewertungen und andere. Die Berechnungen basieren auf
    vorhandenen Feldern in den übergebenen Ergebnissen.

    :param results: Eine Liste von `dict`-Objekten, die die Bewertungsergebnisse
                    einzelner Fälle oder Vorhersagen enthalten. Die `dict`-Objekte
                    können optionale Schlüssel wie `top1_correct`, `top3_correct`,
                    `predicted_team`, `workflow_status`, `risk_score`,
                    `has_retrieved_sources`, `has_used_sources` oder
                    `answer_completeness_score` enthalten.

    :return:
        - Ein `DataFrame`, das die übergebenen Ergebnisse in tabellarischer Form
          strukturiert.
        - Ein Wörterbuch mit berechneten Metriken, darunter:
            - `top1_accuracy` (float): Durchschnittswert der Spalte
              `top1_correct`, falls verfügbar.
            - `top3_accuracy` (float): Durchschnittswert der Spalte
              `top3_correct`, falls verfügbar.
            - `unknown_rate` (float): Anteil der Fälle, bei denen
              `predicted_team` den Wert `"unknown"` hat.
            - `human_review_rate` (float): Durchschnittswert der Spalte
              `human_review_required`, falls verfügbar.
            - `escalation_rate` (float): Anteil der Fälle mit
              `workflow_status` `"escalated_review"`.
            - `blocked_rate` (float): Anteil der Fälle mit
              `workflow_status` `"blocked"`.
            - `auto_draft_rate` (float): Anteil der Fälle mit
              `workflow_status` `"auto_draft"`.
            - `avg_risk_score` (float): Durchschnitt der Spalte `risk_score`,
              falls verfügbar.
            - `retrieved_source_coverage` (float): Durchschnittswert der Spalte
              `has_retrieved_sources`, falls verfügbar.
            - `used_source_coverage` (float): Durchschnittswert der Spalte
              `has_used_sources`, falls verfügbar.
            - `avg_completeness_score` (float): Durchschnittswert der Spalte
              `answer_completeness_score`, falls verfügbar.
            - `total_cases` (int): Gesamtanzahl der Einträge in den Ergebnissen.
    """
    import pandas as pd
    df = pd.DataFrame(results)

    # Hilfsfunktion für sicheren Zugriff auf Spalten
    def get_mean(col: str) -> float:
        if col in df.columns:
            return round(df[col].mean(), 4)
        return 0.0

    metrics = {
        M_TOP1_ACCURACY: get_mean(K_TOP1_CORRECT),
        M_TOP3_ACCURACY: get_mean(K_TOP3_CORRECT),
        M_UNKNOWN_RATE: round((df[K_PREDICTED_TEAM] == V_UNKNOWN).mean(), 4) if K_PREDICTED_TEAM in df.columns else 0.0,
        M_HUMAN_REVIEW_RATE: get_mean(K_HUMAN_REVIEW_REQUIRED),
        M_ESCALATION_RATE: round((df[K_WORKFLOW_STATUS] == STATUS_ESCALATED).mean(),
                                 4) if K_WORKFLOW_STATUS in df.columns else 0.0,
        M_BLOCKED_RATE: round((df[K_WORKFLOW_STATUS] == STATUS_BLOCKED).mean(),
                              4) if K_WORKFLOW_STATUS in df.columns else 0.0,
        M_AUTO_DRAFT_RATE: round((df[K_WORKFLOW_STATUS] == STATUS_AUTO).mean(),
                                 4) if K_WORKFLOW_STATUS in df.columns else 0.0,
        M_AVG_RISK_SCORE: get_mean(K_RISK_SCORE),
        M_RETRIEVED_SOURCE_COVERAGE: get_mean(K_HAS_RETRIEVED_SOURCES),
        M_USED_SOURCE_COVERAGE: get_mean(K_HAS_USED_SOURCES),
        M_AVG_COMPLETENESS_SCORE: get_mean(K_COMPLETENESS_SCORE),
        M_TOTAL_CASES: len(df),
    }

    return df, metrics
