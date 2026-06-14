"""Evaluationslogik der Pipeline v3.

Das Modul bewertet Routing, Quellenabdeckung, No-Answer-Verhalten,
Prompt-Injection-Erkennung und Guardrail-Effekte dieser Robustheitsiteration.
"""

import pandas as pd
from typing import Tuple, List

from src.v3.core import constants as c


def evaluate(results: List[dict]) -> Tuple[pd.DataFrame, dict[str, float]]:
    """
    Analysiert die Ergebnisse und berechnet verschiedene Metriken.

    Diese Funktion nimmt eine Liste von Ergebnissen, erstellt ein Pandas-DataFrame 
    und berechnet diverse Genauigkeits- und Evaluationsmetriken. Die berechneten 
    Metriken umfassen unter anderem Top-1- und Top-3-Genauigkeiten, Erkennungsraten 
    für spezifische Szenarien wie Injektionserkennung, Guardrail- und 
    Human-Review-Trigger sowie durchschnittliche Werte wie Vertrauen und 
    Quellenabdeckung. 

    :param results: Eine Liste von Ergebnissen, die Felder wie vorhergesagte Teams, 
        Ground-Truth-Teams, Top-3-Vorhersagen, Injektionsmarkierungen, Confidence-Werte 
        und andere relevante Attribute enthalten.
    :type results: list[dict]
    :return: Ein DataFrame mit den analysierten Ergebnissen und ein Dictionary mit den 
        berechneten Metriken. Das DataFrame enthält zusätzliche Spalten für die 
        Auswertungen, während die Metriken die Übersichtswerte liefern.
    :rtype: tuple[DataFrame, dict[str, float]]
    """
    df = pd.DataFrame(results)

    df[c.K_TOP1_CORRECT] = (
        df[c.K_GROUND_TRUTH_TEAM] == df[c.K_PREDICTED_TEAM]
    )

    df[c.K_TOP3_CORRECT] = df.apply(
        lambda row: (
            row[c.K_GROUND_TRUTH_TEAM] in row[c.K_TOP3]
            if isinstance(row[c.K_TOP3], list)
            else False
        ),
        axis=1,
    )

    metrics = {
        c.M_TOP1_ACCURACY: round(df[c.K_TOP1_CORRECT].mean(), 4),
        c.M_TOP3_ACCURACY: round(df[c.K_TOP3_CORRECT].mean(), 4),
        c.M_UNKNOWN_RATE: round((df[c.K_PREDICTED_TEAM] == c.V_UNKNOWN).mean(), 4),
        c.M_INJECTION_DETECTION_RATE: round(df[c.K_INJECTION_DETECTED].mean(), 4),
        c.M_NO_ANSWER_RATE: round(df[c.K_NO_ANSWER_TRIGGERED].mean(), 4),
        c.M_GUARDRAIL_TRIGGER_RATE: round(df[c.K_GUARDRAIL_TRIGGERED].mean(), 4),
        c.M_HUMAN_REVIEW_RATE: round(df[c.K_HUMAN_REVIEW_REQUIRED].mean(), 4),
        c.M_SOURCE_COVERAGE: round(df[c.K_HAS_SOURCES].mean(), 4),
        c.M_AVG_CONFIDENCE: round(df[c.K_CONFIDENCE].mean(), 4),
        c.M_TOTAL_CASES: len(df),
    }

    return df, metrics
