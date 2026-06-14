"""
Zentrale Sammlung von statischen Antworttexten, Hinweisen und Phrasen für den V5-Prototyp.
Dies verbessert die Wartbarkeit und ermöglicht eine einfache Anpassung der Nutzerkommunikation.
"""

# --- Fallback & Static Answers (answer.py & risk_aware_answer.py) ---

MSG_NO_KNOWLEDGE_FOUND = (
    "Für dieses Anliegen liegen keine ausreichenden Informationen "
    "in der Wissensbasis vor. Eine manuelle Prüfung ist erforderlich."
)

MSG_INSUFFICIENT_CONFIDENCE = (
    "Ihr Anliegen konnte automatisiert nicht ausreichend sicher bearbeitet "
    "werden. Es wird daher zur manuellen Prüfung weitergeleitet.\n\n"
    "Hinweis: Es wurde bewusst kein fachlicher Antwortentwurf erzeugt, "
    "um fehlerhafte oder unbelegte Aussagen zu vermeiden."
)

MSG_SECURITY_BLOCKED = (
    "Ihre Nachricht enthält Inhalte, die als potenziell sicherheitskritisch "
    "erkannt wurden. Eine automatische Bearbeitung erfolgt daher nicht. "
    "Das Anliegen wird zur manuellen Prüfung weitergeleitet."
)

MSG_SECURITY_BLOCKED_ESCALATED = (
    "Ihre Nachricht enthält Inhalte, die als potenziell sicherheitskritisch "
    "erkannt wurden. Eine automatische Bearbeitung erfolgt daher nicht. "
    "Das Anliegen wird zur manuellen Prüfung eskaliert."
)

MSG_ESCALATION_REQUIRED = (
    "Ihr Anliegen wurde als rechtlich, organisatorisch oder datenschutzbezogen "
    "sensibler Fall erkannt. Eine automatische inhaltliche Bearbeitung erfolgt "
    "nicht. Das Anliegen wird zur qualifizierten manuellen Prüfung eskaliert."
)

MSG_TECHNICAL_ERROR = (
    "Für dieses Anliegen konnte aufgrund eines technischen Fehlers "
    "kein belastbarer Antwortentwurf erstellt werden. Das Anliegen "
    "sollte fachlich geprüft und manuell beantwortet werden."
)


# --- Reflection Messages (reflection.py) ---

REFL_UNKNOWN_TEAM = "Das System konnte kein zuständiges Team sicher bestimmen."
REFL_LOW_CONFIDENCE = "Die ursprüngliche Klassifikationssicherheit war niedrig."
REFL_ADAPTIVE_RETRIEVAL = "Adaptive Retrieval wurde ausgelöst wegen: {reason}."
REFL_SELF_EVAL_ISSUE = "Self-Evaluation-Hinweis: {issue}."
REFL_CONFIDENCE_REDUCED = "Die Confidence wurde nach Self-Evaluation und Retrievalprüfung reduziert."


# --- Self-Evaluation Phrasen (self_evaluation.py) ---

PHRASE_MANUAL_REVIEW = "manuelle prüfung"

RISKY_PHRASES = [
    "ich vermute",
    "wahrscheinlich",
    "möglicherweise",
    "eventuell",
    "vermutlich",
    "garantiert",
    "rechtlich verbindlich"
]


# --- Evaluation Reasons (answer_completeness.py) ---

DEFAULT_NO_REASON = "Keine Begründung vorhanden."

EVAL_REASON_INJECTION = "Keine inhaltliche Bewertung, da eine Prompt Injection erkannt wurde."
EVAL_REASON_INJECTION_DETAILS = "Keine inhaltliche Bewertung, da eine Prompt Injection erkannt wurde. Details: {details}"
EVAL_REASON_BLOCKED = "Keine Bewertung, da der Fall blockiert wurde."
EVAL_REASON_NO_ANSWER = "Keine Bewertung, da ein No-Answer-Fall ausgelöst wurde."
EVAL_REASON_NO_DRAFT = "Keine Bewertung, da kein Antwortentwurf vorhanden ist."
EVAL_REASON_EXCEPTION = "Bewertung konnte nicht durchgeführt werden: {exc_type}: {exc_msg}"
EVAL_REASON_POLICY_ANSWER = "Keine inhaltliche Vollständigkeitsbewertung, da die fachliche Antwort durch eine Policy-Antwort ersetzt wurde."

# --- Sicherheitsprüfung ---
INJECTION_ERROR_REASON = "Fehler bei der Prüfung"
LOG_INJECTION_ERROR = "Fehler bei Injection Detection: {exc}"

# --- Klassifikation & Routing ---
MSG_NO_KEYWORDS = "Keine Keywords definiert."
MSG_NO_SERVICES = "Keine Leistungen definiert."
DISPLAY_NAME_UNKNOWN = "Unbekannt"

# --- Matrix-Bau (classifier.py) ---
MATRIX_LINE_TEAM = "Department-/Fachbereich-ID: {team_id}"
MATRIX_LINE_NAME = "Name: {name}"
MATRIX_LINE_DEPT = "Fachbereich: {department}"
MATRIX_LINE_DESC = "Beschreibung: {description}"
MATRIX_LINE_SERV = "Typische Leistungen: {service_text}"
MATRIX_LINE_KEYS = "Keywords und ähnliche Anliegen: {keyword_text}"
MATRIX_LINE_MAIL = "Routing-E-Mail: {email}"
MATRIX_SEPARATOR = "\n---\n"

# --- Keyword-Regeln (classifier.py) ---
RULE_IF_MATCH = "- Wenn das Bürgeranliegen inhaltlich zu einem dieser Begriffe oder Leistungen passt: {terms}"
RULE_THEN_TEAM = "  Dann ist vorrangig der Fachbereich '{team}' zu wählen."

# --- Log-Meldungen (api/v5_api.py) ---
REASON_SECURITY_BLOCK = "Sicherheitsblock: {reason}"

# --- Pipeline-Ausgaben (pipelines/run_v5.py) ---
PIPELINE_CASE_START = "\n[{index}/{total}] Starte Fall {case_id}"
PIPELINE_CASE_DONE = (
    "  - Fertig: response_mode={response_mode}, "
    "workflow={workflow_status}, "
    "injection_detected={injection_detected}, "
    "retrieval_k={retrieval_k}, "
    "retrieval_expanded={retrieval_expanded}\n"
    "  - completeness={completeness_label}, "
    "human_review={human_review_required}, "
    "calibrated_confidence={calibrated_confidence}\n"
    "  - Fall abgeschlossen in {case_duration:.2f} Sekunden"
)
PIPELINE_V5_SUMMARY_HEADER = "\n===== V5 Current API Pipeline =====\n"

# --- Chunking ---
DEFAULT_DOC_TITLE = "Dokument"
SECTION_TITLE_PATTERN = "Abschnitt {index}"

# --- Log-Meldungen (embeddings.py) ---
ERR_OPENAI_KEY_MISSING = "OPENAI_API_KEY nicht in der Umgebung/ .env gefunden."

# --- Kontext-Templates (answer.py / answer_completeness.py) ---
CONTEXT_CHUNK_TEMPLATE = "[Quelle: {source} | Kategorie {category}]\n{content}"
SOURCE_CONTEXT_TEMPLATE = "Quelle {index}: {source}\nKategorie: {category}\nInhalt:\n{content}"
SOURCE_LIST_HEADER = "Verwendete Quellen:"
SOURCE_LIST_ITEM = "- {source}"
SOURCE_CONTEXT_EMPTY = "Keine verwendeten Quellen vorhanden."

# --- Issue-Formatierung ---
ISSUE_RISKY_PHRASE = "risky_phrase: {phrase}"
ISSUE_HIGH_RISK_KEYWORD = "high_risk_keyword: {keyword}"

# --- Guardrails: Riskante Phrasen ---
GUARDRAIL_RISKY_PHRASES = [
    "ich vermute",
    "wahrscheinlich",
    "möglicherweise",
    "rechtlich verbindlich",
    "garantiert"
]

# --- Risk Scoring: Hochrisiko-Keywords ---
HIGH_RISK_KEYWORDS = [
    "datenschutz",
    "datenschutzbeschwerde",
    "personenbezogene daten",
    "einspruch",
    "widerspruch",
    "beschwerde",
    "dienstaufsichtsbeschwerde",
    "klage",
    "anwalt",
    "bußgeld",
    "sozialhilfe",
    "abgelehnt"
]
