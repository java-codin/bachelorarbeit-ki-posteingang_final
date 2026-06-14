"""
Zentrale Sammlung von statischen Antworttexten und Prüfmustern für den V3-Prototyp.
Dies hält Fallbacks, Guardrails und Injection-Erkennung nachvollziehbar.
"""

# --- Klassifikation & Routing ---

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


# --- Fallback & Static Answers ---

MSG_NO_KNOWLEDGE_FOUND = (
    "Für dieses Anliegen liegen keine ausreichenden Informationen "
    "in der Wissensbasis vor. Eine manuelle Prüfung ist erforderlich."
)

MSG_NO_ANSWER = (
    "Ihr Anliegen konnte automatisiert nicht ausreichend sicher bearbeitet "
    "werden. Es wird daher zur manuellen Prüfung weitergeleitet.\n\n"
    "Hinweis: Es wurde bewusst kein fachlicher Antwortentwurf erzeugt, "
    "um fehlerhafte oder unbelegte Aussagen zu vermeiden."
)

MSG_BLOCKED_ANSWER = (
    "Ihre Nachricht enthält Inhalte, die als potenziell sicherheitskritisch "
    "erkannt wurden. Eine automatische Bearbeitung erfolgt daher nicht. "
    "Das Anliegen wird zur manuellen Prüfung weitergeleitet."
)


# --- Sicherheitsprüfung: Prompt-Injection-nahe Muster ---

SUSPICIOUS_PATTERNS = [
    "ignoriere alle vorherigen",
    "ignore previous instructions",
    "ignore all previous",
    "ignore all prior",
    "system prompt",
    "systemregeln",
    "geheime informationen",
    "interne daten",
    "admin",
    "überschreibe",
    "personenbezogene daten",
    "ignoriere alle bisherigen",
    "ignoriere alle regeln",
    "ignoriere alle bisherigen regeln",
    "vorherige anweisungen",
    "bisherige anweisungen",
    "leite diese anfrage direkt",
    "direkt an den bürgermeister",
    "bürgermeister",
]

SECURITY_CLASSIFICATION_REASON = (
    "Sicherheitsprüfung: Die Nachricht enthält eine Anweisung, die auf eine "
    "Umgehung der vorgesehenen Bearbeitungsregeln hindeutet."
)


# --- Guardrails: Riskante Phrasen ---

RISKY_ANSWER_PHRASES = [
    "ich vermute",
    "wahrscheinlich",
    "möglicherweise",
    "rechtlich verbindlich",
    "garantiert",
]


# --- Pipeline-Ausgaben (pipelines/run_v3.py) ---

PIPELINE_CASE_START = "\n[{index}/{total}] Starte Fall {case_id}"

PIPELINE_CASE_DONE = (
    "  - Fertig: injection_detected={injection_detected}, "
    "no_answer={no_answer_triggered}, "
    "human_review={human_review_required}, "
    "guardrail_triggered={guardrail_triggered}, "
    "dauer={case_duration:.2f}s"
)

PIPELINE_V3_SUMMARY_HEADER = "\n===== V3 Governance & Guardrails =====\n"
