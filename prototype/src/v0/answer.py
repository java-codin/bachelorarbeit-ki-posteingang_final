"""Antworttext-Erzeugung der Baseline-Pipeline v0.

Das Modul bildet bewusst nur einen einfachen Entwurf ab und dient als
Vergleichspunkt für spätere RAG- und Guardrail-Iterationen.
"""

def generate_answer(classification, routing):
    """
    Erzeugt eine Antwortnachricht basierend auf der Klassifikation und der Routing-Strategie.
    Diese Funktion erstellt entweder einen Entwurf, der zur manuellen Prüfung benötigt wird,
    oder einen automatisierten Antwortentwurf mit einer Begründung basierend auf der regelbasierten
    Klassifikation. Der erzeugte Entwurf ist eine Vorlage zur weiteren Bearbeitung.

    :param classification: Ein `dict`, das die Ergebnisse der Klassifikation enthält. Erwartet
                           Schlüssel wie `top_team` und `reason`, die zur Entscheidung der
                           Antwort beitragen.
    :param routing: Ein `dict`, das Routing-Informationen bereitstellt. Erwartet Schlüssel wie
                    `display_name` und `target_email`, die für die Zuordnung und Empfehlung
                    genutzt werden.
    :return: Ein `str`, das die automatisch generierte Antwort als Entwurf enthält.
    """
    if classification["top_team"] == "unknown":
        return (
            "Vielen Dank für Ihre Nachricht.\n\n"
            "Ihr Anliegen konnte in der regelbasierten Baseline nicht eindeutig "
            "zugeordnet werden. Es wird daher zur manuellen Prüfung weitergeleitet.\n\n"
            "Hinweis: Dies ist ein automatisch erzeugter Entwurf der Version V0."
        )

    return (
        f"Vielen Dank für ihre Nachricht.\n\n"
        f"Ihr Anliegen wurde regelbasiert dem Bereich "
        f"{routing['display_name']} zugeordnet.\n\n"
        f"Begründung: {classification['reason']}\n\n"
        f"Vorgeschlagene Weiterleitung: {routing['target_email']}\n\n"
        "Hinweis: Dies ist ein automatisch erzeugter Entwurf der Version V0."
    )
