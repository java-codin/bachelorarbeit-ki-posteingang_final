"""Risikobewertung und Evaluationslogik der Pipeline v4.

Das Modul berechnet Fallmetriken sowie risiko- und reviewbezogene Signale, die
für Response-Policy und Monitoring genutzt werden.
"""

from typing import Any
import pandas as pd

from src.v4.core.constants import (
    K_GUARDRAIL_TRIGGERED,
    K_HAS_RETRIEVED_SOURCES,
    K_HAS_USED_SOURCES,
    K_HUMAN_REVIEW_REQUIRED,
    K_INJECTION_DETECTED,
    K_PREDICTED_TEAM,
    K_RESPONSE_MODE,
    K_RISK_SCORE,
    K_TOP1_CORRECT,
    K_TOP3_CORRECT,
    K_WORKFLOW_STATUS,
    M_AUTO_DRAFT_RATE,
    M_AVG_RISK_SCORE,
    M_BLOCKED_RATE,
    M_ESCALATION_RATE,
    M_GUARDRAIL_TRIGGER_RATE,
    M_HUMAN_REVIEW_RATE,
    M_INJECTION_DETECTION_RATE,
    M_RESPONSE_BLOCKED_RATE,
    M_RESPONSE_ESCALATION_RATE,
    M_RESPONSE_NO_ANSWER_RATE,
    M_RESPONSE_REVIEW_RATE,
    M_RETRIEVED_SOURCE_COVERAGE,
    M_TOP1_ACCURACY,
    M_TOP3_ACCURACY,
    M_TOTAL_CASES,
    M_UNKNOWN_RATE,
    M_USED_SOURCE_COVERAGE,
    MODE_BLOCKED,
    MODE_ESCALATION,
    MODE_NO_ANSWER,
    MODE_REVIEW,
    STATUS_AUTO,
    STATUS_BLOCKED,
    STATUS_ESCALATED,
    V_UNKNOWN,
)


def _mean_bool_or_numeric(df: pd.DataFrame, column: str) -> float:
    """
    Berechnet den Durchschnitt eines numerischen oder booleschen Spalteninhalts in einem
    `pandas.DataFrame`. Wenn die Spalte nicht vorhanden ist oder der Durchschnitt nicht
    berechnet werden kann (z. B. aufgrund fehlender Werte), wird `0.0` zurückgegeben.

    .. note::
        Numerische und boolesche Datentypen werden berücksichtigt. Falls der Spaltenwert
        nicht numerisch oder booleschen Typs ist, wird der Durchschnitt standardmäßig zu `0.0` gesetzt.

    :param df: Der `pandas.DataFrame`, aus dem der Durchschnittswert ermittelt werden soll.
    :type df: pd.DataFrame
    :param column: Der Name der Spalte, für die der Durchschnitt berechnet wird.
    :type column: str
    :return: Der berechnete Durchschnittswert, gerundet auf vier Dezimalstellen. Falls
             keine Berechnung möglich ist, wird `0.0` zurückgegeben.
    :rtype: float
    """
    if column not in df.columns:
        return 0.0

    value = df[column].mean()

    if pd.isna(value):
        return 0.0

    return round(value, 4)


def _rate_equals(df: pd.DataFrame, column: str, value: Any) -> float:
    """
    Berechnet den Anteil der Zeilen in einem DataFrame, bei denen der Wert in der angegebenen Spalte
    mit dem übergebenen Wert übereinstimmt. Falls die Spalte im DataFrame nicht existiert, wird
    `0.0` zurückgegeben.

    :param df: Der `DataFrame`, in dem die Übereinstimmung analysiert werden soll.
    :type df: pd.DataFrame
    :param column: Der Name der Spalte, die überprüft werden soll.
    :type column: str
    :param value: Der Wert, mit dem die Werte in der Spalte verglichen werden sollen.
    :type value: Any
    :return: Der Anteil der Zeilen mit übereinstimmendem Wert, gerundet auf vier Nachkommastellen,
             oder `0.0`, falls die Spalte nicht existiert.
    :rtype: float
    """
    if column not in df.columns:
        return 0.0

    return round((df[column] == value).mean(), 4)


def evaluate(results: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Berechnet Evaluationsmetriken basierend auf den übergebenen Ergebnissen und gibt diese
    zusammen mit den Resultaten in DataFrame-Form zurück. Die Funktion dient der Analyse von
    Modell- und Workflow-Leistungen in Bezug auf verschiedene KPIs (Key Performance Indicators).
    Die Ausgabe der Metriken ermöglicht eine detaillierte Rückverfolgung und Bewertung der
    Qualität und Effizienz des Modells sowie der Workflows.

    :param results: Eine Liste von Wörterbüchern, die die Ergebnisse einzelner Fälle beschreibt.
        Diese Ergebnisse beinhalten Schlüssel wie `K_TOP1_CORRECT`, `K_TOP3_CORRECT`,
        `K_PREDICTED_TEAM`, `K_HUMAN_REVIEW_REQUIRED`, `K_WORKFLOW_STATUS`, `K_RESPONSE_MODE`,
        `K_RISK_SCORE`, `K_HAS_RETRIEVED_SOURCES`, `K_HAS_USED_SOURCES`, `K_INJECTION_DETECTED`
        und `K_GUARDRAIL_TRIGGERED`. Jedes Wörterbuch repräsentiert den Zustand eines einzelnen
        verarbeiteten Falls.
    :return: Ein Tupel, bestehend aus einem DataFrame und einem Wörterbuch.
        - Der erste Rückgabewert ist ein DataFrame, welcher die ursprünglichen Ergebnisse in
          strukturierter Form enthält.
        - Der zweite Rückgabewert ist ein Wörterbuch mit berechneten Metriken, das folgende
          Schlüssel enthält:
            * `M_TOP1_ACCURACY`: Durchschnittswert der Treffsicherheit der besten Vorhersage.
            * `M_TOP3_ACCURACY`: Durchschnittswert der Treffsicherheit der besten drei
              Vorhersagen.
            * `M_UNKNOWN_RATE`: Anteil der Fälle, bei denen das prädizierte Team `V_UNKNOWN`
              war.
            * `M_HUMAN_REVIEW_RATE`: Durchschnittswert der menschlichen Überprüfungen.
            * `M_ESCALATION_RATE`: Anteil der eskalierten Workflow-Status.
            * `M_BLOCKED_RATE`: Anteil der blockierten Workflow-Status.
            * `M_AUTO_DRAFT_RATE`: Anteil der automatischen Antwortentwürfe.
            * `M_RESPONSE_REVIEW_RATE`: Anteil der Fälle im Überprüfungsmodus.
            * `M_RESPONSE_NO_ANSWER_RATE`: Anteil der Fälle ohne Antwort.
            * `M_RESPONSE_ESCALATION_RATE`: Anteil der Antwortfälle, die eskaliert wurden.
            * `M_RESPONSE_BLOCKED_RATE`: Anteil der Antwortfälle, die blockiert wurden.
            * `M_AVG_RISK_SCORE`: Durchschnittlicher Risikobewertungswert.
            * `M_RETRIEVED_SOURCE_COVERAGE`: Abdeckungsrate der abgerufenen Quellen.
            * `M_USED_SOURCE_COVERAGE`: Abdeckungsrate der genutzten Quellen.
            * `M_INJECTION_DETECTION_RATE`: Anteil der Fälle, in denen Injektionsangriffe
              erkannt wurden.
            * `M_GUARDRAIL_TRIGGER_RATE`: Anteil der Fälle, in denen Schutzmechanismen
              ausgelöst wurden.
            * `M_TOTAL_CASES`: Gesamtanzahl der verarbeiteten Fälle.
    """
    df = pd.DataFrame(results)

    metrics = {
        M_TOP1_ACCURACY: _mean_bool_or_numeric(df, K_TOP1_CORRECT),
        M_TOP3_ACCURACY: _mean_bool_or_numeric(df, K_TOP3_CORRECT),
        M_UNKNOWN_RATE: _rate_equals(df, K_PREDICTED_TEAM, V_UNKNOWN),
        M_HUMAN_REVIEW_RATE: _mean_bool_or_numeric(df, K_HUMAN_REVIEW_REQUIRED),
        M_ESCALATION_RATE: _rate_equals(df, K_WORKFLOW_STATUS, STATUS_ESCALATED),
        M_BLOCKED_RATE: _rate_equals(df, K_WORKFLOW_STATUS, STATUS_BLOCKED),
        M_AUTO_DRAFT_RATE: _rate_equals(df, K_WORKFLOW_STATUS, STATUS_AUTO),
        M_RESPONSE_REVIEW_RATE: _rate_equals(df, K_RESPONSE_MODE, MODE_REVIEW),
        M_RESPONSE_NO_ANSWER_RATE: _rate_equals(df, K_RESPONSE_MODE, MODE_NO_ANSWER),
        M_RESPONSE_ESCALATION_RATE: _rate_equals(df, K_RESPONSE_MODE, MODE_ESCALATION),
        M_RESPONSE_BLOCKED_RATE: _rate_equals(df, K_RESPONSE_MODE, MODE_BLOCKED),
        M_AVG_RISK_SCORE: _mean_bool_or_numeric(df, K_RISK_SCORE),
        M_RETRIEVED_SOURCE_COVERAGE: _mean_bool_or_numeric(df, K_HAS_RETRIEVED_SOURCES),
        M_USED_SOURCE_COVERAGE: _mean_bool_or_numeric(df, K_HAS_USED_SOURCES),
        M_INJECTION_DETECTION_RATE: _mean_bool_or_numeric(df, K_INJECTION_DETECTED),
        M_GUARDRAIL_TRIGGER_RATE: _mean_bool_or_numeric(df, K_GUARDRAIL_TRIGGERED),
        M_TOTAL_CASES: len(df)
    }

    return df, metrics
