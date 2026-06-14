"""
Statische Antworttexte und Pipeline-Meldungen für den V2-Prototyp.
"""

DEFAULT_CLASSIFICATION_REASON = "Keine Begründung vorhanden."
DISPLAY_NAME_MANUAL_REVIEW = "Manuelle Prüfung"
MSG_NO_KEYWORDS = "keine Keywords hinterlegt"
MSG_NO_SERVICES = "keine Services hinterlegt"

MATRIX_LINE_TEAM = "Team-ID: {team_id}"
MATRIX_LINE_NAME = "Name: {name}"
MATRIX_LINE_DEPT = "Fachbereich: {department}"
MATRIX_LINE_DESC = "Beschreibung: {description}"
MATRIX_LINE_SERV = "Services: {service_text}"
MATRIX_LINE_KEYS = "Keywords: {keyword_text}"
MATRIX_LINE_MAIL = "E-Mail: {email}"
MATRIX_SEPARATOR = "\n---\n"

RULE_IF_MATCH = "Wenn das Anliegen einen dieser Begriffe oder Services betrifft: {terms}"
RULE_THEN_TEAM = "Dann wähle als top_team: {team}"

MSG_NO_KNOWLEDGE_FOUND = (
    "Für dieses Anliegen liegen in der Wissensbasis keine ausreichenden "
    "Informationen vor. Eine manuelle Prüfung ist erforderlich."
)

NO_ANSWER_INDICATOR = "manuelle Prüfung ist erforderlich"


# --- Pipeline-Ausgaben (pipelines/run_v2.py) ---

PIPELINE_CASE_START = "\n[{index}/{total}] Starte Fall {case_id}"

PIPELINE_CASE_DONE = (
    "  - Fertig: predicted_team={predicted_team}, "
    "sources={source_count}, "
    "dauer={case_duration:.2f}s"
)

PIPELINE_V2_SUMMARY_HEADER = "\n===== V2 RAG with Sources =====\n"
