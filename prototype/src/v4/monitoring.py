"""Monitoring-Export der Pipeline v4.

Die Funktion verdichtet Fallresultate zu operativen Kennzahlen für Risiko,
Human Review, Eskalation und Antwortmodi.
"""

from typing import Any, List

import pandas as pd

from src.v4.core.constants import (
    K_GUARDRAIL_TRIGGERED,
    K_HAS_RETRIEVED_SOURCES,
    K_HAS_USED_SOURCES,
    K_HUMAN_REVIEW_REQUIRED,
    K_INJECTION_DETECTED,
    K_PREDICTED_TEAM,
    K_RISK_SCORE,
    K_TOP1_CORRECT,
    K_WORKFLOW_STATUS,
    STATUS_AUTO,
    STATUS_BLOCKED,
    STATUS_ESCALATED,
    V_UNKNOWN,
)


def create_monitoring_dataframe(results: List[dict[str, Any]]) -> pd.DataFrame:
    """
    Erstellt ein DataFrame zur Überwachung und Bewertung von Ergebnissen, die mit einem generativen
    KI-Modell und einer anschließenden Verarbeitungslogik erzeugt wurden. Das Monitoring-DataFrame
    enthält aggregierte Kennzahlen, die verschiedene Aspekte der Systemleistung und Sicherheit
    bewerten. Diese Kennzahlen umfassen unter anderem die Genauigkeit, Raten von unsicheren oder
    unspezifischen Entscheidungen, die Notwendigkeit menschlicher Überprüfung sowie die Einhaltung
    von Guardrails.

    Das Monitoring-DataFrame hat eine Zeile, in der für jede Kennzahl ein aggregierter Wert enthalten
    ist. Dazu gehören z. B. die Top-1-Genauigkeit, das Verhältnis menschlicher Überprüfungsanfragen,
    die durchschnittliche Risikobewertung und das Auftreten von Eskalationen oder blockierten Fällen.

    :param results: Eine Liste von Wörternbüchern, wobei jedes Wörterbuch die Ergebnisse eines
        einzelnen Falles enthält. Diese Ergebnisse umfassen sowohl Modellvorhersagen als auch
        Metadaten wie Risikobewertungen oder Statusinformationen zu Workflows.
    :type results: List[dict[str, Any]]

    :return: Ein ``pandas.DataFrame``, das eine aggregierte Übersicht mehrerer Überwachungs- und
        Leistungsmetriken enthält. Jede Kennzahl wird dabei in einer separaten Spalte aufgelistet.
    :rtype: pd.DataFrame
    """
    df = pd.DataFrame(results)

    monitoring = {
        "total_cases": len(df),
        "top1_accuracy": round(df[K_TOP1_CORRECT].mean(), 4),
        "unknown_rate": round((df[K_PREDICTED_TEAM] == V_UNKNOWN).mean(), 4),
        "human_review_rate": round(df[K_HUMAN_REVIEW_REQUIRED].mean(), 4),
        "escalation_rate": round((df[K_WORKFLOW_STATUS] == STATUS_ESCALATED).mean(), 4),
        "blocked_rate": round((df[K_WORKFLOW_STATUS] == STATUS_BLOCKED).mean(), 4),
        "auto_draft_rate": round((df[K_WORKFLOW_STATUS] == STATUS_AUTO).mean(), 4),
        "avg_risk_score": round(df[K_RISK_SCORE].mean(), 4),
        "retrieved_source_coverage": round(df[K_HAS_RETRIEVED_SOURCES].mean(), 4),
        "used_source_coverage": round(df[K_HAS_USED_SOURCES].mean(), 4),
        "injection_detection_rate": round(df[K_INJECTION_DETECTED].mean(), 4),
        "guardrail_trigger_rate": round(df[K_GUARDRAIL_TRIGGERED].mean(), 4)
    }

    return pd.DataFrame([monitoring])
