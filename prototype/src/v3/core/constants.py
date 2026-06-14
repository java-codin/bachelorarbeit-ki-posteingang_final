"""
Zentrale Sammlung von Dictionary-Keys und Konstanten für den V3-Prototyp.
Dies hält Governance-, Guardrail- und Human-Review-Logik konsistent.
"""

# --- Klassifikation (Classifier) ---
K_TOP_TEAM = "top_team"
K_TOP3 = "top3"
K_CONFIDENCE = "confidence"
K_REASON = "reason"
K_TEAM_ID = "team_id"

# --- Konfiguration (Config YAML) ---
K_TEAMS = "teams"
K_NAME = "name"
K_DEPARTMENT = "department"
K_DESCRIPTION = "description"
K_KEYWORDS = "keywords"
K_SERVICES = "services"
K_EMAIL = "email"

# --- Sicherheitsprüfung (Injection Detection) ---
K_DETECTED = "detected"
K_MATCHED_PATTERNS = "matched_patterns"

# --- Retrieval & Quellen ---
K_SOURCE = "source"
K_SOURCES = "sources"
K_USED_SOURCES = "used_sources"
K_USED_CHUNKS = "used_chunks"
K_CONTENT = "content"
K_CATEGORY = "category"
K_CHUNK_ID = "chunk_id"
K_FILENAME = "filename"
K_FILEPATH = "filepath"
K_TEXT = "text"
K_DISTANCE = "distance"

# --- Antwort-Generierung ---
K_ANSWER = "answer"
K_DRAFT_ANSWER = "draft_answer"

# --- Evaluation & Guardrails ---
K_VALID = "valid"
K_FLAGS = "flags"
K_REQUIRED = "required"
K_REASONS = "reasons"

# --- Routing ---
K_TARGET_TEAM = "target_team"
K_TARGET_EMAIL = "target_email"
K_DISPLAY_NAME = "display_name"
K_ROUTING_STATUS = "routing_status"

# --- API & Metadaten ---
K_CASE_ID = "case_id"
K_GROUND_TRUTH_TEAM = "ground_truth_team"
K_PREDICTED_TEAM = "predicted_team"
K_RETRIEVED_SOURCES = "retrieved_sources"
K_RETRIEVED_CHUNK_IDS = "retrieved_chunk_ids"
K_USED_CHUNK_IDS = "used_chunk_ids"
K_HAS_RETRIEVED_SOURCES = "has_retrieved_sources"
K_HAS_USED_SOURCES = "has_used_sources"
K_HAS_SOURCES = "has_sources"
K_INJECTION_DETECTED = "injection_detected"
K_INJECTION_PATTERNS = "injection_patterns"
K_NO_ANSWER_TRIGGERED = "no_answer_triggered"
K_GUARDRAIL_TRIGGERED = "guardrail_triggered"
K_GUARDRAIL_FLAGS = "guardrail_flags"
K_HUMAN_REVIEW_REQUIRED = "human_review_required"
K_HUMAN_REVIEW_REASONS = "human_review_reasons"
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
K_RETRIEVAL_K = "retrieval_k"
K_OUTPUT_FILES = "output_files"
K_RESULTS_CSV = "results_csv"
K_METRICS_JSON = "metrics_json"
K_CONFIG_JSON = "config_json"
K_AUDIT_LOG_JSONL = "audit_log_jsonl"

# --- Evaluationsmetriken ---
M_TOP1_ACCURACY = "top1_accuracy"
M_TOP3_ACCURACY = "top3_accuracy"
M_UNKNOWN_RATE = "unknown_rate"
M_INJECTION_DETECTION_RATE = "injection_detection_rate"
M_NO_ANSWER_RATE = "no_answer_rate"
M_GUARDRAIL_TRIGGER_RATE = "guardrail_trigger_rate"
M_HUMAN_REVIEW_RATE = "human_review_rate"
M_SOURCE_COVERAGE = "source_coverage"
M_AVG_CONFIDENCE = "avg_confidence"
M_TOTAL_CASES = "total_cases"

# --- Step-Timing-Namen ---
T_INJECTION = "injection_detection"
T_CLASSIFICATION = "classification"
T_ROUTING = "routing"
T_RETRIEVAL = "retrieval"
T_GENERATION = "answer_generation"
T_EVALUATION = "evaluation"

# --- Werte & Status ---
V_UNKNOWN = "unknown"
V_ROUTED = "routed"
V_MANUAL_REVIEW = "manual_review"

# --- LLM Rollen ---
K_ROLE = "role"
ROLE_SYSTEM = "system"
ROLE_USER = "user"

# --- Guardrail- und Review-Gründe ---
ISSUE_MISSING_SOURCES = "missing_sources"
ISSUE_ANSWER_TOO_SHORT = "answer_too_short"
ISSUE_RISKY_PHRASE = "risky_phrase: {phrase}"

REASON_UNKNOWN_TEAM = "unknown_team"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_PROMPT_INJECTION = "prompt_injection_detected"
REASON_NO_ANSWER_TRIGGERED = "no_answer_triggered"
REASON_GUARDRAIL_FLAGS = "guardrail_flags"

# --- Pipeline Metadaten ---
PIPELINE_VERSION_V3 = "v3_governance_guardrails"

V3_FEATURE_PROMPT_INJECTION_DETECTION = "prompt_injection_detection"
V3_FEATURE_NO_ANSWER_MECHANISM = "no_answer_mechanism"
V3_FEATURE_ANSWER_GUARDRAILS = "answer_guardrails"
V3_FEATURE_HUMAN_REVIEW = "human_review"
V3_FEATURE_AUDIT_LOGGING = "audit_logging"

V3_PIPELINE_FEATURES = [
    V3_FEATURE_PROMPT_INJECTION_DETECTION,
    V3_FEATURE_NO_ANSWER_MECHANISM,
    V3_FEATURE_ANSWER_GUARDRAILS,
    V3_FEATURE_HUMAN_REVIEW,
    V3_FEATURE_AUDIT_LOGGING,
]

# --- Quality Thresholds ---
MIN_GUARDRAIL_ANSWER_LENGTH = 30
CLASSIFICATION_UNKNOWN_THRESHOLD = 0.6
CLASSIFICATION_REVIEW_THRESHOLD = 0.75

# --- Technische Konstanten ---
DTYPE_FLOAT32 = "float32"
DIR_V3 = "v3"
RETRIEVAL_K = 3
DEFAULT_CHUNK_MAX_CHARS = 700
CHUNK_ID_SEP = "::"
SEP_NL2 = "\n\n"
FILENAME_V3_RESULTS_CSV = "v3_results.csv"
FILENAME_V3_METRICS_JSON = "v3_metrics.json"
FILENAME_V3_CONFIG_JSON = "v3_config.json"
FILENAME_V3_AUDIT_LOG_JSONL = "audit_log.jsonl"
