"""
Statische Antworttexte und Pipeline-Meldungen für den V1-Prototyp.
"""

DEFAULT_CLASSIFICATION_REASON = "Keine Begründung vorhanden."
DISPLAY_NAME_MANUAL_REVIEW = "Manuelle Prüfung"

MSG_UNKNOWN_ROUTING_DRAFT = (
    "Vielen Dank für Ihre Nachricht.\n\n"
    "Ihr Anliegen konnte automatisiert nicht eindeutig zugeordnet werden. "
    "Es wird daher zur manuellen Prüfung weitergeleitet.\n\n"
    "Hinweis: Dies ist ein automatisch erzeugter Routing-Entwurf der Version V1."
)

MSG_ROUTING_DRAFT = (
    "Vielen Dank für Ihre Nachricht.\n\n"
    "Ihr Anliegen wurde semantisch dem Bereich {display_name} zugeordnet.\n\n"
    "Begründung der Zuordnung: {reason}\n\n"
    "Vorgeschlagene Weiterleitung: {target_email}.\n\n"
    "Hinweis: Dies ist ein automatisch erzeugter Routing-Entwurf der Version V1."
)

PIPELINE_CASE_START = "\n[{index}/{total}] Starte Fall {case_id}"

PIPELINE_CASE_DONE = (
    "  - Fertig: predicted_team={predicted_team}, "
    "routing_status={routing_status}, "
    "dauer={case_duration:.2f}s"
)

PIPELINE_V1_SUMMARY_HEADER = "\n===== V1 LLM Classification =====\n"
