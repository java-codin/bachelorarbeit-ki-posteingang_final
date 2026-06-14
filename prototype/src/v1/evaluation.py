"""Evaluationslogik der Pipeline v1.

Die Funktion berechnet Routing-Accuracy, Unknown-Rate und Fallanzahl für den
Vergleich mit Baseline und späteren RAG-Versionen.
"""

import pandas as pd
from typing import Tuple, Sequence, Mapping, Any

from src.v1.core import constants as c


def evaluate(results: Sequence[Mapping[str, Any]]) -> tuple[float, float]:
    """
    Bewertet die Ergebnisse einer Klassifikation und berechnet verschiedene Metriken zur
    Leistungsbewertung. Die Funktion erstellt ein `DataFrame` mit berechneten Feldern basierend
    auf vorgegebenen Schlüsseln und liefert außerdem eine Metadatenübersicht mit durchschnittlichen
    und aggregierten Kennzahlen zurück.

    :param results: Ein Wörterbuch, das die Klassifikationsergebnisse enthält. Die enthaltenen
        Schlüssel und Werte sollten mit den Anforderungen der Funktion kompatibel sein.
    :return: Gibt ein `DataFrame` zurück, das die erweiterten Klassifikationsergebnisse enthält,
        sowie ein Wörterbuch mit berechneten Metriken, in denen unter anderem Genauigkeit und
        Durchschnittswerte festgehalten sind.
    :rtype: Tuple[float, float]
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

    metrics = {
        c.M_TOP1_ACCURACY: round(df[c.K_TOP1_CORRECT].mean(), 4),
        c.M_TOP3_ACCURACY: round(df[c.K_TOP3_CORRECT].mean(), 4),
        c.M_UNKNOWN_RATE: round(df[c.K_UNKNOWN_PREDICTED].mean(), 4),
        c.M_AVG_CONFIDENCE: round(df[c.K_CONFIDENCE].mean(), 4),
        c.M_TOTAL_CASES: len(df),
    }

    return df, metrics
