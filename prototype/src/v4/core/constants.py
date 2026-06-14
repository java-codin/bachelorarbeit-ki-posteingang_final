"""
Zentrale Sammlung von Dictionary-Keys und Konstanten für den V4-Prototyp.
Dies verhindert Tippfehler und hält Risk-Scoring, Policies und Workflow konsistent.
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

# --- Sicherheits-Prüfung (Injection Detection) ---
K_DETECTED = "detected"
K_MATCHED_PATTERNS = "matched_patterns"

# --- Retrieval & Quellen ---
K_RETRIEVED_SOURCES = "retrieved_sources"
K_SOURCES = "sources"
K_USED_SOURCES = "used_sources"
K_USED_CHUNKS = "used_chunks"
K_SOURCE = "source"
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
K_SCORE = "score"
K_VALID = "valid"
K_FLAGS = "flags"
K_REQUIRED = "required"
K_REASONS = "reasons"

# --- Evaluationsmetriken ---
M_TOP1_ACCURACY = "top1_accuracy"
M_TOP3_ACCURACY = "top3_accuracy"
M_UNKNOWN_RATE = "unknown_rate"
M_HUMAN_REVIEW_RATE = "human_review_rate"
M_ESCALATION_RATE = "escalation_rate"
M_BLOCKED_RATE = "blocked_rate"
M_AUTO_DRAFT_RATE = "auto_draft_rate"
M_RESPONSE_REVIEW_RATE = "response_review_rate"
M_RESPONSE_NO_ANSWER_RATE = "response_no_answer_rate"
M_RESPONSE_ESCALATION_RATE = "response_escalation_rate"
M_RESPONSE_BLOCKED_RATE = "response_blocked_rate"
M_AVG_RISK_SCORE = "avg_risk_score"
M_RETRIEVED_SOURCE_COVERAGE = "retrieved_source_coverage"
M_USED_SOURCE_COVERAGE = "used_source_coverage"
M_INJECTION_DETECTION_RATE = "injection_detection_rate"
M_GUARDRAIL_TRIGGER_RATE = "guardrail_trigger_rate"
M_TOTAL_CASES = "total_cases"

# --- Workflow & Status ---
K_RESPONSE_MODE = "response_mode"
K_WORKFLOW_STATUS = "workflow_status"
K_RISK_SCORE = "risk_score"
K_RISK_REASONS = "risk_reasons"
K_NO_ANSWER_TRIGGERED = "no_answer_triggered"
K_INJECTION_DETECTED = "injection_detected"
K_INJECTION_PATTERNS = "injection_patterns"
K_HUMAN_REVIEW_REQUIRED = "human_review_required"
K_HUMAN_REVIEW_REASONS = "human_review_reasons"
K_ESCALATION_REQUIRED = "escalation_required"
K_ALLOW_GENERATION = "allow_generation"
K_GUARDRAIL_TRIGGERED = "guardrail_triggered"
K_GUARDRAIL_FLAGS = "guardrail_flags"

# --- Routing ---
K_TARGET_TEAM = "target_team"
K_TARGET_EMAIL = "target_email"
K_DISPLAY_NAME = "display_name"
K_ROUTING_STATUS = "routing_status"

# --- API & Metadaten ---
K_CASE_ID = "case_id"
K_GROUND_TRUTH_TEAM = "ground_truth_team"
K_PREDICTED_TEAM = "predicted_team"
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
K_UNKNOWN_PREDICTED = "unknown_predicted"
K_AUDIT_TIMESTAMP = "audit_timestamp"

# --- Pipeline Export & Experiment Metadata ---
K_FEATURES = "features"
K_CONFIG_FILE = "config_file"
K_TESTSET_FILE = "testset_file"
K_KNOWLEDGE_BASE = "knowledge_base"
K_RETRIEVAL_K = "retrieval_k"
K_WORKFLOW_STATES = "workflow_states"
K_THRESHOLDS = "thresholds"
K_OUTPUT_FILES = "output_files"
K_RESULTS_CSV = "results_csv"
K_METRICS_JSON = "metrics_json"
K_MONITORING_CSV = "monitoring_csv"
K_AUDIT_LOG_JSONL = "audit_log_jsonl"

K_THRESHOLD_CLASSIFICATION_UNKNOWN = "classification_unknown"
K_THRESHOLD_CLASSIFICATION_REVIEW = "classification_review"
K_THRESHOLD_RISK_REVIEW = "risk_review"
K_THRESHOLD_RISK_ESCALATION = "risk_escalation"
K_THRESHOLD_GUARDRAIL_MIN_LENGTH = "guardrail_min_answer_length"

# --- Step Timings Namen ---
T_INJECTION = "injection_detection"
T_CLASSIFICATION = "classification"
T_ROUTING = "routing"
T_RETRIEVAL = "retrieval"
T_GENERATION = "answer_generation"
T_EVALUATION = "evaluation"

# --- Werte & Konstanten (Values) ---
V_UNKNOWN = "unknown"

# LLM Rollen
ROLE_SYSTEM = "system"
ROLE_USER = "user"
K_ROLE = "role"

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

# Gemeinsame Issue- & Grund-Bezeichner
ISSUE_ANSWER_TOO_SHORT = "answer_too_short"
ISSUE_HIGH_RISK_KEYWORD = "high_risk_keyword: {keyword}"
ISSUE_MISSING_SOURCES = "missing_sources"
ISSUE_RISKY_PHRASE_PREFIX = "risky_phrase"

REASON_UNKNOWN_TEAM = "unknown_team"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_PROMPT_INJECTION = "prompt_injection_detected"
REASON_NO_ANSWER_TRIGGERED = "no_answer_triggered"
REASON_GUARDRAIL_FLAGS = "guardrail_flags"

# --- Pipeline Metadaten ---
PIPELINE_VERSION_V4 = "v4_production_workflow_simulation"

V4_FEATURE_PROMPT_INJECTION_DETECTION = "prompt_injection_detection"
V4_FEATURE_NO_ANSWER_MECHANISM = "no_answer_mechanism"
V4_FEATURE_ANSWER_GUARDRAILS = "answer_guardrails"
V4_FEATURE_RISK_SCORING = "risk_scoring"
V4_FEATURE_RESPONSE_POLICY = "response_policy"
V4_FEATURE_HUMAN_REVIEW = "human_review"
V4_FEATURE_WORKFLOW_STATUS = "workflow_status"
V4_FEATURE_MONITORING = "monitoring"
V4_FEATURE_AUDIT_LOGGING = "audit_logging"

V4_PIPELINE_FEATURES = [
    V4_FEATURE_PROMPT_INJECTION_DETECTION,
    V4_FEATURE_NO_ANSWER_MECHANISM,
    V4_FEATURE_ANSWER_GUARDRAILS,
    V4_FEATURE_RISK_SCORING,
    V4_FEATURE_RESPONSE_POLICY,
    V4_FEATURE_HUMAN_REVIEW,
    V4_FEATURE_WORKFLOW_STATUS,
    V4_FEATURE_MONITORING,
    V4_FEATURE_AUDIT_LOGGING,
]

V4_WORKFLOW_STATES = [
    STATUS_AUTO,
    STATUS_HUMAN,
    STATUS_ESCALATED,
    STATUS_BLOCKED,
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

RISK_ESCALATION_THRESHOLD = 7
RISK_REVIEW_THRESHOLD = 4

# --- Technische Konstanten ---
DTYPE_FLOAT32 = "float32"
DIR_V4 = "v4"
RETRIEVAL_K = 3
DEFAULT_CHUNK_MAX_CHARS = 700
CHUNK_ID_SEP = "::"
SEP_NL2 = "\n\n"
FILENAME_V4_RESULTS_CSV = "v4_results.csv"
FILENAME_V4_METRICS_JSON = "v4_metrics.json"
FILENAME_V4_CONFIG_JSON = "v4_config.json"
FILENAME_V4_MONITORING_CSV = "monitoring.csv"
FILENAME_V4_AUDIT_LOG_JSONL = "audit_log.jsonl"
