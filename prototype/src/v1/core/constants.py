"""
Zentrale Sammlung von Dictionary-Keys und Konstanten für den V1-Prototyp.
V1 fokussiert LLM-basierte Klassifikation und Routing.
"""

K_TOP_TEAM = "top_team"
K_TOP3 = "top3"
K_CONFIDENCE = "confidence"
K_REASON = "reason"
K_TEAM_ID = "team_id"

K_TEAMS = "teams"
K_NAME = "name"
K_DEPARTMENT = "department"
K_DESCRIPTION = "description"
K_KEYWORDS = "keywords"
K_SERVICES = "services"
K_EMAIL = "email"

K_TARGET_TEAM = "target_team"
K_TARGET_EMAIL = "target_email"
K_DISPLAY_NAME = "display_name"
K_ROUTING_STATUS = "routing_status"

K_CASE_ID = "case_id"
K_TEXT = "text"
K_GROUND_TRUTH_TEAM = "ground_truth_team"
K_PREDICTED_TEAM = "predicted_team"
K_DRAFT_ANSWER = "draft_answer"
K_STEP_TIMINGS = "step_timings"
K_PROCESSING_TIME = "processing_time_seconds"
K_VERSION = "version"
K_TIMESTAMP = "timestamp"
K_TOP1_CORRECT = "top1_correct"
K_TOP3_CORRECT = "top3_correct"
K_UNKNOWN_PREDICTED = "unknown_predicted"

K_FEATURES = "features"
K_CONFIG_FILE = "config_file"
K_TESTSET_FILE = "testset_file"
K_OUTPUT_FILES = "output_files"
K_RESULTS_CSV = "results_csv"
K_METRICS_JSON = "metrics_json"
K_CONFIG_JSON = "config_json"

M_TOP1_ACCURACY = "top1_accuracy"
M_TOP3_ACCURACY = "top3_accuracy"
M_UNKNOWN_RATE = "unknown_rate"
M_AVG_CONFIDENCE = "avg_confidence"
M_TOTAL_CASES = "total_cases"

T_CLASSIFICATION = "classification"
T_ROUTING = "routing"
T_ANSWER_GENERATION = "answer_generation"

K_ROLE = "role"
K_CONTENT = "content"
ROLE_SYSTEM = "system"
ROLE_USER = "user"

V_UNKNOWN = "unknown"
V_ROUTED = "routed"
V_MANUAL_REVIEW = "manual_review"

PIPELINE_VERSION_V1 = "v1_llm_classification"

V1_FEATURE_LLM_CLASSIFICATION = "llm_classification"
V1_FEATURE_SEMANTIC_ROUTING = "semantic_routing"
V1_FEATURE_ROUTING_DRAFT = "routing_draft"

V1_PIPELINE_FEATURES = [
    V1_FEATURE_LLM_CLASSIFICATION,
    V1_FEATURE_SEMANTIC_ROUTING,
    V1_FEATURE_ROUTING_DRAFT,
]

CLASSIFICATION_UNKNOWN_THRESHOLD = 0.6
TOP3_LIMIT = 3

DIR_V1 = "v1"
FILENAME_V1_RESULTS_CSV = "v1_results.csv"
FILENAME_V1_METRICS_JSON = "v1_metrics.json"
FILENAME_V1_CONFIG_JSON = "v1_config.json"
