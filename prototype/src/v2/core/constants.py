"""
Zentrale Sammlung von Dictionary-Keys und Konstanten für den V2-Prototyp.
V2 fokussiert RAG, Quellenbindung und quellenbasierte Antwortgenerierung.
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

K_SOURCE = "source"
K_SOURCES = "sources"
K_USED_CHUNKS = "used_chunks"
K_CONTENT = "content"
K_CATEGORY = "category"
K_CHUNK_ID = "chunk_id"
K_FILENAME = "filename"
K_FILEPATH = "filepath"
K_TEXT = "text"
K_DISTANCE = "distance"

K_ANSWER = "answer"
K_DRAFT_ANSWER = "draft_answer"

K_TARGET_TEAM = "target_team"
K_TARGET_EMAIL = "target_email"
K_DISPLAY_NAME = "display_name"
K_ROUTING_STATUS = "routing_status"

K_CASE_ID = "case_id"
K_GROUND_TRUTH_TEAM = "ground_truth_team"
K_PREDICTED_TEAM = "predicted_team"
K_RETRIEVED_SOURCES = "retrieved_sources"
K_USED_SOURCES = "used_sources"
K_RETRIEVED_CHUNK_IDS = "retrieved_chunk_ids"
K_HAS_SOURCES = "has_sources"
K_NO_ANSWER_TRIGGERED = "no_answer_triggered"
K_STEP_TIMINGS = "step_timings"
K_PROCESSING_TIME = "processing_time_seconds"
K_VERSION = "version"
K_TIMESTAMP = "timestamp"
K_TOP1_CORRECT = "top1_correct"
K_TOP3_CORRECT = "top3_correct"
K_UNKNOWN_PREDICTED = "unknown_predicted"

K_FEATURES = "features"
K_CHUNKING = "chunking"
K_RETRIEVAL = "retrieval"
K_EMBEDDING_MODEL = "embedding_model"
K_EMBEDDING_PROVIDER= "embedding_provider"
K_CONFIG_FILE = "config_file"
K_TESTSET_FILE = "testset_file"
K_KNOWLEDGE_BASE = "knowledge_base"
K_OUTPUT_FILES = "output_files"
K_RESULTS_CSV = "results_csv"
K_METRICS_JSON = "metrics_json"
K_CONFIG_JSON = "config_json"

M_TOP1_ACCURACY = "top1_accuracy"
M_TOP3_ACCURACY = "top3_accuracy"
M_UNKNOWN_RATE = "unknown_rate"
M_SOURCE_COVERAGE = "source_coverage"
M_NO_ANSWER_RATE = "no_answer_rate"
M_AVG_CONFIDENCE = "avg_confidence"
M_TOTAL_CASES = "total_cases"

T_CLASSIFICATION = "classification"
T_ROUTING = "routing"
T_RETRIEVAL = "retrieval"
T_GENERATION = "answer_generation"

K_ROLE = "role"
ROLE_SYSTEM = "system"
ROLE_USER = "user"

V_UNKNOWN = "unknown"
V_ROUTED = "routed"
V_MANUAL_REVIEW = "manual_review"

PIPELINE_VERSION_V2 = "v2_rag_with_sources"

V2_FEATURE_LLM_CLASSIFICATION = "llm_classification"
V2_FEATURE_RAG_RETRIEVAL = "rag_retrieval"
V2_FEATURE_SOURCE_BASED_ANSWER = "source_based_answer_generation"
V2_FEATURE_SOURCE_EXPORT = "source_export"

V2_PIPELINE_FEATURES = [
    V2_FEATURE_LLM_CLASSIFICATION,
    V2_FEATURE_RAG_RETRIEVAL,
    V2_FEATURE_SOURCE_BASED_ANSWER,
    V2_FEATURE_SOURCE_EXPORT,
]

CLASSIFICATION_UNKNOWN_THRESHOLD = 0.6
RETRIEVAL_K = 3
DEFAULT_CHUNK_MAX_CHARS = 700
DTYPE_FLOAT32 = "float32"
SEP_NL2 = "\n\n"
CHUNK_ID_SEP = "::"

CHUNKING_STRATEGY = "structure_chunking"
DIR_V2 = "v2"
FILENAME_V2_RESULTS_CSV = "v2_results.csv"
FILENAME_V2_METRICS_JSON = "v2_metrics.json"
FILENAME_V2_CONFIG_JSON = "v2_config.json"
