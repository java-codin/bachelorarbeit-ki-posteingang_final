"""Regelbasierte Klassifikation der Baseline-Pipeline v0.

Die Funktion nutzt Schlüsselwörter aus der Konfiguration und zeigt damit den
einfachsten Ausgangspunkt vor den LLM-gestützten Pipeline-Versionen.
"""

def classify(text, config):
    """
    Klassifiziert einen Text basierend auf einer gegebenen Konfiguration, um Teams zuzuordnen, die
    am besten mit dem Inhalt des Texts korrelieren. Die Klassifikation erfolgt durch die Analyse
    von Schlüsselwörtern, die in der Konfiguration definiert sind. Das Ergebnis umfasst das
    höchstbewertete Team, die Top-3-Teams, die berechnete Zuversicht für die Klassifikation,
    einen Grund für die Zuordnung und die identifizierten Schlüsselwörter pro Team.

    :param text: Der Eingabetext, der klassifiziert werden soll.
    :type text: str
    :param config: Die Konfiguration, die unter anderem Informationen über Teams und deren
        zugehörige Schlüsselwörter enthält. Erwartet wird ein Wörterbuch mit einer Struktur,
        bei der jedes Team durch eine ID repräsentiert wird, und jedes Team eine Liste von
        Schlüsselwörtern besitzt.
    :type config: dict
    :return: Ein Wörterbuch mit folgenden Schlüsseln:
        - "top_team" (str): Die ID des am besten passenden Teams oder "unknown", falls keine
          Zuordnung möglich war.
        - "top3" (list[str]): Eine Liste der IDs der besten drei Teams, die das höchste
          Punktverhältnis erzielten.
        - "confidence" (float): Der Zuversichtswert der Klassifikation, basierend auf dem Anteil
          der Schlüsselworttreffer des besten Teams im Vergleich zu allen anderen Teams.
        - "reason" (str): Eine verbale Erklärung der Zuordnung, z. B. basierend auf gefundenen
          Schlüsselwörtern.
        - "matched_keywords" (dict): Ein Wörterbuch, das für jede Team-ID die Liste der
          Schlüsselwörter enthält, die mit dem Text übereinstimmen.
    :rtype: dict
    """
    text_lower = text.lower()
    scores = {}
    matched_keywords = {}

    for team_id, team in config["teams"].items():
        keywords = team.get("keywords", [])

        matches = [
            keyword for keyword in keywords
            if keyword.lower() in text_lower
        ]

        scores[team_id] = len(matches)
        matched_keywords[team_id] = matches

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse = True
    )

    top_team, top_score = ranked[0]

    if top_score == 0:
        return {
            "top_team": "unknown",
            "top3": [],
            "confidence": 0.0,
            "reason": "Keine passenden Schlüsselwörter gefunden.",
            "matched_keywords": {}
        }

    total_score = sum(scores.values())
    confidence = top_score / total_score if total_score > 0 else 0

    top3 = [
        team_id for team_id, score in ranked[:3]
        if score > 0
    ]

    return {
        "top_team": top_team,
        "top3": top3,
        "confidence": round(confidence, 2),
        "reason": (
            f"Zuordnung wegen Keyword-Match: "
            f"{', '.join(matched_keywords[top_team])}"
        ),
        "matched_keywords": matched_keywords
    }
