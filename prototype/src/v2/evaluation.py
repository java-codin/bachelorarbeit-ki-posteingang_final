"""Evaluationslogik der Pipeline v2.

Die Funktion bewertet Routing, Quellenabdeckung und No-Answer-Verhalten für die
erste RAG- und Chunking-orientierte Pipeline-Version.
"""

import pandas as pd

from src.v2.core import constants as c
from src.v2.core.response_messages import NO_ANSWER_INDICATOR


def evaluate(results):
    """
    Analysiert die Ergebnisse einer Klassifikation und berechnet verschiedene
    Metriken zur Bewertung von Vorhersagen und Modellen.

    :param results: Eine Liste von Ergebnissen, die typische Schlüssel enthalten,
        wie `c.K_GROUND_TRUTH_TEAM`, `c.K_PREDICTED_TEAM`, `c.K_TOP3`,
        `c.K_RETRIEVED_SOURCES`, `c.K_DRAFT_ANSWER` und `c.K_CONFIDENCE`. Die
        Struktur der Ergebnisse variiert je nach Kontext, muss jedoch den genannten
        Schlüsseln entsprechen.

    :return: Ein Tupel bestehend aus einem `DataFrame`, das die berechneten
        Ergebnisse und deren Details enthält, und einem Wörterbuch mit aggregierten
        Metriken. Die Metriken umfassen:

        - `c.M_TOP1_ACCURACY`: Genauigkeit basierend auf erster Vorhersage.
        - `c.M_TOP3_ACCURACY`: Genauigkeit basierend auf den ersten drei Vorhersagen.
        - `c.M_UNKNOWN_RATE`: Rate der als "unbekannt" klassifizierten Fälle.
        - `c.M_SOURCE_COVERAGE`: Anteil der Fälle, bei denen Quellen verfügbar sind.
        - `c.M_NO_ANSWER_RATE`: Anteil der Fälle, bei denen keine Antwort ausgelöst wurde.
        - `c.M_AVG_CONFIDENCE`: Durchschnittliches Vertrauensniveau der Vorhersagen.
        - `c.M_TOTAL_CASES`: Gesamtzahl der analysierten Fälle.
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

    df[c.K_UNKNOWN_PREDICTED] = df[c.K_PREDICTED_TEAM] == c.V_UNKNOWN

    df[c.K_HAS_SOURCES] = df[c.K_RETRIEVED_SOURCES].apply(
        lambda sources: isinstance(sources, list) and len(sources) > 0
    )

    df[c.K_NO_ANSWER_TRIGGERED] = df[c.K_DRAFT_ANSWER].apply(
        lambda answer: NO_ANSWER_INDICATOR in answer
    )

    metrics = {
        c.M_TOP1_ACCURACY: round(df[c.K_TOP1_CORRECT].mean(), 4),
        c.M_TOP3_ACCURACY: round(df[c.K_TOP3_CORRECT].mean(), 4),
        c.M_UNKNOWN_RATE: round(df[c.K_UNKNOWN_PREDICTED].mean(), 4),
        c.M_SOURCE_COVERAGE: round(df[c.K_HAS_SOURCES].mean(), 4),
        c.M_NO_ANSWER_RATE: round(df[c.K_NO_ANSWER_TRIGGERED].mean(), 4),
        c.M_AVG_CONFIDENCE: round(df[c.K_CONFIDENCE].mean(), 4),
        c.M_TOTAL_CASES: len(df),
    }

    return df, metrics
