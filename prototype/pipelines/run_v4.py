"""Kommandozeilen-Runner für Pipeline v4.

Das Skript führt die risikobewusste Pipeline-Iteration aus und exportiert
Ergebnisse, Metriken, Monitoringdaten und Audit-Einträge für den Vergleich der
Human-Oversight-Mechanismen.
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd
import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.v4.core.constants as c
import src.v4.core.response_messages as m
from prototype.shared.constants import ENC_UTF8, JSON_INDENT
from prototype.shared.logging_config import configure_logging
from prototype.shared.paths import (
    DEFAULT_KNOWLEDGE_BASE_PATH,
    LEGACY_MUNICIPALITY_CONFIG_PATH,
    DEFAULT_TESTSET_PATH,
    V4_OUTPUT_DIR, knowledge_base_path_for_version,
)
from src.v4.api.v4_api import run_v4_pipeline
from src.v4.chunking.structure_chunking import create_chunks
from src.v4.evaluation import evaluate
from src.v4.knowledge_loader import load_knowledge_base
from src.v4.logging_audit import log_decision
from src.v4.monitoring import create_monitoring_dataframe
from src.v4.retrieval import build_vector_store


config_path = LEGACY_MUNICIPALITY_CONFIG_PATH
testset_path = DEFAULT_TESTSET_PATH
knowledge_base_path = knowledge_base_path_for_version("V4")
output_path = V4_OUTPUT_DIR

results_csv_path = output_path / c.FILENAME_V4_RESULTS_CSV
metrics_json_path = output_path / c.FILENAME_V4_METRICS_JSON
config_json_path = output_path / c.FILENAME_V4_CONFIG_JSON
monitoring_csv_path = output_path / c.FILENAME_V4_MONITORING_CSV
audit_log_path = output_path / c.FILENAME_V4_AUDIT_LOG_JSONL

output_path.mkdir(parents=True, exist_ok=True)
configure_logging()


def load_config(path):
    return yaml.safe_load(path.read_text(encoding=ENC_UTF8))


config = load_config(config_path)
testset = pd.read_csv(testset_path)

documents = load_knowledge_base(knowledge_base_path)
chunks = create_chunks(documents)
vector_store = build_vector_store(chunks)

results = []
total_cases = len(testset)

for index, row in testset.iterrows():
    case_start = time.time()

    print(
        m.PIPELINE_CASE_START.format(
            index=index + 1,
            total=total_cases,
            case_id=row[c.K_CASE_ID]
        )
    )

    result = run_v4_pipeline(
        inquiry_text=row[c.K_TEXT],
        config=config,
        vector_store=vector_store,
        row_metadata=row
    )

    case_duration = result.get(c.K_PROCESSING_TIME, time.time() - case_start)

    results.append(result)
    log_decision(audit_log_path, result)

    print(
        m.PIPELINE_CASE_DONE.format(
            response_mode=result.get(c.K_RESPONSE_MODE),
            workflow_status=result.get(c.K_WORKFLOW_STATUS),
            risk_score=result.get(c.K_RISK_SCORE),
            human_review_required=result.get(c.K_HUMAN_REVIEW_REQUIRED),
            case_duration=case_duration
        )
    )


df_results, metrics = evaluate(results)
monitoring_df = create_monitoring_dataframe(results)

df_results.to_csv(results_csv_path, index=False)
monitoring_df.to_csv(monitoring_csv_path, index=False)

metrics_json_path.write_text(
    json.dumps(metrics, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8
)

v4_config = {
    c.K_VERSION: c.PIPELINE_VERSION_V4,
    c.K_FEATURES: c.V4_PIPELINE_FEATURES,
    c.K_CONFIG_FILE: str(config_path),
    c.K_TESTSET_FILE: str(testset_path),
    c.K_KNOWLEDGE_BASE: str(knowledge_base_path),
    c.K_RETRIEVAL_K: c.RETRIEVAL_K,
    c.K_WORKFLOW_STATES: c.V4_WORKFLOW_STATES,
    c.K_THRESHOLDS: {
        c.K_THRESHOLD_CLASSIFICATION_UNKNOWN: c.CLASSIFICATION_UNKNOWN_THRESHOLD,
        c.K_THRESHOLD_CLASSIFICATION_REVIEW: c.CLASSIFICATION_REVIEW_THRESHOLD,
        c.K_THRESHOLD_RISK_REVIEW: c.RISK_REVIEW_THRESHOLD,
        c.K_THRESHOLD_RISK_ESCALATION: c.RISK_ESCALATION_THRESHOLD,
        c.K_THRESHOLD_GUARDRAIL_MIN_LENGTH: c.MIN_GUARDRAIL_ANSWER_LENGTH,
    },
    c.K_OUTPUT_FILES: {
        c.K_RESULTS_CSV: str(results_csv_path),
        c.K_METRICS_JSON: str(metrics_json_path),
        c.K_MONITORING_CSV: str(monitoring_csv_path),
        c.K_AUDIT_LOG_JSONL: str(audit_log_path),
    },
}

config_json_path.write_text(
    json.dumps(v4_config, indent=JSON_INDENT, ensure_ascii=False),
    encoding=ENC_UTF8
)

print(m.PIPELINE_V4_SUMMARY_HEADER)
print(metrics)
