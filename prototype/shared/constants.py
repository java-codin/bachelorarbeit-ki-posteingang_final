"""
Globale technische Konstanten des Prototyps.

Dieses Modul enthält nur prototypweit gültige Basiswerte:
- technische Standardwerte
- Verzeichnis- und Dateinamen
- globale Konfigurations- und Testdatenkontexte
- gemeinsame Output- und Laufzeitdateien
- Umgebungsvariablen für externe Infrastruktur

Fachliche Workflow-Status, UI-Texte, Pipeline-Dict-Keys und
versionsspezifische Entscheidungslogik bleiben in den jeweiligen Modulen.
"""

# --- Allgemeine technische Konstanten ---

ENCODING_UTF8 = "utf-8"
ENC_UTF8 = ENCODING_UTF8

JSON_INDENT = 2

EXT_MD = "*.md"
EXT_CSV = "*.csv"
EXT_JSON = "*.json"
EXT_JSONL = "*.jsonl"
EXT_YAML = "*.yaml"


# --- Umgebungsdateien und Umgebungsvariablen ---

ENV_FILE_NAME = ".env"

ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_EMBEDDING_MODEL = "OPENAI_EMBEDDING_MODEL"
ENV_EMBEDDING_PROVIDER = "EMBEDDING_PROVIDER"
ENV_LOCAL_EMBEDDING_MODEL = "LOCAL_EMBEDDING_MODEL"
ENV_ACTIVE_MODEL_PROFILE = "ACTIVE_MODEL_PROFILE"
ENV_MODEL_PROFILE_ID = "MODEL_PROFILE_ID"
ENV_MODEL_PROFILE_LABEL = "MODEL_PROFILE_LABEL"

ENV_LLM_PROVIDER = "LLM_PROVIDER"
ENV_OLLAMA_MODEL = "OLLAMA_MODEL"
ENV_OLLAMA_REQUEST_TIMEOUT_SECONDS = "OLLAMA_REQUEST_TIMEOUT_SECONDS"
ENV_OPENAI_MODEL = "OPENAI_MODEL"
ENV_TEMPERATURE = "TEMPERATURE"

ENV_MAILPIT_API_URL = "MAILPIT_API_URL"
ENV_MAILPIT_SMTP_HOST = "MAILPIT_SMTP_HOST"
ENV_MAILPIT_SMTP_PORT = "MAILPIT_SMTP_PORT"
ENV_MAILPIT_INBOX_ADDRESS = "MAILPIT_INBOX_ADDRESS"

ENV_CENTRAL_POSTBOX_NAME = "CENTRAL_POSTBOX_NAME"
ENV_CENTRAL_POSTBOX_ADDRESS = "CENTRAL_POSTBOX_ADDRESS"

ENV_OPERATIONS_VERSION = "OPERATIONS_VERSION"
ENV_EMAIL_POLL_SECONDS = "EMAIL_POLL_SECONDS"

ENV_PROTOTYPE_LOG_LEVEL = "PROTOTYPE_LOG_LEVEL"


# --- Standardwerte für Umgebungsvariablen ---

DEFAULT_MAILPIT_API_URL = "http://localhost:8025/api/v1"
DEFAULT_MAILPIT_SMTP_HOST = "localhost"
DEFAULT_MAILPIT_SMTP_PORT = "1025"
DEFAULT_MAILPIT_INBOX_ADDRESS = "buergeranliegen@kommune.test"

DEFAULT_CENTRAL_POSTBOX_NAME = "KI-Posteingang Musterstadt"
DEFAULT_CENTRAL_POSTBOX_ADDRESS = "buergeranliegen@kommune.test"

DEFAULT_OPERATIONS_VERSION = "V5"
DEFAULT_EMAIL_POLL_SECONDS = "10"

DEFAULT_LOG_LEVEL = "INFO"


# --- Verzeichnisse im Prototyp ---

DIR_APPS = "apps"
DIR_CONFIG = "config"
DIR_DASHBOARDS = "dashboards"
DIR_DATA = "data"
DIR_EXPERIMENTS = "experiments"
DIR_INQUIRIES = "inquiries"
DIR_KNOWLEDGE_BASE = "knowledge_base"
DIR_MODELS = "models"
DIR_OUTPUTS = "outputs"
DIR_PIPELINES = "pipelines"
DIR_SHARED = "shared"
DIR_SRC = "src"
DIR_TESTS = "tests"

DIR_CACHE = "cache"
DIR_PYCACHE = "__pycache__"

DIR_OPERATIONS_OUTPUTS = "operations"
DIR_CHUNKING_EXPERIMENT = "chunking_experiment"


# --- Versions- und Output-Verzeichnisse ---

DIR_V0 = "v0"
DIR_V0_ALPHA = "v0_alpha"
DIR_V1 = "v1"
DIR_V2 = "v2"
DIR_V3 = "v3"
DIR_V4 = "v4"
DIR_V5 = "v5"


# --- Konfigurationsdateien ---

FILENAME_MUNICIPALITY_CONFIG = "municipality.yaml"
FILENAME_MUNICIPALITY_V2_CONFIG = "municipality_v2.yaml"
FILENAME_MODEL_PROFILES = "model_profiles.yaml"


# --- Testset-Dateien ---

FILENAME_INQUIRIES_20 = "inquiries_20.csv"
FILENAME_INQUIRIES_80 = "inquiries_80.csv"


# --- Knowledge-Base-Kontext ---

FILENAME_README = "readme.md"

KNOWLEDGE_BASE_VERSION_V2 = "v2"
KNOWLEDGE_BASE_VERSION_V3 = "v3"
KNOWLEDGE_BASE_VERSION_V4 = "v4"
KNOWLEDGE_BASE_VERSION_V5 = "v5"


# --- Allgemeine Output-Dateien ---

FILENAME_RESULTS_CSV = "results.csv"
FILENAME_SUMMARY_CSV = "summary.csv"
FILENAME_METRICS_JSON = "metrics.json"
FILENAME_MONITORING_JSON = "monitoring.json"
FILENAME_MONITORING_CSV = "monitoring.csv"
FILENAME_CONFIG_JSON = "config.json"
FILENAME_EXPERIMENT_CONFIG_JSON = "experiment_config.json"
FILENAME_AUDIT_LOG_JSONL = "audit_log.jsonl"
FILENAME_AUDIT_DOT_LOG_JSONL = "audit.log.jsonl"


# --- Versionsspezifische Output-Dateien ---

FILENAME_V0_RESULTS_CSV = "v0_results.csv"
FILENAME_V0_ALPHA_RESULTS_CSV = "v0_alpha_results.csv"

FILENAME_V1_RESULTS_CSV = "v1_results.csv"
FILENAME_V1_METRICS_JSON = "v1_metrics.json"
FILENAME_V1_CONFIG_JSON = "v1_config.json"

FILENAME_V2_RESULTS_CSV = "v2_results.csv"
FILENAME_V2_METRICS_JSON = "v2_metrics.json"
FILENAME_V2_CONFIG_JSON = "v2_config.json"

FILENAME_V3_RESULTS_CSV = "v3_results.csv"
FILENAME_V3_METRICS_JSON = "v3_metrics.json"
FILENAME_V3_CONFIG_JSON = "v3_config.json"
FILENAME_V3_AUDIT_LOG_JSONL = "audit_log.jsonl"

FILENAME_V4_RESULTS_CSV = "v4_results.csv"
FILENAME_V4_METRICS_JSON = "v4_metrics.json"
FILENAME_V4_CONFIG_JSON = "v4_config.json"
FILENAME_V4_MONITORING_CSV = "monitoring.csv"
FILENAME_V4_AUDIT_LOG_JSONL = "audit_log.jsonl"

FILENAME_V5_RESULTS_CSV = "v5_results.csv"
FILENAME_V5_METRICS_JSON = "v5_metrics.json"
FILENAME_V5_CONFIG_JSON = "v5_config.json"
FILENAME_V5_AUDIT_LOG_JSONL = "audit.log.jsonl"


# --- Operations-Store-Dateien ---

FILENAME_CASES_STORE = "cases.json"
FILENAME_PROCESSED_EMAILS_STORE = "processed_emails.json"
FILENAME_WORKER_STATUS_STORE = "worker_status.json"

FILENAME_METRICS = "metrics.json"
FILENAME_MONITORING = "monitoring.json"
FILENAME_DASHBOARD_METRICS = "dashboard_metrics.json"
FILENAME_LAST_RUN = "last_run.json"
FILENAME_RUNTIME_STATE = "runtime_state.json"


# --- Chunking-Experiment-Dateien ---

FILENAME_CHUNKING_RESULTS_CSV = "results.csv"
FILENAME_CHUNKING_METRICS_JSON = "metrics.json"
FILENAME_CHUNKING_SUMMARY_CSV = "summary.csv"
FILENAME_CHUNKING_EXPERIMENT_CONFIG_JSON = "experiment_config.json"


# --- Modelle und Embeddings ---

MODEL_ALL_MINILM_L6_V2 = "all-MiniLM-L6-v2"

PROVIDER_LOCAL = "local"
PROVIDER_ONLINE = "online"
PROVIDER_OPENAI = "openai"

DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

LLM_PROVIDER_OLLAMA = "ollama"
LLM_PROVIDER_OPENAI = "openai"

DEFAULT_LLM_PROVIDER = LLM_PROVIDER_OLLAMA
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_LLM_TEMPERATURE = "0"
DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS = "120"


# --- Logging ---

LOG_FORMAT_DEFAULT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT_DEFAULT = "%Y-%m-%d %H:%M:%S"


# --- Dateisperren und Polling ---

LOCK_TIMEOUT_SECONDS = 5
LOCK_POLL_SECONDS = 0.1

REQUEST_TIMEOUT_SECONDS = 10


# --- Häufige technische Trennzeichen ---

SEP_NL = "\n"
SEP_NL2 = "\n\n"
SEP_SENTENCE = ". "
SEP_DASHES = "\n---\n"
SEP_DASHES_EXT = "\n\n---\n\n"
CHUNK_ID_SEP = "::"


# --- Gemeinsame Typ-/Formatwerte ---

DTYPE_FLOAT32 = "float32"


# --- Gemeinsame Export-Metadaten-Keys ---

K_CONFIG_FILE = "config_file"
K_TESTSET_FILE = "testset_file"
K_KNOWLEDGE_BASE = "knowledge_base"
K_OUTPUT_FILES = "output_files"
K_RESULTS_CSV = "results_csv"
K_METRICS_JSON = "metrics_json"
K_CONFIG_JSON = "config_json"
K_MONITORING_CSV = "monitoring_csv"
K_AUDIT_LOG_JSONL = "audit_log_jsonl"
K_SUMMARY_CSV = "summary_csv"
K_EXPERIMENT_CONFIG_JSON = "experiment_config_json"
