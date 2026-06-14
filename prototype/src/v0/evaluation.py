"""Metrikberechnung für die Baseline-Pipeline v0.

Das Modul erzeugt einfache Routing-Kennzahlen, die als Referenz für die
fortgeschritteneren Pipeline-Versionen dienen.
"""

import pandas as pd
from typing import Any, List, Tuple


def evaluate(results: List[dict[str, Any]]) -> Tuple[pd.DataFrame, dict[str, Any]]:
    """
    Berechnet Evaluierungsmetriken für Vorhersagedaten und aktualisiert ein Pandas DataFrame.

    Diese Funktion dient zur Bewertung von Klassifikationsvorhersagen im Kontext der Zuordnung
    zu Teams. Sie überprüft, ob die vorhergesagten Teams korrekt sind, ob sie in den Top-3-
    Vorhersagen enthalten sind und ob ein unbekanntes Team vorhergesagt wurde. Die Berechnung
    liefert Genauigkeiten (Top-1 und Top-3) sowie die Rate der unbekannten Vorhersagen.

    :param results: Eine Liste von Ergebnissen, wobei jedes Ergebnis eine Vorhersage sowie die
        zugehörigen Ground-Truth-Daten enthält. Die Ergebnisse müssen mindestens die Felder
        `ground_truth_team`, `predicted_team` und `top3` enthalten.
    :return: Ein Tupel, bestehend aus:
        - Einem `DataFrame`, der die ursprünglichen Ergebnisse mit ergänzenden Evaluierungs-Spalten (`top1_correct`, `top3_correct`, `unknown_predicted`) enthält.
        - Einem `dict`, das die zusammengefassten Metriken `top1_accuracy`, `top3_accuracy`,
          `unknown_rate` und `total_cases` zurückgibt.
    """
    df = pd.DataFrame(results)

    df["top1_correct"] = (
        df["ground_truth_team"] == df["predicted_team"]
    )

    df["top3_correct"] = df.apply(
        lambda row: (
            row["ground_truth_team"] in row["top3"]
            if isinstance(row["top3"], list)
            else False
        ),
        axis=1
    )

    df["unknown_predicted"] = df["predicted_team"] == "unknown"

    metrics = {
        "top1_accuracy": round(df["top1_correct"].mean(), 4),
        "top3_accuracy": round(df["top3_correct"].mean(), 4),
        "unknown_rate": round(df["unknown_predicted"].mean(), 4),
        "total_cases": len(df)
    }

    return df, metrics
