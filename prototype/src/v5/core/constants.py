"""
Zentrale Sammlung von Dictionary-Keys und Konstanten für den V5-Prototyp.
Dies verhindert Tippfehler und erleichtert das Refactoring der Datenstrukturen.
"""

# --- Klassifikation (Classifier) ---
# Historische API-Feldnamen:
# In v5 meinen top_team/predicted_team/target_team fachlich den zuständigen
# Fachbereich bzw. das Department. Die Namen bleiben für CSV-, UI- und
# Evaluationskompatibilität erhalten.
K_TOP_TEAM = "top_team"
K_TOP3 = "top3"
K_CONFIDENCE = "confidence"
K_REASON = "reason"
K_MATCHED_SUBTEAM = "matched_subteam"
K_MATCHED_SUBTEAM_NAME = "matched_subteam_name"
K_MATCHED_SUBTEAM_CONFIDENCE = "matched_subteam_confidence"
K_MATCHED_TEAM = "matched_team"
K_MATCHED_TEAM_NAME = "matched_team_name"
K_MATCHED_TEAM_CONFIDENCE = "matched_team_confidence"

# --- Konfiguration (Config YAML) ---
K_DEPARTMENT_GROUPS = "department_groups"
K_DEPARTMENTS = "departments"
K_DIVISIONS = "divisions"
# In v5 bezeichnet K_TEAMS echte Teams innerhalb eines Bereichs, nicht die
# oberste Routing-Ebene.
K_TEAMS = "teams"
K_NAME = "name"
K_DEPARTMENT = "department"
K_DESCRIPTION = "description"
K_KEYWORDS = "keywords"
K_SERVICES = "services"
K_SUBTEAMS = "subteams"
K_EMAIL = "email"

# --- Sicherheits-Prüfung (Injection Detection) ---
K_DETECTED = "detected"
K_REASONING = "reasoning"
K_MATCHED_PATTERNS = "matched_patterns"

# --- Retrieval & Quellen ---
K_RETRIEVED_CHUNKS = "retrieved_chunks"
K_RETRIEVED_SOURCES = "retrieved_sources"
K_SOURCES = "sources"
K_USED_SOURCES = "used_sources"
K_USED_CHUNKS = "used_chunks"
K_SOURCE = "source"
K_SOURCE_ID = "source_id"
K_USED_SOURCE_IDS = "used_source_ids"
K_USED_SOURCE_DETAILS = "used_source_details"
K_INVALID_SOURCE_IDS = "invalid_source_ids"
K_CONTENT = "content"
K_CATEGORY = "category"
K_CHUNK_ID = "chunk_id"
K_FILENAME = "filename"
K_FILEPATH = "filepath"
K_TITLE = "title"
K_SECTION_TITLE = "section_title"
K_SECTION_INDEX = "section_index"
K_CHUNK_INDEX = "chunk_index"
K_TEXT = "text"
K_DISTANCE = "distance"
K_EXPAND = "expand"
K_REASONS = "reasons"
K_RETRIEVAL_EXPANDED = "retrieval_expanded"
K_RETRIEVAL_REASONS = "retrieval_reasons"
K_RETRIEVAL_K = "retrieval_k"

# --- Antwort-Generierung ---
K_ANSWER = "answer"
K_DRAFT_ANSWER = "draft_answer"

# --- Evaluation & Vollständigkeit ---
K_SCORE = "score"
K_PASSED = "passed"
K_ISSUES = "issues"
K_VALID = "valid"
K_FLAGS = "flags"
K_REQUIRED = "required"
K_COMPLETENESS_SCORE = "answer_completeness_score"
K_COMPLETENESS_LABEL = "answer_completeness_label"
K_COMPLETENESS_REASON = "answer_completeness_reason"
K_COVERED_ASPECTS = "covered_aspects"
K_MISSING_ASPECTS = "missing_aspects"
K_UNCERTAIN_ASPECTS = "uncertain_aspects"
K_HUMAN_REQUIRED = "requires_human_completion"

# --- Workflow & Status ---
K_RESPONSE_MODE = "response_mode"
K_WORKFLOW_STATUS = "workflow_status"
K_RISK_SCORE = "risk_score"
K_RISK_REASONS = "risk_reasons"
K_NO_ANSWER_TRIGGERED = "no_answer_triggered"
K_INJECTION_DETECTED = "injection_detected"
K_INJECTION_REASONING = "injection_reasoning"
K_INJECTION_PATTERNS = "injection_patterns"
K_HUMAN_REVIEW_REQUIRED = "human_review_required"
K_HUMAN_REVIEW_REASONS = "human_review_reasons"
K_ESCALATION_REQUIRED = "escalation_required"
K_ALLOW_GENERATION = "allow_generation"
K_SELF_EVAL_PASSED = "self_evaluation_passed"
K_SELF_EVAL_ISSUES = "self_evaluation_issues"
K_REFLECTION_TRIGGERED = "reflection_triggered"
K_REFLECTIONS = "reflections"
K_GUARDRAIL_TRIGGERED = "guardrail_triggered"
K_GUARDRAIL_FLAGS = "guardrail_flags"
K_CALIBRATED_CONFIDENCE = "calibrated_confidence"

# --- Routing ---
K_TARGET_TEAM = "target_team"
K_TARGET_DEPARTMENT = "target_department"
K_TARGET_DEPARTMENT_NAME = "target_department_name"
K_TARGET_EMAIL = "target_email"
K_DISPLAY_NAME = "display_name"
K_ROUTING_STATUS = "routing_status"

# --- API & Metadaten ---
K_CASE_ID = "case_id"
K_GROUND_TRUTH_TEAM = "ground_truth_team"
K_PREDICTED_TEAM = "predicted_team"
K_PREDICTED_DEPARTMENT = "predicted_department"
K_PREDICTED_DEPARTMENT_NAME = "predicted_department_name"
K_HAS_RETRIEVED_SOURCES = "has_retrieved_sources"
K_HAS_USED_SOURCES = "has_used_sources"
K_RETRIEVED_CHUNK_IDS = "retrieved_chunk_ids"
K_USED_CHUNK_IDS = "used_chunk_ids"
K_POLICY_ALLOWS_GENERATION = "policy_allows_generation"
K_STEP_TIMINGS = "step_timings"
K_PROCESSING_TIME = "processing_time_seconds"
K_VERSION = "version"
K_TIMESTAMP = "timestamp"
K_TOP1_CORRECT = "top1_correct"
K_TOP3_CORRECT = "top3_correct"
K_AUDIT_TIMESTAMP = "audit_timestamp"

# --- Pipeline Export & Experiment Metadata ---
K_FEATURES = "features"
K_CONFIG_FILE = "config_file"
K_TESTSET_FILE = "testset_file"
K_KNOWLEDGE_BASE = "knowledge_base"
K_INITIAL_RETRIEVAL_K = "initial_retrieval_k"
K_EXPANDED_RETRIEVAL_K = "expanded_retrieval_k"
K_THRESHOLDS = "thresholds"
K_OUTPUT_FILES = "output_files"
K_RESULTS_CSV = "results_csv"
K_METRICS_JSON = "metrics_json"
K_AUDIT_LOG_JSONL = "audit_log_jsonl"

K_THRESHOLD_CLASSIFICATION_UNKNOWN = "classification_unknown"
K_THRESHOLD_CLASSIFICATION_REVIEW = "classification_review"
K_THRESHOLD_RISK_REVIEW = "risk_review"
K_THRESHOLD_RISK_ESCALATION = "risk_escalation"
K_THRESHOLD_ANSWER_COMPLETENESS_MEDIUM = "answer_completeness_medium"
K_THRESHOLD_ANSWER_COMPLETENESS_HIGH = "answer_completeness_high"
K_THRESHOLD_ANSWER_COMPLETENESS_REVIEW = "answer_completeness_review"

# --- Step Timings Namen ---
T_INJECTION = "injection_detection"
T_CLASSIFICATION = "classification"
T_ROUTING = "routing"
T_RETRIEVAL = "retrieval"
T_GENERATION = "answer_generation"
T_EVALUATION = "evaluation"
T_COMPLETENESS = "answer_completeness"

# --- Werte & Konstanten (Values) ---
V_UNKNOWN = "unknown"

# LLM Rollen
ROLE_SYSTEM = "system"
ROLE_USER = "user"
K_ROLE = "role"
K_CONTENT_MSG = "content"

# Response Modes
MODE_NORMAL = "normal"
MODE_REVIEW = "review_required"
MODE_BLOCKED = "blocked"
MODE_ESCALATION = "escalation"
MODE_NO_ANSWER = "no_answer"

# Workflow Status
STATUS_AUTO = "auto_draft"
STATUS_HUMAN = "human_review"
STATUS_ESCALATED = "escalated_review"
STATUS_BLOCKED = "blocked"

# Routing Status
V_ROUTED = "routed"
V_MANUAL_REVIEW = "manual_review"

# Vollständigkeits-Labels
LABEL_HIGH = "high"
LABEL_MEDIUM = "medium"
LABEL_LOW = "low"
LABEL_NONE = "none"

# Gemeinsame Issue- & Grund-Bezeichner
ISSUE_ANSWER_TOO_SHORT = "answer_too_short"
ISSUE_NO_RETRIEVED_SOURCES = "no_retrieved_sources"
ISSUE_NO_USED_SOURCES = "no_used_sources"
ISSUE_MISSING_SOURCES = "missing_sources"
ISSUE_SECURITY_BLOCK = "security_block_active"
ISSUE_MANUAL_REVIEW_MENTIONED = "manual_review_mentioned"
ISSUE_INVALID_SOURCE_IDS = "invalid_source_ids"

REASON_UNKNOWN_TEAM = "unknown_team"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_PROMPT_INJECTION = "prompt_injection_detected"
REASON_NO_ANSWER_TRIGGERED = "no_answer_triggered"
REASON_GUARDRAIL_FLAGS = "guardrail_flags"
REASON_INCOMPLETE_ANSWER = "incomplete_answer"
REASON_LOW_CLASSIFICATION_CONFIDENCE = "low_classification_confidence"
REASON_TOO_FEW_CHUNKS = "too_few_retrieved_chunks"
REASON_SELF_EVAL_FAILED = "self_evaluation_failed"

# Pipeline Metadaten
PIPELINE_VERSION_V5 = "v5_api"

V5_FEATURE_LLM_INJECTION_DETECTION = "llm_based_prompt_injection_detection"
V5_FEATURE_SECURITY_SHORT_CIRCUIT = "security_short_circuit_on_prompt_injection"
V5_FEATURE_ADAPTIVE_RETRIEVAL = "adaptive_retrieval"
V5_FEATURE_SELF_EVALUATION = "self_evaluation"
V5_FEATURE_ANSWER_COMPLETENESS = "answer_completeness_evaluation"
V5_FEATURE_RISK_SCORING = "risk_scoring"
V5_FEATURE_RESPONSE_POLICY_MODES = "response_policy_modes"
V5_FEATURE_HUMAN_OVERSIGHT_WORKFLOW = "human_oversight_workflow"
V5_FEATURE_CONFIDENCE_CALIBRATION = "confidence_calibration"
V5_FEATURE_REFLECTION = "reflection"
V5_FEATURE_SOURCE_ID_GROUNDING = "source_id_grounding"
V5_FEATURE_INVALID_SOURCE_ID_GUARDRAIL = "invalid_source_id_guardrail"
V5_FEATURE_OFFICIAL_CLOSING_POSTPROCESSING = "official_closing_postprocessing"
V5_FEATURE_PRIVACY_PRESERVING_AUDIT_LOG = "privacy_preserving_audit_log"

# --- Evaluationsmetriken ---

M_TOP1_ACCURACY = "top1_accuracy"
M_TOP3_ACCURACY = "top3_accuracy"
M_UNKNOWN_RATE = "unknown_rate"
M_HUMAN_REVIEW_RATE = "human_review_rate"
M_ESCALATION_RATE = "escalation_rate"
M_BLOCKED_RATE = "blocked_rate"
M_AUTO_DRAFT_RATE = "auto_draft_rate"
M_AVG_RISK_SCORE = "avg_risk_score"
M_RETRIEVED_SOURCE_COVERAGE = "retrieved_source_coverage"
M_USED_SOURCE_COVERAGE = "used_source_coverage"
M_AVG_COMPLETENESS_SCORE = "avg_completeness_score"
M_TOTAL_CASES = "total_cases"

V5_PIPELINE_FEATURES = [
    V5_FEATURE_LLM_INJECTION_DETECTION,
    V5_FEATURE_SECURITY_SHORT_CIRCUIT,
    V5_FEATURE_ADAPTIVE_RETRIEVAL,
    V5_FEATURE_SELF_EVALUATION,
    V5_FEATURE_ANSWER_COMPLETENESS,
    V5_FEATURE_RISK_SCORING,
    V5_FEATURE_RESPONSE_POLICY_MODES,
    V5_FEATURE_HUMAN_OVERSIGHT_WORKFLOW,
    V5_FEATURE_CONFIDENCE_CALIBRATION,
    V5_FEATURE_REFLECTION,
    V5_FEATURE_SOURCE_ID_GROUNDING,
    V5_FEATURE_INVALID_SOURCE_ID_GUARDRAIL,
    V5_FEATURE_OFFICIAL_CLOSING_POSTPROCESSING,
    V5_FEATURE_PRIVACY_PRESERVING_AUDIT_LOG,
]

# --- Quality Thresholds ---
MIN_GUARDRAIL_ANSWER_LENGTH = 30
CLASSIFICATION_UNKNOWN_THRESHOLD = 0.6
CLASSIFICATION_REVIEW_THRESHOLD = 0.75

# --- Risk Scoring ---
RISK_WEIGHT_HIGH_RISK_KEYWORD = 3
RISK_WEIGHT_UNKNOWN_TEAM = 2
RISK_WEIGHT_LOW_CONFIDENCE = 2
RISK_WEIGHT_PROMPT_INJECTION = 5
RISK_WEIGHT_NO_ANSWER = 2
RISK_WEIGHT_GUARDRAIL_FLAGS = 2
RISK_WEIGHT_INCOMPLETE_ANSWER = 2

RISK_ESCALATION_THRESHOLD = 7
RISK_REVIEW_THRESHOLD = 4

ANSWER_COMPLETENESS_MIN_SCORE = 0.0
ANSWER_COMPLETENESS_LOW_EXAMPLE_SCORE = 0.2
ANSWER_COMPLETENESS_MEDIUM_THRESHOLD = 0.5
ANSWER_COMPLETENESS_HIGH_THRESHOLD = 0.8
ANSWER_COMPLETENESS_MAX_SCORE = 1.0
ANSWER_COMPLETENESS_REVIEW_THRESHOLD = ANSWER_COMPLETENESS_HIGH_THRESHOLD

# --- Diagnostic Prefixes ---
ISSUE_GUARDRAIL_PREFIX = "guardrail"

# --- Technische Konstanten ---
DTYPE_FLOAT32 = "float32"
DIR_MODELS = "models"
DIR_V5 = "v5"
MODEL_NAME = "all-MiniLM-L6-v2"
FALLBACK_TEXT = " "
FILENAME_AUDIT_LOG_JSONL = "audit.log.jsonl"
FILENAME_V5_RESULTS_CSV = "v5_results.csv"
FILENAME_V5_METRICS_JSON = "v5_metrics.json"
FILENAME_V5_CONFIG_JSON = "v5_config.json"
RETRIEVAL_INITIAL_K = 3
RETRIEVAL_EXPANDED_K = 6
SEP_NL = "\n"
SEP_NL2 = "\n\n"
SEP_SENTENCE = ". "
SEP_DASHES = "\n---\n"
SEP_DASHES_EXT = "\n\n---\n\n"
CHUNK_ID_SEP = "::"
CHAR_HASH = "#"
REGEX_HEADING = r"^(#{1,6}\s+.+|\d{1,2}\.\s+.+)$"

# --- Umgebungsvariablen ---
ENV_EMBEDDING_PROVIDER = "EMBEDDING_PROVIDER"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_EMBEDDING_MODEL = "OPENAI_EMBEDDING_MODEL"

# --- Embedding Provider ---
PROVIDER_LOCAL = "local"
PROVIDER_ONLINE = "online"
PROVIDER_OPENAI = "openai"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
